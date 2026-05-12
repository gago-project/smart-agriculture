"""LLM route classifier: promotes safe_hint/summary to a specific route.

Called only when the 26 deterministic rules in TurnRouteDecisionService produce
a weak outcome (safe_hint or summary-fallback). LLM picks from a fixed set of
classifiable routes; follow-up routes and routes that need extra context
(list_target, group_by) are excluded.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any


logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.8

# Routes the classifier may produce. Excludes:
#   - follow_up_* (require multi-turn context analysis)
#   - standalone_list / standalone_group (require list_target / group_by)
#   - device_registry_county_detail (requires city entity already resolved)
#   - unsupported_derived / safe_hint (terminal "give up" outcomes)
CLASSIFIABLE_ROUTES = frozenset({
    "warning_list",
    "warning_count",
    "warning_disposal",
    "warning_rule_description",
    "device_registry_count",
    "device_registry_distribution",
    "count",
    "field",
    "compare",
    "latest_record",
    "detail",
    "rule",
    "template",
    "summary",
})

_SYSTEM_PROMPT = """\
你是土壤墒情问答系统的路由分类器，只输出 JSON，不解释。

根据用户输入，选择最匹配的查询路由：
- warning_list: 查预警记录列表（哪些点位有预警、有哪些告警记录）
- warning_count: 查预警数量（多少条预警、预警了多少台）
- warning_disposal: 查预警处置进度（处置情况、处理了吗、处置状态、跟进情况）
- warning_rule_description: 查预警规则说明（什么情况下触发预警、重旱标准是什么）
- device_registry_count: 查接入设备总数（接入了多少台墒情仪）
- device_registry_distribution: 查设备分布（各地市分布、设备分布在哪些城市）
- count: 查记录/点位数量（最近有多少条记录、有多少个点位）
- field: 查某字段具体值（含水量是多少、温度是多少）
- compare: 对比查询（A和B哪里更严重、对比两个地区的墒情）
- latest_record: 查最新一条记录（最新一条、最近的一条数据）
- detail: 查详情明细（某地详细数据、某设备明细）
- rule: 查业务规则（规则是什么、规则说明）
- template: 查预警模板（模板内容、按模板输出）
- summary: 墒情概况（某地最近墒情怎么样、整体情况如何）

严格输出：
{"route": "路由名称", "confidence": 0.0}

规则：
- 对把握度高的情况 confidence 给接近 1 的值
- 不确定时 confidence 给 0.5 以下
"""


@dataclass(frozen=True)
class LlmRouteClassification:
    route: str
    confidence: float = 0.0


class LlmRouteClassifierService:
    """Classify ambiguous inputs into a specific route using a bounded LLM call."""

    def __init__(self, qwen_client: Any = None, timeout_seconds: float = 3.0) -> None:
        self._client = qwen_client
        self._timeout = timeout_seconds

    async def classify(self, text: str) -> LlmRouteClassification | None:
        normalized = str(text or "").strip()
        if not normalized:
            return None
        if not self._client or not getattr(self._client, "available", lambda: False)():
            logger.debug("LLM route classifier unavailable; skipping")
            return None

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": normalized},
        ]
        try:
            raw = await asyncio.wait_for(
                self._client._request_json(messages=messages),
                timeout=self._timeout,
            )
        except Exception as exc:
            logger.debug("LLM route classifier fallback (timeout/error): %s", exc)
            return None

        if not isinstance(raw, dict):
            return None

        route = str(raw.get("route") or "").strip()
        if route not in CLASSIFIABLE_ROUTES:
            logger.debug("LLM route classifier returned unknown route %r; discarding", route)
            return None

        try:
            confidence = float(raw.get("confidence") or 0.0)
        except (TypeError, ValueError):
            return None

        confidence = max(0.0, min(1.0, confidence))
        if confidence < CONFIDENCE_THRESHOLD:
            logger.debug("LLM route classifier low confidence=%.2f for route=%s; discarding", confidence, route)
            return None

        return LlmRouteClassification(route=route, confidence=confidence)


__all__ = ["LlmRouteClassifierService", "LlmRouteClassification", "CLASSIFIABLE_ROUTES", "CONFIDENCE_THRESHOLD"]
