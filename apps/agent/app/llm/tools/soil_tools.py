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
    "city": {"type": "string", "description": "市名称，如 '延安市'，可选"},
    "county": {"type": "string", "description": "县区名称，如 '志丹县'，可选"},
    "sn": {"type": "string", "description": "设备编号，如 'SNS00204333'，可选"},
}

SOIL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_soil_overview",
            "description": (
                "查询土壤墒情整体概况：记录数、平均含水量、需关注点位数。"
                "适合用户问整体情况、墒情如何、最近怎么样等概述性问题。"
            ),
            "parameters": {
                "type": "object",
                "properties": {**_REGION_PROPS, **_TIME_PROPS},
                "required": ["start_time", "end_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_soil_ranking",
            "description": (
                "按墒情严重程度排名，返回前 N 个最干旱或最需关注的地区或设备。"
                "适合用户问前几名、最严重、排名等问题。"
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
            "name": "get_soil_detail",
            "description": (
                "查询特定地区或设备的土壤墒情详情，返回各层含水量和温度数据。"
                "适合用户问具体某个地区或设备的详细数据。"
            ),
            "parameters": {
                "type": "object",
                "properties": {**_REGION_PROPS, **_TIME_PROPS},
                "required": ["start_time", "end_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_soil_anomaly",
            "description": (
                "查询异常墒情记录：重旱、涝渍或需要关注的设备和区域。"
                "适合用户问有没有异常、哪里需要关注、是否有重旱等问题。"
            ),
            "parameters": {
                "type": "object",
                "properties": {**_REGION_PROPS, **_TIME_PROPS},
                "required": ["start_time", "end_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_warning_data",
            "description": (
                "获取最新墒情预警所需数据，用于生成预警报告。"
                "适合用户要求生成预警、按模板出预警等场景。"
            ),
            "parameters": {
                "type": "object",
                "properties": {**_REGION_PROPS, **_TIME_PROPS},
                "required": ["start_time", "end_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_advice_context",
            "description": (
                "获取用于生成管理建议的墒情数据，包括各层含水量和历史趋势。"
                "适合用户问怎么办、有什么建议、应该怎么处理等问题。"
            ),
            "parameters": {
                "type": "object",
                "properties": {**_REGION_PROPS, **_TIME_PROPS},
                "required": ["start_time", "end_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "diagnose_empty_result",
            "description": (
                "当查询无数据时，诊断原因：地区是否存在、设备是否有数据、时间段是否有记录。"
                "在其他工具返回空结果后调用此工具排查原因。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    **_REGION_PROPS,
                    **_TIME_PROPS,
                    "scenario": {
                        "type": "string",
                        "enum": ["region_exists", "device_exists", "period_exists"],
                        "description": "诊断场景",
                    },
                },
                "required": ["start_time", "end_time", "scenario"],
            },
        },
    },
]

__all__ = ["SOIL_TOOLS"]
