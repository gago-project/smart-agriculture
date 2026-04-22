from __future__ import annotations

"""Controlled answer generation for the Soil Agent.

The service first builds deterministic, data-grounded fallback answers from
query/rule/template outputs.  Qwen is optional and may only rewrite those facts
through `generate_controlled_answer`; it is not allowed to invent metrics,
counts, time windows, or warning conclusions.
"""

from statistics import mean
from typing import Any

from jinja2 import Environment, FileSystemLoader

from app.llm.qwen_client import QwenClient


def _safe_float(value: Any) -> float | None:
    """Convert database numeric values into floats without raising."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class ResponseService:
    """Create final human-readable answers from verified intermediate facts."""

    def __init__(self, qwen_client: QwenClient | None = None) -> None:
        """Prepare optional Qwen client and Jinja templates for fixed outputs."""
        self.qwen_client = qwen_client
        self.template_env = Environment(
            loader=FileSystemLoader(str(__import__("pathlib").Path(__file__).resolve().parents[1] / "templates")),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    async def generate(
        self,
        *,
        intent: str,
        answer_type: str,
        query_result: dict[str, Any],
        rule_result: dict[str, Any],
        template_result: dict[str, Any],
        advice_result: dict[str, Any],
        slots: dict[str, Any],
        business_time: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate the final answer for a plans-defined `answer_type`.

        The deterministic answer is always produced first.  If Qwen is
        unavailable, slow, or returns invalid JSON, the deterministic answer is
        returned unchanged so the agent remains stable in offline/local Docker.
        """
        fallback_answer = self.build_deterministic_answer(
            intent=intent,
            answer_type=answer_type,
            query_result=query_result,
            rule_result=rule_result,
            template_result=template_result,
            advice_result=advice_result,
            slots=slots,
            business_time=business_time,
        ) or "当前未能生成结构化回答，已切换到安全兜底。"

        qwen_answer = await self._try_qwen_answer(
            answer_type=answer_type,
            fallback_answer=fallback_answer,
            facts={
                "query_result": query_result,
                "rule_result": rule_result,
                "template_result": template_result,
                "advice_result": advice_result,
            },
        )
        return {"final_answer": qwen_answer or fallback_answer}

    def build_deterministic_answer(
        self,
        *,
        intent: str,
        answer_type: str,
        query_result: dict[str, Any],
        rule_result: dict[str, Any],
        template_result: dict[str, Any],
        advice_result: dict[str, Any],
        slots: dict[str, Any],
        business_time: dict[str, Any],
    ) -> str | None:
        """Build a deterministic answer without any LLM usage.

        Returning `None` means the current state does not yet contain enough
        structured data to synthesize a meaningful answer.
        """
        del intent
        records = rule_result.get("evaluated_records") or query_result.get("records") or []
        if answer_type == "soil_summary_answer" and records:
            return self._summary_answer(records, slots, business_time)
        if answer_type == "soil_ranking_answer" and records:
            return self._ranking_answer(records, query_result)
        if answer_type == "soil_detail_answer" and records:
            return self._detail_answer(records, slots)
        if answer_type == "soil_anomaly_answer" and records:
            return self._anomaly_answer(records)
        if answer_type == "soil_warning_answer" and (template_result.get("rendered_text") or records):
            return self._warning_answer(records, template_result, advice_result, slots)
        if answer_type == "soil_advice_answer" and advice_result.get("advice_text"):
            return advice_result.get("advice_text")
        return None

    def _summary_answer(self, records: list[dict[str, Any]], slots: dict[str, Any], business_time: dict[str, Any]) -> str:
        """Summarize the current scope using only returned MySQL records."""
        if not records:
            region_name = slots.get("town_name") or slots.get("county_name") or slots.get("city_name") or "当前范围"
            return f"{region_name} 当前没有可用墒情数据，请先确认地区名称或导入最新批次。"
        water_values = [_safe_float(item.get("water20cm")) for item in records]
        valid_values = [item for item in water_values if item is not None]
        avg_water = round(mean(valid_values), 2) if valid_values else None
        risky = [item for item in records if item.get("soil_status") != "not_triggered"]
        if slots.get("batch_id") == "latest_batch":
            scope_name = "本批数据"
        else:
            scope_name = slots.get("town_name") or slots.get("county_name") or slots.get("city_name") or "当前整体"
        avg_text = f"20cm平均相对含水量约 {avg_water}%" if avg_water is not None else "20cm相对含水量暂无可用统计"
        if risky:
            risk_text = f"当前有 {len(risky)} 个点位需要重点关注"
        else:
            risk_text = "当前未发现需要重点关注的异常点位"
        return f"{scope_name}墒情概况：{avg_text}，{risk_text}。"

    def _ranking_answer(self, records: list[dict[str, Any]], query_result: dict[str, Any]) -> str:
        """Build a TopN ranking from anomaly scores in the query result."""
        if not records:
            return "当前范围内没有可用于排名的墒情记录，请先确认查询对象或导入最新数据。"
        aggregation = query_result.get("aggregation", "county")
        top_n = query_result.get("top_n", 5)
        grouped: dict[str, list[float]] = {}
        for record in records:
            key = record.get("device_sn") if aggregation == "device" else record.get("city_name") if aggregation == "city" else record.get("county_name")
            grouped.setdefault(key or "未知", []).append(float(record.get("soil_anomaly_score") or 0))
        ranking = sorted(
            ((name, round(max(scores), 2)) for name, scores in grouped.items()),
            key=lambda item: item[1],
            reverse=True,
        )[:top_n]
        items = "；".join(f"{idx}. {name}" for idx, (name, _score) in enumerate(ranking, start=1))
        label_map = {"county": "县区", "city": "地市", "device": "设备", "province": "地区"}
        aggregation_label = label_map.get(aggregation, "对象")
        return f"当前需优先关注的{aggregation_label}如下：{items}。"

    def _detail_answer(self, records: list[dict[str, Any]], slots: dict[str, Any]) -> str:
        """Describe the latest detail record for a device or region."""
        if not records:
            target = slots.get("device_sn") or slots.get("town_name") or slots.get("county_name") or slots.get("city_name") or "当前对象"
            return f"没有找到 {target} 的墒情数据，请核对名称或导入最新数据。"
        record = records[0]
        target = slots.get("device_sn") or slots.get("county_name") or slots.get("city_name") or record.get("device_sn")
        return (
            f"{target} 最新监测时间为 {record.get('sample_time')}，位于 {record.get('city_name')}{record.get('county_name')}，"
            f"20cm 相对含水量 {record.get('water20cm')}%，规则判断为 {record.get('display_label')}。"
        )

    def _anomaly_answer(self, records: list[dict[str, Any]]) -> str:
        """Explain which records triggered drought/fault warning rules."""
        anomalies = [record for record in records if record.get("soil_status") != "not_triggered"]
        if not records:
            return "当前没有可用于异常分析的墒情记录，请先确认范围或导入最新数据。"
        if not anomalies:
            return "当前范围内未发现命中规则的墒情异常点位。"
        names = []
        for record in anomalies[:5]:
            region_name = record.get("county_name") or record.get("city_name") or record.get("device_sn")
            names.append(f"{region_name}（{record.get('display_label')}）")
        return f"当前共识别出 {len(anomalies)} 个异常点位，重点关注：{'；'.join(names)}。"

    def _warning_answer(
        self,
        records: list[dict[str, Any]],
        template_result: dict[str, Any],
        advice_result: dict[str, Any],
        slots: dict[str, Any],
    ) -> str:
        """Render warning output, preferring strict template text when present."""
        if template_result.get("rendered_text"):
            final_answer = template_result["rendered_text"]
            if advice_result.get("advice_text"):
                final_answer = f"{final_answer}\n\n建议：{advice_result['advice_text']}"
            elif slots.get("render_mode") == "plus_explanation" and records:
                record = records[0]
                final_answer = f"{final_answer}\n\n说明：该结论基于 {record.get('sample_time')} 的最新监测值与规则判断生成。"
            return final_answer
        if not records:
            return "没有找到可用于预警判断的最新墒情记录。"
        record = records[0]
        return (
            f"设备 {record.get('device_sn')} 最新记录时间 {record.get('sample_time')}，20cm 相对含水量 {record.get('water20cm')}%，"
            f"规则判断为 {record.get('display_label')}。"
        )

    async def _try_qwen_answer(self, *, answer_type: str, fallback_answer: str, facts: dict[str, Any]) -> str | None:
        """Ask Qwen to polish wording while preserving the deterministic facts."""
        if not self.qwen_client or not self.qwen_client.available():
            return None
        return await self.qwen_client.generate_controlled_answer(
            answer_type=answer_type,
            facts=facts,
            fallback_answer=fallback_answer,
        )


__all__ = ["ResponseService"]
