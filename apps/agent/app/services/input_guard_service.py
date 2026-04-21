from __future__ import annotations

"""Input boundary classifier for the restricted Soil Agent.

This service is the first safety gate.  Its job is to decide whether a user
message should enter the business Flow at all.  It deliberately catches
greetings, capability questions, out-of-domain topics, low-confidence vague
requests, and random keyboard input before any database query can happen.
"""

import re
from dataclasses import dataclass


def _contains_chinese(text: str) -> bool:
    """Return whether the text contains at least one CJK character."""
    return any("\u4e00" <= char <= "\u9fff" for char in text)


@dataclass(frozen=True)
class InputGuardResult:
    """Structured result consumed by `InputGuardNode`."""

    allow_business_flow: bool
    input_type: str
    terminal_action: str
    suggested_answer_type: str
    suggested_answer: str
    intent: str | None = None


class InputGuardService:
    """Classify raw user input into business or terminal guardrail paths."""

    # Random Latin-letter strings such as "h d k j h" should be treated as
    # meaningless input, not forced into a soil summary/advice answer.
    meaningless_re = re.compile(r"^[a-zA-Z\s\?？!！,，.。/]+$")
    ambiguous_texts = {"看看", "查一下", "帮我查一下", "情况", "帮我看一下", "那个情况呢"}
    colloquial_texts = {"有没有问题", "现在的墒情", "当前的墒情"}
    colloquial_markers = ("那", "这个", "这种情况", "换成")

    def classify(self, text: str) -> InputGuardResult:
        """Classify one user message and provide a terminal answer when needed."""
        normalized = text.strip()
        compact = normalized.replace(" ", "")
        if not normalized or normalized in {"？？？", "???", "..."}:
            return InputGuardResult(
                allow_business_flow=False,
                input_type="meaningless_input",
                terminal_action="safe_end",
                suggested_answer_type="safe_hint_answer",
                suggested_answer="我是墒情智能助手，可以帮你查询墒情概览、地区/设备详情、异常分析和预警模板。你可以问：最近墒情怎么样？如东县最近怎么样？SNS00204333 需要发预警吗？",
            )
        if normalized in {"你好", "在吗", "hello", "hi"}:
            return InputGuardResult(
                allow_business_flow=False,
                input_type="greeting",
                terminal_action="safe_end",
                suggested_answer_type="safe_hint_answer",
                suggested_answer="你好，我可以帮助查询土壤墒情、分析异常、生成预警模板，并提供保守的管理建议。",
            )
        if "能做什么" in normalized or "你是谁" in normalized:
            return InputGuardResult(
                allow_business_flow=False,
                input_type="capability_question",
                terminal_action="safe_end",
                suggested_answer_type="safe_hint_answer",
                suggested_answer="我当前支持墒情概览、地区/设备详情、异常分析、预警判断和模板输出。你可以直接给地区、设备或时间范围来问。",
            )
        if any(keyword in normalized for keyword in ["天气", "写首诗", "股票"]):
            return InputGuardResult(
                allow_business_flow=False,
                input_type="out_of_domain",
                terminal_action="boundary_end",
                suggested_answer_type="boundary_answer",
                suggested_answer="我当前只支持土壤墒情相关的数据查询、异常分析、预警判断和管理建议，暂不处理天气、诗歌或股票类问题。",
                intent="out_of_scope",
            )
        if compact in self.ambiguous_texts:
            return InputGuardResult(
                allow_business_flow=False,
                input_type="ambiguous_low_confidence",
                terminal_action="clarify_end",
                suggested_answer_type="clarification_answer",
                suggested_answer="你想查看哪类墒情信息？可以补充地区、设备或时间，例如：如东县最近墒情怎么样、SNS00204333 最近有没有异常、过去一个月哪里最严重。",
                intent="clarification_needed",
            )
        if self.meaningless_re.match(normalized) and not _contains_chinese(normalized):
            return InputGuardResult(
                allow_business_flow=False,
                input_type="meaningless_input",
                terminal_action="safe_end",
                suggested_answer_type="safe_hint_answer",
                suggested_answer="我这边更擅长处理墒情业务问题。你可以直接问地区、设备、时间范围、异常或预警相关内容。",
            )
        input_type = "business_colloquial" if self._is_colloquial_business(normalized, compact) else "business_direct"
        return InputGuardResult(
            allow_business_flow=True,
            input_type=input_type,
            terminal_action="continue",
            suggested_answer_type="",
            suggested_answer="",
        )

    def _is_colloquial_business(self, normalized: str, compact: str) -> bool:
        """Detect short colloquial business prompts that still need the Flow."""
        if compact in self.colloquial_texts:
            return True
        if "什么意思" in normalized:
            return True
        return any(marker in normalized for marker in self.colloquial_markers)


__all__ = ["InputGuardResult", "InputGuardService"]
