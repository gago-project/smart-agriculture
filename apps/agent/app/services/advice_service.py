from __future__ import annotations

"""Conservative management-advice composer.

Advice text is intentionally generic and cautious.  It can reference verified
query/rule facts, but it should not become the source of factual conclusions.
That boundary keeps "事实题" and "建议题" from contaminating each other.
"""

from typing import Any


class AdviceService:
    """Build practical soil-management advice from evaluated records."""

    async def compose(self, *, intent: str, query_result: dict[str, Any], rule_result: dict[str, Any], slots: dict[str, Any]) -> dict[str, Any]:
        """Return one advice string for the downstream response node."""
        del intent
        records = rule_result.get("evaluated_records") or query_result.get("records") or []
        record = records[0] if records else None
        audience = slots.get("audience", "general")
        facts = ""
        if record:
            facts = f"当前最新记录为 {record.get('sample_time')}，20cm 相对含水量 {record.get('water20cm')}%，规则判断为 {record.get('display_label')}。"
        if audience == "greenhouse":
            advice = "建议优先检查棚内通风与排灌条件，避免长时间积水或局部失墒。"
        else:
            advice = "建议先结合地块实况核查墒情，偏旱时优先小水慢灌，偏湿时及时排水降渍。"
        return {
            "advice_text": f"{facts} {advice} 以上建议仅作管理参考，实际措施还需结合土壤、作物和天气情况综合判断。".strip()
        }


__all__ = ["AdviceService"]
