"""Four canonical soil-moisture Function Calling tool schemas.

Tool contract (plan/1/1.plan.md):
  query_soil_summary   – aggregated overview; anomaly/warning/advice modes via output_mode
  query_soil_ranking   – sorted TopN by aggregation dimension
  query_soil_detail    – single region or device detail with evidence fields
  diagnose_empty_result – distinguish entity-not-found vs no-data-in-window

Every query tool requires start_time + end_time (YYYY-MM-DD HH:MM:SS).
"""
from __future__ import annotations

_TIME_PROPS = {
    "start_time": {
        "type": "string",
        "description": "查询起始时间，格式 YYYY-MM-DD HH:MM:SS，包含该时刻",
    },
    "end_time": {
        "type": "string",
        "description": "查询结束时间，格式 YYYY-MM-DD HH:MM:SS，包含该时刻",
    },
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
            ),
            "parameters": {
                "type": "object",
                "properties": {**_REGION_PROPS, **_TIME_PROPS, **_OUTPUT_MODE_PROP},
                "required": ["start_time", "end_time"],
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
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    **_REGION_PROPS,
                    **_TIME_PROPS,
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
                "required": ["start_time", "end_time", "aggregation"],
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
            ),
            "parameters": {
                "type": "object",
                "properties": {**_REGION_PROPS, **_TIME_PROPS, **_OUTPUT_MODE_PROP},
                "required": ["start_time", "end_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "diagnose_empty_result",
            "description": (
                "当其他工具返回空结果时，诊断原因：地区是否存在、设备是否存在、"
                "时间窗内是否有数据。"
                "必须在其他工具返回空数据后才调用此工具，用于区分"
                "'对象不存在'与'时间窗内无数据'两种情况。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    **_REGION_PROPS,
                    **_TIME_PROPS,
                    "scenario": {
                        "type": "string",
                        "enum": ["region_exists", "device_exists", "period_exists"],
                        "description": (
                            "诊断场景：region_exists=检查地区是否存在，"
                            "device_exists=检查设备是否存在，"
                            "period_exists=检查指定时间窗内是否有数据"
                        ),
                    },
                },
                "required": ["start_time", "end_time", "scenario"],
            },
        },
    },
]

__all__ = ["SOIL_TOOLS"]
