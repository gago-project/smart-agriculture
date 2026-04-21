from __future__ import annotations

"""Intent and slot extraction for soil-moisture questions.

The parser is intentionally restricted.  It may ask Qwen for structured JSON,
but every request still has a deterministic regex/repository fallback so local
Docker can answer without an LLM key.  The output is limited to known intents,
answer types, and slots used by the Flow.
"""

import re
from dataclasses import dataclass
from typing import Any

from app.llm.qwen_client import QwenClient
from app.repositories.soil_repository import SoilRepository
from app.schemas.enums import AnswerType, IntentType
from app.services.region_service import RegionAliasResolver


DEVICE_RE = re.compile(r"SNS\d{8}", re.IGNORECASE)
TOP_N_RE = re.compile(r"前\s*(\d+)")
DATE_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")


@dataclass(frozen=True)
class ParseResult:
    """Normalized parser output passed to `IntentSlotExtractNode`."""

    intent: str
    answer_type: str
    slots: dict[str, Any]


class IntentSlotService:
    """Parse Chinese soil questions into a constrained intent/slot contract."""

    def __init__(self, repository: SoilRepository, qwen_client: QwenClient | None = None):
        """Keep repository access for known-region matching and optional Qwen."""
        self.repository = repository
        self.qwen_client = qwen_client
        self.region_alias_resolver = RegionAliasResolver(repository)

    async def parse(self, user_input: str, session_id: str) -> ParseResult:
        """Return a single best intent, answer type, and slot dictionary."""
        llm_result = await self._try_qwen_parse(user_input=user_input, session_id=session_id)
        if llm_result:
            return llm_result
        text = user_input.strip()
        slots: dict[str, Any] = {}
        device_match = DEVICE_RE.search(text)
        if device_match:
            slots["device_sn"] = device_match.group(0).upper()
        date_match = DATE_RE.search(text)
        if date_match:
            slots["target_date"] = date_match.group(1)

        region_resolution = await self.region_alias_resolver.resolve_from_text(text)
        if region_resolution["status"] == "matched":
            slots.update(region_resolution["slots"])
        elif region_resolution["status"] == "ambiguous":
            return ParseResult("clarification_needed", "clarification_answer", slots)

        if "乡镇" in text and "town_name" not in slots:
            candidate = text.split("乡镇")[0]
            if candidate:
                slots["town_name"] = f"{candidate}乡镇"

        slots["time_range"] = self._parse_time_range(text)
        if any(token in text for token in ["这批", "这一批", "本批"]):
            # "这一批" is a business alias for the latest imported batch.  The
            # actual batch UUID is resolved later by `TimeResolveService`.
            slots["batch_id"] = "latest_batch"
        compact = text.replace(" ", "")
        slots["follow_up"] = any(token in text for token in ["那", "这个", "这种情况", "换成", "上周的呢"]) or compact in {"有没有问题", "那个情况呢"}
        top_match = TOP_N_RE.search(text)
        if top_match:
            slots["top_n"] = int(top_match.group(1))

        if any(token in text for token in ["所有设备", "全部设备"]):
            slots["batch_devices"] = "all"
        if "趋势" in text:
            slots["trend"] = "daily" if "每天" in text else "series"
        if "全省" in text:
            slots["aggregation"] = "province"
        if "设备" in text:
            slots["aggregation"] = "device"
        elif "哪个市" in text or ("市" in text and "最严重" in text):
            slots["aggregation"] = "city"
        elif any(token in text for token in ["哪个县", "哪里最严重", "县区"]):
            slots["aggregation"] = "county"

        if any(token in text for token in ["20cm", "40cm", "60cm", "80cm"]):
            metric_match = re.search(r"(20|40|60|80)cm", text)
            if metric_match:
                slots["metric"] = f"water{metric_match.group(1)}cm"

        if "农户" in text:
            slots["audience"] = "farmer"
        elif "大棚" in text:
            slots["audience"] = "greenhouse"

        if "按模板" in text:
            slots["render_mode"] = "strict"
        elif "解释原因" in text:
            slots["render_mode"] = "plus_explanation"

        if any(token in text for token in ["预警", "模板"]):
            slots["need_template"] = True
            return ParseResult("soil_warning_generation", "soil_warning_answer", slots)
        if any(token in text for token in ["建议", "怎么办", "注意", "什么意思", "怎么处理"]):
            if "什么意思" in text:
                return ParseResult("soil_metric_explanation", "soil_advice_answer", slots)
            return ParseResult("soil_management_advice", "soil_advice_answer", slots)
        if self._is_summary_question(text):
            return ParseResult("soil_recent_summary", "soil_summary_answer", slots)
        if compact == "有没有问题":
            return ParseResult("clarification_needed", "clarification_answer", slots)
        if slots.get("device_sn") and "异常" in text:
            return ParseResult("soil_device_query", "soil_detail_answer", slots)
        if any(token in text for token in ["异常", "重旱", "涝渍", "需要关注"]):
            return ParseResult("soil_anomaly_query", "soil_anomaly_answer", slots)
        if any(token in text for token in ["排名", "最严重", "Top", "top", "前"]) and "预警" not in text:
            slots.setdefault("aggregation", "county")
            return ParseResult("soil_severity_ranking", "soil_ranking_answer", slots)
        if slots.get("trend") and (slots.get("device_sn") or slots.get("batch_devices") == "all" or slots.get("aggregation") == "device"):
            return ParseResult("soil_device_query", "soil_detail_answer", slots)
        if slots.get("trend"):
            return ParseResult("soil_region_query", "soil_detail_answer", slots)
        if slots.get("device_sn"):
            return ParseResult("soil_device_query", "soil_detail_answer", slots)
        if slots.get("city_name") or slots.get("county_name") or slots.get("town_name") or slots.get("follow_up"):
            return ParseResult("soil_region_query", "soil_detail_answer", slots)
        return ParseResult("soil_recent_summary", "soil_summary_answer", slots)

    async def _try_qwen_parse(self, *, user_input: str, session_id: str) -> ParseResult | None:
        """Attempt Qwen structured parsing and reject malformed responses."""
        if not self.qwen_client or not self.qwen_client.available():
            return None
        result = await self.qwen_client.extract_intent_slots(user_input=user_input, session_id=session_id)
        if not result:
            return None
        intent = result.get("intent")
        answer_type = result.get("answer_type")
        slots = result.get("slots")
        if not isinstance(intent, str) or not isinstance(answer_type, str) or not isinstance(slots, dict):
            return None
        if intent not in {item.value for item in IntentType}:
            return None
        if answer_type not in {item.value for item in AnswerType}:
            return None
        slots = await self.region_alias_resolver.normalize_slots(slots)
        if slots.get("_region_resolution_status") == "ambiguous":
            return ParseResult("clarification_needed", "clarification_answer", {})
        return ParseResult(intent, answer_type, slots)

    def _parse_time_range(self, text: str) -> str:
        """Map user time phrases to the finite time-window vocabulary."""
        if "这批" in text or "这一批" in text or "本批" in text:
            return "latest_batch"
        if DATE_RE.search(text):
            return "exact_date"
        if any(token in text for token in ["现在", "当前", "最新"]):
            return "latest_business_time"
        if any(token in text for token in ["过去一个月", "近一个月", "最近一个月"]):
            return "last_30_days"
        if "最近7天" in text or "近7天" in text:
            return "last_7_days"
        if "上周" in text:
            return "last_week"
        if "最近" in text:
            return "last_7_days"
        if "今年以来" in text:
            return "year_to_date"
        if "过去两年" in text or "近两年" in text:
            return "last_2_years"
        if "过去5年" in text or "近5年" in text:
            return "last_5_years"
        if "近三年" in text or "过去三年" in text:
            return "last_3_years"
        return "last_7_days"

    def _is_summary_question(self, text: str) -> bool:
        """Return whether the question asks for an overview rather than detail."""
        if any(token in text for token in ["异常", "预警", "最严重", "排名", "需要关注"]):
            return False
        return any(
            token in text
            for token in [
                "墒情怎么样",
                "墒情如何",
                "整体情况",
                "总体情况",
                "现在的墒情",
                "当前的墒情",
                "这批数据整体情况",
                "这一批数据整体情况",
            ]
        )


__all__ = ["IntentSlotService", "ParseResult"]
