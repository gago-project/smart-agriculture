"""Four canonical soil-moisture Function Calling tool schemas."""
from __future__ import annotations

_TIME_WINDOW_PROPS = {
    "start_time": {
        "type": "string",
        "description": (
            "查询开始时间，格式必须为 YYYY-MM-DD HH:MM:SS。"
            "所有时间都以数据库最新业务时间为锚点理解，不要使用系统当前时间。"
        ),
    },
    "end_time": {
        "type": "string",
        "description": (
            "查询结束时间，格式必须为 YYYY-MM-DD HH:MM:SS。"
            "结束时间不得晚于当前最新业务时间所在范围。"
        ),
    }
}

_REGION_PROPS = {
    "city": {"type": "string", "description": "市名称，如 '南通市'，可选"},
    "county": {"type": "string", "description": "县区名称，如 '如东县'，可选"},
    "sn": {"type": "string", "description": "设备编号，如 'SNS00204333'，可选"},
}

_OUTPUT_MODE_PROP = {
    "output_mode": {
        "type": "string",
        "enum": ["normal", "anomaly_focus", "warning_mode", "advice_mode"],
        "description": (
            "输出关注模式：normal=标准概览，anomaly_focus=突出异常与需关注点，"
            "warning_mode=预警数据视角，advice_mode=管理建议背景"
        ),
    }
}

SOIL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_soil_summary",
            "description": (
                "查询土壤墒情整体概况，返回聚合统计结果：记录总数、平均含水量、"
                "各状态分布、需关注地区 TopN。"
                "适合用户问整体情况、近期概况、有没有问题等概述性问题。"
                "也用于异常分析（output_mode=anomaly_focus）、预警视角（warning_mode）、"
                "建议视角（advice_mode）。"
                "当查询返回空结果时，系统会自动诊断原因并在结果中说明。"
            ),
            "parameters": {
                "type": "object",
                "properties": {**_REGION_PROPS, **_TIME_WINDOW_PROPS, **_OUTPUT_MODE_PROP},
                "required": ["start_time", "end_time"],
            },
        },
        # internal metadata — not sent to the LLM, used by AgentLoopNode
        "meta": {
            "intent": "soil_recent_summary",
            "answer_type": "soil_summary_answer",
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_soil_ranking",
            "description": (
                "按墒情严重程度排名，返回已聚合、已排序、已裁剪的 TopN 列表。"
                "适合用户问前几名、最严重、排名等问题。"
                "返回的是结构化排名结果，不是原始记录。"
                "当查询返回空结果时，系统会自动诊断原因并在结果中说明。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    **_REGION_PROPS,
                    **_TIME_WINDOW_PROPS,
                    "top_n": {
                        "type": "integer",
                        "description": "返回前几名，最大 20，默认 5",
                    },
                    "aggregation": {
                        "type": "string",
                        "enum": ["county", "city", "device"],
                        "description": "排名维度：county=县区级，city=市级,device=设备级",
                    },
                },
                "required": ["start_time", "end_time", "aggregation"],
            },
        },
        "meta": {
            "intent": "soil_severity_ranking",
            "answer_type": "soil_ranking_answer",
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_soil_detail",
            "description": (
                "查询特定地区或设备的土壤墒情详情，返回最新记录、各层含水量、"
                "状态判断和异常证据字段。"
                "适合用户问具体某地区或设备的详细数据、预警情况、趋势描述。"
                "当查询返回空结果时，系统会自动诊断原因并在结果中说明。"
            ),
            "parameters": {
                "type": "object",
                "properties": {**_REGION_PROPS, **_TIME_WINDOW_PROPS, **_OUTPUT_MODE_PROP},
                "required": ["start_time", "end_time"],
            },
        },
        "meta": {
            "intent": "soil_region_query",
            "answer_type": "soil_detail_answer",
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_soil_comparison",
            "description": (
                "对多个地区或设备做横向对比查询，返回每个实体的统计结果与统一排序后的对比列表。"
                "适合用户问类似 '南通市和盐城市最近哪边墒情更差'、'对比 SNS00204333 和 SNS00204334' 的问题。"
                "entities 列表里每一项可以是 city 名、county 名或设备 SN，最多 5 个。"
                "当某个实体查询返回空结果时，系统会在该实体的结果中说明原因。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "对比对象列表（city/county/sn 任意一种），最少 2 个，最多 5 个",
                        "minItems": 2,
                        "maxItems": 5,
                    },
                    "entity_type": {
                        "type": "string",
                        "enum": ["region", "device"],
                        "description": "对比对象类型：region=地区（city 或 county），device=设备 SN",
                    },
                    **_TIME_WINDOW_PROPS,
                },
                "required": ["entities", "entity_type", "start_time", "end_time"],
            },
        },
        "meta": {
            "intent": "soil_severity_ranking",
            "answer_type": "soil_ranking_answer",
        },
    },
]


def get_tool_meta(tool_name: str) -> dict:
    """Return the internal metadata for a tool name (intent / answer_type)."""
    for tool in SOIL_TOOLS:
        if tool.get("function", {}).get("name") == tool_name:
            return tool.get("meta") or {}
    return {}


def get_tools_for_llm() -> list[dict]:
    """Return SOIL_TOOLS without internal `meta` keys for the LLM payload."""
    return [
        {"type": t["type"], "function": t["function"]}
        for t in SOIL_TOOLS
    ]


__all__ = ["SOIL_TOOLS", "get_tool_meta", "get_tools_for_llm"]
