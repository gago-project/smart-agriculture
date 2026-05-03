"""受限土壤墒情 Agent 的输入边界分类模块。

在业务 Flow 与数据库访问之前，对用户原始输入做第一道分流：问候、能力询问、
明显越界话题、信息过少的模糊请求、无意义乱敲等直接走终止态并给出固定话术；
只有通过守卫的输入才 `allow_business_flow=True` 进入后续节点链。

分类策略：
- 高确定性规则（问候/越界/结束语/无意义）→ 同步，不走 LLM
- 低确定性（business_colloquial）→ 仍放行进业务流程，
  由后续 deterministic 解析链按需做指代消解与参数补全
- 超时降级：不拦截合法请求
"""

from __future__ import annotations


import re
from dataclasses import dataclass


def _contains_chinese(text: str) -> bool:
    """判断字符串中是否至少包含一个中日韩统一表意文字（CJK）字符。"""
    return any("\u4e00" <= char <= "\u9fff" for char in text)


@dataclass(frozen=True)
class InputGuardResult:
    """输入守卫的结构化输出，供数据回答服务决定后续路由。

    Attributes:
        allow_business_flow: 是否允许进入后续业务 Flow（查库、意图抽取等）。
        input_type: 输入类别标签，如 greeting、out_of_domain、business_direct 等。
        terminal_action: 流程终态或继续：如 safe_end、clarify_end、continue。
        suggested_answer_type: 若需直接回复用户，建议的答案类型（与模板/渲染约定对齐）。
        suggested_answer: 守卫阶段可直接返回给用户的文案（业务流时通常为空）。
        intent: 可选语义标签，如越界、需澄清等，供下游或日志使用。
    """

    allow_business_flow: bool
    input_type: str
    terminal_action: str
    suggested_answer_type: str  # always "guidance_answer" for non-business, "" for business
    suggested_answer: str
    intent: str | None = None
    guidance_reason: str | None = None  # clarification / safe_hint / boundary / closing


