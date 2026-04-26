"""Intent and slot extraction for soil-moisture questions.

The parser is intentionally restricted.  It may ask Qwen for structured JSON,
but every request still has a deterministic regex/repository fallback so local
Docker can answer without an LLM key.  The output is limited to known intents,
answer types, and slots used by the Flow.
"""

from __future__ import annotations


import re
from dataclasses import dataclass
from typing import Any

from app.llm.qwen_client import QwenClient
from app.repositories.soil_repository import SoilRepository
from app.schemas.enums import AnswerType, IntentType
from app.services.region_service import RegionAliasResolver


DEVICE_RE = re.compile(r"SNS\d{8}", re.IGNORECASE)
TOP_N_RE = re.compile(r"(?<!之)前\s*(\d+)(?!\s*天)")
DATE_RE = re.compile(r"(20\d{2}-\d{2}-\d{2})(?!\d)")
ANCHOR_DAYS_RE = re.compile(r"(20\d{2}-\d{2}-\d{2})\s*(之前|之后)\s*(\d{1,4})\s*天")
RELATIVE_ANCHOR_DAYS_RE = re.compile(r"(\d{1,4})\s*天前\s*的\s*前\s*(\d{1,4})\s*天")
N_DAYS_AGO_RE = re.compile(r"(\d{1,4})\s*天前")
LAST_N_DAYS_RE = re.compile(r"(?:最近|近|过去)\s*(\d{1,4})\s*天")
DEPRECATED_FILLER_TOKENS = ("这一批", "这批", "本批", "这次")
SUPPORTED_SLOT_KEYS = {
    "aggregation",
    "audience",
    "batch_devices",
    "city",
    "county",
    "end_time",
    "follow_up",
    "metric",
    "need_template",
    "raw_time_expr",
    "render_mode",
    "sn",
    "start_time",
    "target_date",
    "time_explicit",
    "time_range",
    "top_n",
    "_region_resolution_status",
}


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
        deterministic_result = await self._parse_deterministic(user_input)
        if self._batch_phrase_requires_explicit_time(user_input):
            return deterministic_result
        if deterministic_result.intent != "clarification_needed":
            return deterministic_result
        llm_result = await self._try_qwen_parse(user_input=user_input, session_id=session_id)
        if llm_result and llm_result.intent != "clarification_needed":
            return llm_result
        return deterministic_result

    async def _parse_deterministic(self, user_input: str) -> ParseResult:
        """Return the regex/keyword-based parse result used as the stable baseline."""
        text = user_input.strip()
        semantic_text = self._strip_batch_fillers(text)
        slots: dict[str, Any] = {}
        device_match = DEVICE_RE.search(text)
        if device_match:
            slots["sn"] = device_match.group(0).upper()
        date_match = DATE_RE.search(text)
        if date_match:
            slots["target_date"] = date_match.group(1)
        if text.replace(" ", "") in {"看看", "查一下", "帮我查一下", "情况", "帮我看一下"}:
            return ParseResult("clarification_needed", "clarification_answer", slots)

        region_resolution = await self.region_alias_resolver.resolve_from_text(text)
        if region_resolution["status"] == "matched":
            slots.update(region_resolution["slots"])
        elif region_resolution["status"] == "ambiguous":
            return ParseResult("clarification_needed", "clarification_answer", slots)

        if self._batch_phrase_requires_explicit_time(text):
            return ParseResult("clarification_needed", "clarification_answer", slots)

        time_range, raw_time_expr = self._parse_time_range(semantic_text)
        if time_range:
            slots["time_range"] = time_range
            slots["time_explicit"] = True
            slots["raw_time_expr"] = raw_time_expr
        compact = text.replace(" ", "")
        compact_no_punctuation = compact.rstrip("？?。.!！")
        follow_up_detected = (
            any(token in text for token in ["那", "这个", "这种情况", "换成", "上周的呢"])
            or compact in {"有没有问题", "那个情况呢", "这种情况呢"}
            or (
                compact_no_punctuation.endswith("呢")
                and (slots.get("sn") or slots.get("city") or slots.get("county") or slots.get("metric"))
            )
        )
        slots["follow_up"] = bool(follow_up_detected)
        top_match = TOP_N_RE.search(text)
        if top_match:
            slots["top_n"] = int(top_match.group(1))

        if any(token in text for token in ["所有设备", "全部设备"]):
            slots["batch_devices"] = "all"
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
        if self._is_summary_question(semantic_text):
            return ParseResult("soil_recent_summary", "soil_summary_answer", slots)
        if compact == "有没有问题":
            return ParseResult("clarification_needed", "clarification_answer", slots)
        if slots.get("sn") and "异常" in text:
            return ParseResult("soil_device_query", "soil_detail_answer", slots)
        if any(token in text for token in ["异常", "重旱", "涝渍", "需要关注"]):
            return ParseResult("soil_anomaly_query", "soil_anomaly_answer", slots)
        if any(token in text for token in ["排名", "最严重", "Top", "top", "前"]) and "预警" not in text:
            slots.setdefault("aggregation", "county")
            return ParseResult("soil_severity_ranking", "soil_ranking_answer", slots)
        if slots.get("sn"):
            return ParseResult("soil_device_query", "soil_detail_answer", slots)
        if slots.get("city") or slots.get("county") or slots.get("follow_up"):
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
        slots = self._sanitize_slots(slots)
        if slots.get("_region_resolution_status") == "ambiguous":
            return ParseResult("clarification_needed", "clarification_answer", {})
        return ParseResult(intent, answer_type, slots)

    def _parse_time_range(self, text: str) -> tuple[str | None, str | None]:
        """Map user time phrases to the finite time-window vocabulary."""
        # Relative-anchor patterns must be checked before ANCHOR_DAYS_RE and plain DATE_RE.
        relative_anchor_match = RELATIVE_ANCHOR_DAYS_RE.search(text)
        if relative_anchor_match:
            n_ago = int(relative_anchor_match.group(1))
            before_days = int(relative_anchor_match.group(2))
            return f"relative_before_{before_days}_at_{n_ago}_ago", relative_anchor_match.group(0)
        n_days_ago_match = N_DAYS_AGO_RE.search(text)
        if n_days_ago_match:
            n = int(n_days_ago_match.group(1))
            return f"n_days_ago_{n}", n_days_ago_match.group(0)
        # Anchored window must be checked before plain date so "2025-12-01之前50天"
        # is not swallowed by the exact_date branch.
        anchor_match = ANCHOR_DAYS_RE.search(text)
        if anchor_match:
            anchor_date = anchor_match.group(1)
            direction = anchor_match.group(2)   # "之前" or "之后"
            n_days = int(anchor_match.group(3))
            direction_key = "before" if direction == "之前" else "after"
            raw_expr = f"{anchor_date}{direction}{n_days}天"
            return f"anchor_{direction_key}_{n_days}_days", raw_expr
        date_match = DATE_RE.search(text)
        if date_match:
            return "exact_date", date_match.group(1)
        if "前天" in text:
            return "day_before_yesterday", "前天"
        if "昨天" in text:
            return "yesterday", "昨天"
        if "今天" in text:
            return "today", "今天"
        if any(token in text for token in ["现在", "当前", "最新"]):
            raw_expr = next(token for token in ["现在", "当前", "最新"] if token in text)
            return "latest_business_time", raw_expr
        if any(token in text for token in ["过去一个月", "近一个月", "最近一个月"]):
            raw_expr = next(token for token in ["过去一个月", "近一个月", "最近一个月"] if token in text)
            return "last_30_days", raw_expr
        day_match = LAST_N_DAYS_RE.search(text)
        if day_match:
            return f"last_{max(int(day_match.group(1)), 1)}_days", day_match.group(0)
        if "最近7天" in text or "近7天" in text:
            return "last_7_days", "最近7天" if "最近7天" in text else "近7天"
        if "上周" in text:
            return "last_week", "上周"
        if "最近" in text:
            return "last_7_days", "最近"
        if "今年以来" in text:
            return "year_to_date", "今年以来"
        if "过去两年" in text or "近两年" in text:
            return "last_2_years", "过去两年" if "过去两年" in text else "近两年"
        if "过去5年" in text or "近5年" in text:
            return "last_5_years", "过去5年" if "过去5年" in text else "近5年"
        if "近三年" in text or "过去三年" in text:
            return "last_3_years", "近三年" if "近三年" in text else "过去三年"
        return None, None

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
            ]
        )

    def _batch_phrase_requires_explicit_time(self, text: str) -> bool:
        """Return whether batch-like filler words require a real time expression."""
        return self._has_batch_filler(text) and not self._has_explicit_time_expression(self._strip_batch_fillers(text))

    @staticmethod
    def _has_batch_filler(text: str) -> bool:
        """Return whether text contains deprecated batch-like filler words."""
        return any(token in text for token in DEPRECATED_FILLER_TOKENS)

    @staticmethod
    def _strip_batch_fillers(text: str) -> str:
        """Remove batch-like filler words without assigning batch query semantics."""
        result = text
        for token in DEPRECATED_FILLER_TOKENS:
            result = result.replace(token, "")
        return result

    def _has_explicit_time_expression(self, text: str) -> bool:
        """Return whether text contains a user-facing time expression."""
        if DATE_RE.search(text) or LAST_N_DAYS_RE.search(text) or N_DAYS_AGO_RE.search(text):
            return True
        return any(
            token in text
            for token in [
                "今天",
                "昨天",
                "前天",
                "现在",
                "当前",
                "最新",
                "过去一个月",
                "近一个月",
                "最近一个月",
                "最近7天",
                "近7天",
                "上周",
                "最近",
                "今年以来",
                "过去两年",
                "近两年",
                "过去5年",
                "近5年",
                "近三年",
                "过去三年",
            ]
        )

    @staticmethod
    def _sanitize_slots(slots: dict[str, Any]) -> dict[str, Any]:
        """Keep only supported Agent slots."""
        return {key: value for key, value in slots.items() if key in SUPPORTED_SLOT_KEYS}


__all__ = ["IntentSlotService", "ParseResult"]
