from __future__ import annotations

import re
from statistics import mean
from typing import Any

from app.repositories.soil_repository import SoilRepository


MEANINGLESS_RE = re.compile(r"^[a-zA-Z\s\?？!！。,.，、]{8,}$")
DEVICE_RE = re.compile(r"SNS\d{8}", re.IGNORECASE)


class SoilAgentService:
    def __init__(self, repository: SoilRepository | None = None):
        self.repository = repository or SoilRepository.from_env()

    def chat(self, user_input: str, *, session_id: str, turn_id: int) -> dict[str, Any]:
        text = user_input.strip()
        input_type = self._classify_input(text)
        if input_type in {"meaningless_input", "greeting", "capability_question", "out_of_domain"}:
            return self._safe_or_boundary(text, input_type, session_id, turn_id)
        if input_type == "ambiguous_low_confidence":
            return self._clarify(session_id, turn_id)

        device_sn = self._extract_device(text)
        if "预警" in text or "模板" in text:
            return self._warning_answer(text, device_sn, session_id, turn_id)
        if device_sn or "设备" in text or "异常" in text:
            return self._detail_answer(text, device_sn, session_id, turn_id)
        if any(keyword in text for keyword in ["建议", "怎么办", "注意", "什么意思"]):
            return self._advice_answer(text, device_sn, session_id, turn_id)
        return self._summary_answer(text, session_id, turn_id)

    def _classify_input(self, text: str) -> str:
        if not text or text in {"？？？", "???", "..."}:
            return "meaningless_input"
        if text in {"你好", "在吗", "hello", "hi"}:
            return "greeting"
        if "能做什么" in text or "你是谁" in text:
            return "capability_question"
        if any(keyword in text for keyword in ["天气", "写首诗", "股票"]):
            return "out_of_domain"
        compact = text.replace(" ", "")
        if MEANINGLESS_RE.match(text) and not any(ch >= "\u4e00" and ch <= "\u9fff" for ch in text):
            return "meaningless_input"
        if compact in {"看看", "查一下", "帮我查一下", "情况"}:
            return "ambiguous_low_confidence"
        return "business_direct"

    def _extract_device(self, text: str) -> str | None:
        match = DEVICE_RE.search(text)
        return match.group(0).upper() if match else None

    def _safe_or_boundary(self, text: str, input_type: str, session_id: str, turn_id: int) -> dict[str, Any]:
        if input_type == "out_of_domain":
            return self._response("out_of_scope", "boundary_answer", "我当前只支持土壤墒情相关的数据查询、异常分析、预警判断和管理建议。你可以问：最近墒情怎么样？某个设备是否需要预警？", session_id, turn_id, should_query=False, input_type=input_type)
        return self._response("none", "safe_hint_answer", "我是墒情智能助手，可以帮你查询墒情数据、分析异常、判断预警并给出处置建议。你可以问：最近墒情怎么样？SNS00204333 需要发预警吗？", session_id, turn_id, should_query=False, input_type=input_type)

    def _clarify(self, session_id: str, turn_id: int) -> dict[str, Any]:
        return self._response("clarification_needed", "clarification_answer", "你想查看哪类墒情信息？可以补充地区、设备或时间，例如：如东县最近墒情怎么样、SNS00204333 是否异常、过去一个月哪里最严重。", session_id, turn_id, should_query=False, input_type="ambiguous_low_confidence")

    def _summary_answer(self, text: str, session_id: str, turn_id: int) -> dict[str, Any]:
        records = self.repository.latest_records()
        water_values = [float(r["water20cm"]) for r in records if r.get("water20cm") is not None]
        avg_water = round(mean(water_values), 2) if water_values else None
        latest_time = records[0].get("record_time") if records else "暂无"
        risky = [r for r in records if self._status_for_record(r)["soil_status"] != "not_triggered"]
        answer = f"整体墒情概况：当前样本 {len(records)} 条，最新业务时间 {latest_time}，20cm 平均相对含水量 {avg_water}% ，需关注点位 {len(risky)} 个。数据来源为 smart_agriculture.fact_soil_moisture。"
        return self._response("soil_recent_summary", "soil_summary_answer", answer, session_id, turn_id, input_type="business_direct")

    def _detail_answer(self, text: str, device_sn: str | None, session_id: str, turn_id: int) -> dict[str, Any]:
        record = self.repository.latest_record_by_device(device_sn) if device_sn else self.repository.latest_records(1)[0]
        if not record:
            return self._response("soil_device_query", "fallback_answer", "没有找到该设备的墒情数据，请核对设备 SN 或导入最新数据。", session_id, turn_id)
        status = self._status_for_record(record)
        answer = f"设备 {record['device_sn']} 最新监测时间为 {record['record_time']}，位于{record['city_name']}{record['county_name']}，20cm 相对含水量 {record['water20cm']}%，规则判断为{status['display_label']}。"
        return self._response("soil_device_query", "soil_detail_answer", answer, session_id, turn_id)

    def _warning_answer(self, text: str, device_sn: str | None, session_id: str, turn_id: int) -> dict[str, Any]:
        record = self.repository.latest_record_by_device(device_sn or "SNS00204333")
        if not record:
            return self._response("soil_warning_generation", "fallback_answer", "没有找到可用于预警判断的最新墒情记录。", session_id, turn_id)
        status = self._status_for_record(record)
        if status["soil_status"] == "not_triggered":
            answer = f"设备 {record['device_sn']} 最新记录未达到墒情预警条件。监测时间 {record['record_time']}，20cm 相对含水量 {record['water20cm']}%，内部状态为 not_triggered，warning_level=none。"
        else:
            answer = f"{record['record_time']} {record['city_name']}{record['county_name']} SN 编号 {record['device_sn']} 土壤墒情仪监测到相对含水量 {record['water20cm']}%，预警等级 {status['display_label']}，请相关主体关注！"
        return self._response("soil_warning_generation", "soil_warning_answer", answer, session_id, turn_id)

    def _advice_answer(self, text: str, device_sn: str | None, session_id: str, turn_id: int) -> dict[str, Any]:
        answer = "建议：先结合最近墒情记录确认地块水分状态；如偏旱，优先小水慢灌；如偏湿，注意排水降渍。该建议仅作管理参考，具体措施需结合现场土壤、作物和天气情况。"
        return self._response("soil_management_advice", "soil_advice_answer", answer, session_id, turn_id)


    def get_summary_payload(self) -> dict[str, Any]:
        records = self.repository.latest_records()
        latest_time = records[0].get("record_time") if records else "暂无"
        water_values = [float(r["water20cm"]) for r in records if r.get("water20cm") is not None]
        avg_water = round(mean(water_values), 2) if water_values else None
        devices = []
        risky = 0
        for record in records[:10]:
            status = self._status_for_record(record)
            if status["soil_status"] != "not_triggered":
                risky += 1
            devices.append({**record, **status})
        return {
            "latest_time": latest_time,
            "total_records": len(records),
            "risky_devices": risky,
            "avg_water20cm": avg_water,
            "devices": devices,
        }

    def _status_for_record(self, record: dict[str, Any]) -> dict[str, str]:
        water20 = float(record.get("water20cm") or 0)
        if water20 < 50:
            return {"soil_status": "heavy_drought", "warning_level": "heavy_drought", "display_label": "重旱"}
        if water20 >= 150:
            return {"soil_status": "waterlogging", "warning_level": "waterlogging", "display_label": "涝渍"}
        return {"soil_status": "not_triggered", "warning_level": "none", "display_label": "未达到预警条件"}

    def _response(self, intent: str, answer_type: str, final_answer: str, session_id: str, turn_id: int, *, should_query: bool = True, input_type: str = "business_direct") -> dict[str, Any]:
        return {
            "session_id": session_id,
            "turn_id": turn_id,
            "input_type": input_type,
            "intent": intent,
            "answer_type": answer_type,
            "final_answer": final_answer,
            "should_query": should_query,
            "status": "ok",
        }