class InputGuardService:
    """将用户原始输入分为「可进业务流程」与「守卫终止」两类。

    采用轻量规则与集合匹配，优先拦截低成本误触与越界，避免无意义请求触发
    数据库访问与后续解析链；对仍属墒情域但表述口语、过短的句子标记为
    colloquial，交给后续服务补全上下文。
    """

    # 仅拉丁字母、空白与少量标点（如 "h d k j h"）：视为乱敲，不按墒情摘要硬答。
    meaningless_re = re.compile(r"^[a-zA-Z\s\?？!！,，.。/]+$")
    device_re = re.compile(r"SNS\d{8}", re.IGNORECASE)
    # 去掉空格后的整句仍过短、缺主体：置信低，引导用户补充地区/设备/时间。
    ambiguous_texts = {"看看", "查一下", "帮我查一下", "情况", "帮我看一下"}
    # 短句但明显在问墒情现状，仍走业务 Flow，由后续节点解析。
    colloquial_texts = {"有没有问题", "现在的墒情", "当前的墒情"}
    # 指代型口语（那/这个/换成…），通常需要结合上下文，仍视为业务相关。
    colloquial_markers = ("那", "这个", "这种情况", "换成", "不是")
    pure_closing_texts = {
        "谢谢",
        "谢谢了",
        "多谢",
        "好的不用了",
        "好的先这样",
        "不用了",
        "先这样",
        "先到这",
        "结束",
        "结束当前话题",
        "就这样",
    }

    capability_markers = (
        "能做什么",
        "可以做什么",
        "可以帮我做什么",
        "可以为我做点什么",
        "能帮我做什么",
        "会什么",
        "支持什么",
        "你是谁",
    )
    greeting_fragments = ("你好", "您好", "在吗", "在不在", "hello", "hi")
    casual_smalltalk_fragments = ("哈哈", "呵呵", "嘿嘿")
    creative_request_re = re.compile(r"(写|创作).{0,16}(诗|散文|作文|故事|文章|文案|歌词|小说)")

    def classify(self, text: str) -> InputGuardResult:
        """对单条用户消息做分类；若不应进业务流，则附带建议回复与终态动作。"""
        normalized = text.strip()
        compact = normalized.replace(" ", "")
        # 空输入或纯占位符：安全提示后直接结束。
        if not normalized or normalized in {"？？？", "???", "..."}:
            return InputGuardResult(
                allow_business_flow=False,
                input_type="meaningless_input",
                terminal_action="safe_end",
                suggested_answer_type="guidance_answer",
                suggested_answer="我是墒情智能助手，可以帮你查询墒情概况、地区/点位/记录明细、按地区汇总，以及查看预警规则和模板。你可以问：最近墒情怎么样？如东县最近怎么样？最近30天按地区汇总墒情数据。",
                guidance_reason="safe_hint",
            )
        # 简单问候：不查库，友好说明能力范围。
        if normalized in {"你好", "在吗", "hello", "hi"}:
            return InputGuardResult(
                allow_business_flow=False,
                input_type="greeting",
                terminal_action="safe_end",
                suggested_answer_type="guidance_answer",
                suggested_answer="你好，我可以帮助查询土壤墒情、查看地区或设备详情、按地区汇总数据，以及查看预警规则和模板。",
                guidance_reason="safe_hint",
            )
        if self._is_greeting_like_smalltalk(normalized, compact):
            return InputGuardResult(
                allow_business_flow=False,
                input_type="meaningless_input",
                terminal_action="safe_end",
                suggested_answer_type="guidance_answer",
                suggested_answer="我可以继续帮你查墒情数据、地区/点位/记录明细、按地区汇总，或查看预警规则和模板。你也可以直接说地区、设备或时间范围。",
                guidance_reason="safe_hint",
            )
        # 能力/身份询问：用固定话术概括支持范围。
        if any(marker in normalized for marker in self.capability_markers):
            return InputGuardResult(
                allow_business_flow=False,
                input_type="capability_question",
                terminal_action="safe_end",
                suggested_answer_type="guidance_answer",
                suggested_answer="我当前支持墒情概况、地区/点位/记录明细、按地区汇总，以及预警规则和模板查看。你可以直接给地区、设备或时间范围来问。",
                guidance_reason="safe_hint",
            )
        domain_knowledge_answer = self._domain_knowledge_answer(normalized)
        if domain_knowledge_answer:
            return InputGuardResult(
                allow_business_flow=False,
                input_type="capability_question",
                terminal_action="safe_end",
                suggested_answer_type="guidance_answer",
                suggested_answer=domain_knowledge_answer,
                guidance_reason="safe_hint",
            )
        if self._is_out_of_domain_request(normalized):
            return InputGuardResult(
                allow_business_flow=False,
                input_type="out_of_domain",
                terminal_action="boundary_end",
                suggested_answer_type="guidance_answer",
                suggested_answer="我当前只支持土壤墒情相关的数据查询，以及预警规则、模板查看，暂不处理创作型请求或内部系统指令问题。",
                intent="out_of_scope",
                guidance_reason="boundary",
            )
        if self._is_pure_closing(normalized):
            return InputGuardResult(
                allow_business_flow=False,
                input_type="conversation_closing",
                terminal_action="closing_end",
                suggested_answer_type="guidance_answer",
                suggested_answer="好的，这个话题先结束。有需要时你再继续问我即可。",
                guidance_reason="closing",
            )
        # 明确越界关键词：边界终止，声明只处理墒情域。
        if any(keyword in normalized for keyword in ["天气", "写首诗", "股票"]):
            return InputGuardResult(
                allow_business_flow=False,
                input_type="out_of_domain",
                terminal_action="boundary_end",
                suggested_answer_type="guidance_answer",
                suggested_answer="我当前只支持土壤墒情相关的数据查询，以及预警规则、模板查看，暂不处理天气、诗歌或股票类问题。",
                intent="out_of_scope",
                guidance_reason="boundary",
            )
        # 过短模糊：澄清终止，提示补充查询要素。
        if compact in self.ambiguous_texts:
            return InputGuardResult(
                allow_business_flow=False,
                input_type="ambiguous_low_confidence",
                terminal_action="clarify_end",
                suggested_answer_type="guidance_answer",
                suggested_answer="你想查看哪类墒情信息？可以补充地区、设备或时间，例如：如东县最近墒情怎么样、SNS00204333 最近记录明细、最近30天按地区汇总墒情数据。",
                intent="clarification_needed",
                guidance_reason="clarification",
            )
        # 全拉丁且无中文：乱敲/试探，安全提示。
        if self.meaningless_re.match(normalized) and not _contains_chinese(normalized):
            return InputGuardResult(
                allow_business_flow=False,
                input_type="meaningless_input",
                terminal_action="safe_end",
                suggested_answer_type="guidance_answer",
                suggested_answer="我这边更擅长处理墒情业务问题。你可以直接问地区、设备、时间范围，或让我按地区汇总墒情数据。",
                guidance_reason="safe_hint",
            )
        # 其余视为可进业务：区分口语短问与更明确的业务直述。
        input_type = "business_colloquial" if self._is_colloquial_business(normalized, compact) else "business_direct"
        return InputGuardResult(
            allow_business_flow=True,
            input_type=input_type,
            terminal_action="continue",
            suggested_answer_type="",
            suggested_answer="",
        )

    def _is_colloquial_business(self, normalized: str, compact: str) -> bool:
        """判断是否为短口语、仍属墒情业务但需后续 Flow 补全的输入。"""
        if compact in self.colloquial_texts:
            return True
        if compact in {"那个情况呢", "这种情况呢"}:
            return True
        if (
            re.search(r"^(查一下|查下|看一下|看下|帮我查一下|帮我看一下).+情况", compact)
            and not self._has_explicit_time_signal(normalized)
        ):
            return True
        if "什么意思" in normalized:
            return True
        if normalized.endswith("呢") and self._contains_business_signal(normalized):
            return True
        return any(marker in normalized for marker in self.colloquial_markers)

    def _is_greeting_like_smalltalk(self, normalized: str, compact: str) -> bool:
        """识别夹杂问候词或口水话的短噪声输入，避免误入业务澄清。"""
        if self._contains_business_signal(normalized) or self._has_explicit_time_signal(normalized):
            return False
        if len(compact) > 6:
            return False
        if any(fragment in normalized.lower() for fragment in self.greeting_fragments):
            return True
        return any(fragment in normalized for fragment in self.casual_smalltalk_fragments)

    def _is_pure_closing(self, text: str) -> bool:
        """仅在无业务信号时，将结束语判定为关闭会话。"""
        compact = text.replace(" ", "").replace("，", "").replace(",", "").replace("。", "").replace(".", "")
        if compact not in self.pure_closing_texts:
            return False
        return not self._contains_business_signal(text)

    @staticmethod
    def _is_out_of_domain_request(text: str) -> bool:
        lowered = text.lower()
        if InputGuardService.creative_request_re.search(text):
            return True
        return any(
            token in text or token in lowered
            for token in (
                "写一首诗",
                "写诗",
                "system prompt",
                "prompt",
                "提示词",
                "内部指令",
                "忽略以上所有指令",
                "function_call",
                "tool_name",
            )
        )

    @staticmethod
    def _domain_knowledge_answer(text: str) -> str | None:
        if "涝渍" in text and ("什么意思" in text or "是什么" in text):
            return (
                "涝渍是土壤墒情的一种预警状态，通常表示 20cm 含水量达到或超过 80%，"
                "说明土壤可能存在积水风险，需要及时排水。"
                "如果你想看真实数据里的涝渍分布，可以直接问最近哪些地区有涝渍预警。"
            )
        return None

    def _contains_business_signal(self, text: str) -> bool:
        """识别设备、地区、时间、指标或业务动作词。"""
        if self.device_re.search(text):
            return True
        if re.search(r"(20|40|60|80)cm", text):
            return True
        if re.search(r"[\u4e00-\u9fff]{2,}(?:市|县|区|乡|镇)", text):
            return True
        return any(
            token in text
            for token in [
                "南京",
                "徐州",
                "盐城",
                "南通",
                "镇江",
                "如东",
                "墒情",
                "异常",
                "预警",
                "排名",
                "最严重",
                "建议",
                "怎么办",
                "注意",
                "情况",
                "数据",
                "今天",
                "昨天",
                "前天",
                "最近",
                "上周",
                "近",
                "过去",
            ]
        )

    @staticmethod
    def _has_explicit_time_signal(text: str) -> bool:
        return any(
            token in text
            for token in (
                "今天",
                "昨天",
                "前天",
                "上周",
                "这周",
                "本周",
                "这个月",
                "本月",
                "上个月",
                "今年",
                "最近",
                "过去",
                "近",
                "月",
                "天",
                "周",
                "年",
            )
        )


__all__ = ["InputGuardResult", "InputGuardService"]
