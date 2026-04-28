"""Four canonical soil-moisture Function Calling tool schemas.

Tool contract:
  query_soil_summary   – aggregated overview; anomaly/warning/advice modes via output_mode
  query_soil_ranking   – sorted TopN by aggregation dimension
  query_soil_detail    – single region or device detail with evidence fields

Time is specified via time_expression (semantic enum). The Parameter Resolver
expands it to absolute start_time/end_time before hitting the database.
Empty-result diagnosis is handled automatically by the executor — no separate tool needed.
"""
from __future__ import annotations

_TIME_EXPRESSION_PROP = {
    "time_expression": {
        "type": "string",
        "enum": [
            "today", "yesterday", "last_3_days", "last_7_days",
            "last_14_days", "last_30_days", "last_week", "this_month", "last_month",
        ],
        "description": (
            "查询时间范围语义枚举。"
            "today=今天，yesterday=昨天，last_3_days=最近3天，last_7_days=最近7天，"
            "last_14_days=最近14天，last_30_days=最近30天，"
            "last_week=上一个完整周（周一至周日），"
            "this_month=本月至今，last_month=上个完整自然月。"
            "所有时间以数据库最新业务时间为锚点计算，不使用系统当前时间。"
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
                "properties": {**_REGION_PROPS, **_TIME_EXPRESSION_PROP, **_OUTPUT_MODE_PROP},
                "required": ["time_expression"],
            },
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
                    **_TIME_EXPRESSION_PROP,
                    "top_n": {
                        "type": "integer",
                        "description": "返回前几名，最大 20，默认 5",
                    },
                    "aggregation": {
                        "type": "string",
                        "enum": ["county", "city", "device"],
                        "description": "排名维度：county=县区级，city=市级，device=设备级",
                    },
                },
                "required": ["time_expression", "aggregation"],
            },
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
                "properties": {**_REGION_PROPS, **_TIME_EXPRESSION_PROP, **_OUTPUT_MODE_PROP},
                "required": ["time_expression"],
            },
        },
    },
]

__all__ = ["SOIL_TOOLS"]
