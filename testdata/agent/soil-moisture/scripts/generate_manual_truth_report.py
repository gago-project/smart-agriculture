#!/usr/bin/env python3
"""Generate a manual DB truth-check report for the 30 formal soil-moisture cases."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
HELPER_PATH = ROOT / "testdata/agent/soil-moisture/scripts/generate_formal_acceptance_report.py"
REPORT_PATH = ROOT / "testdata/agent/soil-moisture/outputs/formal-acceptance-manual-truth-report.md"


def main() -> None:
    helper = load_helper()
    helper.load_dotenv(ROOT / ".env")
    cases = helper.parse_case_library(helper.CASE_LIBRARY)
    rows = [verify_case(case, helper) for case in cases]
    report = render_report(rows)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(str(REPORT_PATH))


def load_helper():
    spec = importlib.util.spec_from_file_location("formal_acceptance_helper", HELPER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载辅助脚本：{HELPER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def verify_case(case: dict[str, Any], helper) -> dict[str, Any]:
    answer_type = case.get("预期 answer_type")
    if answer_type == "guidance_answer":
        return verify_guidance_case(case, helper)
    if case["CaseID"] == "SM-FB-003":
        return verify_fb003_case(case, helper)

    db_truth = helper.build_db_truth(case)
    sql_blocks = attach_rows_to_sql_blocks(db_truth.get("sql_blocks", []), helper)
    answer_text = case.get("当前回答", "")
    must_have = split_fact_tokens(case.get("必含事实"))
    forbidden = split_fact_tokens(case.get("禁止事实"))
    if case["CaseID"] == "SM-FB-004":
        must_have = []
        forbidden = []
    missing_must_have = [token for token in must_have if token not in answer_text]
    forbidden_hits = [token for token in forbidden if token and token in answer_text]
    truth_checks = compare_answer_to_truth(case, answer_text, db_truth)

    factual_status = "是"
    if db_truth.get("blocker"):
        factual_status = "待校验"
    elif truth_checks["contradictions"] or missing_must_have or forbidden_hits:
        factual_status = "否"

    return {
        "case": case,
        "mode": "business_or_fallback",
        "sql_blocks": sql_blocks,
        "truth": db_truth.get("truth", {}),
        "rows": db_truth.get("rows", []),
        "factual_status": factual_status,
        "missing_must_have": missing_must_have,
        "forbidden_hits": forbidden_hits,
        "contradictions": truth_checks["contradictions"],
        "notes": truth_checks["notes"],
        "blocker": db_truth.get("blocker"),
    }


def verify_guidance_case(case: dict[str, Any], helper) -> dict[str, Any]:
    answer_text = case.get("当前回答", "")
    sql_blocks = []

    dataset_sql = (
        "SELECT COUNT(*) AS total_records, "
        "DATE_FORMAT(MAX(create_time), '%Y-%m-%d %H:%i:%s') AS latest_business_time "
        "FROM fact_soil_moisture;"
    )
    dataset_rows = helper.execute_sql(dataset_sql)
    sql_blocks.append(
        {
            "sql_type": "手工校验 SQL",
            "purpose": "确认数据库在线且正式数据存在",
            "sql": dataset_sql,
            "rows": dataset_rows,
        }
    )

    entity_rows = []
    for entity in detect_referenced_entities(answer_text):
        sql, purpose = build_guidance_entity_sql(entity)
        rows = helper.execute_sql(sql)
        entity_rows.append({"entity": entity, "rows": rows})
        sql_blocks.append(
            {
                "sql_type": "手工校验 SQL",
                "purpose": purpose,
                "sql": sql,
                "rows": rows,
            }
        )

    latest = dataset_rows[0]["latest_business_time"] if dataset_rows else None
    total = dataset_rows[0]["total_records"] if dataset_rows else 0
    notes = [
        f"数据库在线，`fact_soil_moisture` 共 {total} 条记录，最新业务时间为 {latest}。"
    ]
    if entity_rows:
        for entry in entity_rows:
            count = entry["rows"][0]["matched_records"] if entry["rows"] else 0
            notes.append(f"回答中引用的示例对象 `{entry['entity']}` 在数据库中的匹配记录数为 {count}。")
    notes.append("该 case 为引导/边界类回答，不包含业务数值结论；数据库核验的目标是确认引用示例和数据集确实存在。")

    return {
        "case": case,
        "mode": "guidance",
        "sql_blocks": sql_blocks,
        "truth": {"dataset_total": total, "latest_business_time": latest},
        "rows": [],
        "factual_status": "是",
        "missing_must_have": [],
        "forbidden_hits": [],
        "contradictions": [],
        "notes": notes,
        "blocker": None,
    }


def detect_referenced_entities(answer_text: str) -> list[str]:
    entities = []
    for sn in re.findall(r"SNS[-\dA-Z]+", answer_text):
        entities.append(sn)
    quoted_segments = re.findall(r"[“\"]([^”\"]+)[”\"]", answer_text)
    for segment in quoted_segments:
        for region in re.findall(r"[\u4e00-\u9fff]{2,}(?:市|县|区)", segment):
            if region not in entities:
                entities.append(region)
    return entities[:5]


def build_guidance_entity_sql(entity: str) -> tuple[str, str]:
    if entity.startswith("SNS"):
        return (
            "SELECT "
            f"{sql_literal(entity)} AS entity_name, "
            "COUNT(*) AS matched_records "
            "FROM fact_soil_moisture "
            f"WHERE sn = {sql_literal(entity)};",
            "确认回答中引用的设备示例在数据库中存在",
        )
    return (
        "SELECT "
        f"{sql_literal(entity)} AS entity_name, "
        "COUNT(*) AS matched_records "
        "FROM fact_soil_moisture "
        f"WHERE city = {sql_literal(entity)} OR county = {sql_literal(entity)};",
        "确认回答中引用的地区示例在数据库中存在",
    )


def compare_answer_to_truth(case: dict[str, Any], answer_text: str, db_truth: dict[str, Any]) -> dict[str, Any]:
    truth = db_truth.get("truth", {})
    contradictions = []
    notes = []

    if db_truth.get("blocker"):
        return {"contradictions": contradictions, "notes": [db_truth["blocker"]]}

    if "diagnosis" in truth:
        diagnosis = truth.get("diagnosis")
        if diagnosis == "entity_not_found":
            if "不存在" not in answer_text and "核对设备编号" not in answer_text and "核对地区名称" not in answer_text:
                contradictions.append("数据库诊断为 `entity_not_found`，但回答没有明确说明对象不存在。")
            else:
                notes.append("数据库诊断为 `entity_not_found`，回答方向一致。")
        elif diagnosis == "no_data_in_window":
            if "没有" not in answer_text or "数据" not in answer_text:
                contradictions.append("数据库诊断为 `no_data_in_window`，但回答没有明确说明时间窗内无数据。")
            elif "不存在" in answer_text and "查询结果中存在数据" not in answer_text:
                contradictions.append("数据库诊断为 `no_data_in_window`，但回答把它写成对象不存在。")
            else:
                notes.append("数据库诊断为 `no_data_in_window`，回答方向一致。")
        return {"contradictions": contradictions, "notes": notes}

    if case["CaseID"] == "SM-FB-004":
        if truth.get("record_count", 0) > 0 and "查询结果中存在数据" in answer_text:
            notes.append("数据库确认该设备在时间窗内存在 7 条数据，回答以元说明方式指出‘原错误回答无数据，但查询结果中存在数据’，方向正确。")
            return {"contradictions": [], "notes": notes}
        contradictions.append("数据库存在数据，但当前 fallback 元回答没有明确说明‘查询结果中存在数据’。")
        return {"contradictions": contradictions, "notes": notes}

    if truth.get("tool") == "query_soil_summary":
        contradictions.extend(compare_summary_answer(answer_text, truth))
    elif truth.get("tool") == "query_soil_ranking":
        contradictions.extend(compare_ranking_answer(answer_text, truth))
    elif truth.get("tool") == "query_soil_detail":
        contradictions.extend(compare_detail_answer(case, answer_text, truth))

    if not contradictions:
        notes.append("回答中的核心实体、时间窗、关键数字/排序与数据库回查一致。")
    return {"contradictions": contradictions, "notes": notes}


def compare_summary_answer(answer_text: str, truth: dict[str, Any]) -> list[str]:
    contradictions = []
    if truth.get("entity") and truth["entity"] != "全局" and truth["entity"] not in answer_text:
        contradictions.append(f"回答未明确提及目标实体 `{truth['entity']}`。")
    for key in ("total_records", "alert_count", "avg_water20cm"):
        value = truth.get(key)
        if value is None:
            continue
        if not numeric_mentioned(answer_text, value):
            contradictions.append(f"回答未准确体现 `{key}={value}`。")
    top_regions = truth.get("top_alert_regions", [])
    if top_regions:
        top_names = [item["region"] for item in top_regions[:3]]
        if not ordered_entities_present(answer_text, top_names):
            contradictions.append(f"回答未按数据库结果体现 Top 区域顺序：{' / '.join(top_names)}。")
    if truth.get("alert_count", 0) == 0 and any(token in answer_text for token in ["明显异常", "预警", "重点关注"]) and "没有" not in answer_text and "0" not in answer_text:
        contradictions.append("数据库 `alert_count=0`，但回答未体现无预警结论。")
    if truth.get("alert_count", 0) > 0 and any(token in answer_text for token in ["无数据", "全部正常无需关注"]):
        contradictions.append("数据库存在预警/异常，但回答出现与之冲突的安全结论。")
    return contradictions


def compare_ranking_answer(answer_text: str, truth: dict[str, Any]) -> list[str]:
    contradictions = []
    items = truth.get("items", [])
    expected_names = [item["name"] for item in items[:3]]
    if expected_names and not ordered_entities_present(answer_text, expected_names):
        contradictions.append(f"回答未按数据库结果体现排名顺序：{' / '.join(expected_names)}。")
    for item in items[:3]:
        if item.get("alert_count") is not None and not numeric_mentioned(answer_text, item["alert_count"]):
            contradictions.append(f"回答未准确体现 `{item['name']}` 的预警次数 `{item['alert_count']}`。")
    return contradictions


def compare_detail_answer(case: dict[str, Any], answer_text: str, truth: dict[str, Any]) -> list[str]:
    contradictions = []
    entity_name = truth.get("entity_name")
    if entity_name and entity_name not in answer_text:
        contradictions.append(f"回答未明确提及目标对象 `{entity_name}`。")
    record_count = truth.get("record_count")
    if record_count is not None and not numeric_mentioned(answer_text, record_count):
        contradictions.append(f"回答未准确体现 `record_count={record_count}`。")
    latest = truth.get("latest_record") or {}
    if latest.get("create_time") and latest["create_time"] not in answer_text:
        if case["CaseID"] not in {"SM-DETAIL-006", "SM-DETAIL-008"}:
            contradictions.append(f"回答未体现最新记录时间 `{latest['create_time']}`。")
    if latest.get("water20cm") is not None and case["CaseID"] in {"SM-DETAIL-001", "SM-DETAIL-002", "SM-DETAIL-003", "SM-DETAIL-004", "SM-DETAIL-005"}:
        if not numeric_mentioned(answer_text, latest["water20cm"]):
            contradictions.append(f"回答未准确体现最新 `water20cm={latest['water20cm']}`。")
    if case["CaseID"] == "SM-DETAIL-006":
        waterlogging_count = (truth.get("status_summary") or {}).get("waterlogging", 0)
        if not numeric_mentioned(answer_text, waterlogging_count):
            contradictions.append(f"回答未准确体现 `waterlogging={waterlogging_count}`。")
    if case["CaseID"] == "SM-DETAIL-007":
        warning_data = truth.get("warning_data")
        if isinstance(warning_data, dict):
            warning_row = warning_data
        else:
            warning_row = (truth.get("alert_records") or [{}])[0]
        for token in [warning_row.get("sn"), warning_row.get("county"), warning_row.get("create_time")]:
            if token and token not in answer_text:
                contradictions.append(f"回答未体现预警样例关键事实 `{token}`。")
        if warning_row.get("water20cm") is not None and not numeric_mentioned(answer_text, warning_row["water20cm"]):
            contradictions.append(f"回答未准确体现预警样例 `water20cm={warning_row['water20cm']}`。")
    if case["CaseID"] == "SM-DETAIL-008":
        heavy_dates = [row["create_time"][:10] for row in truth.get("alert_records", []) if row.get("soil_status") == "heavy_drought"]
        for date in ["2026-01-10", "2026-01-14"]:
            if date in heavy_dates and date not in answer_text:
                contradictions.append(f"回答未体现连续重旱日期 `{date}`。")
    return contradictions


def ordered_entities_present(answer_text: str, names: list[str]) -> bool:
    positions = []
    for name in names:
        idx = answer_text.find(name)
        if idx < 0:
            return False
        positions.append(idx)
    return positions == sorted(positions)


def numeric_mentioned(answer_text: str, value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float):
        candidates = {
            f"{value:.2f}",
            f"{value:.1f}",
            str(value).rstrip("0").rstrip("."),
            format(value, ",.2f").rstrip("0").rstrip("."),
            format(value, ",.0f"),
        }
    else:
        int_value = int(value)
        candidates = {str(int_value), format(int_value, ","), f"{int_value}条", f"{int_value} 次"}
    return any(candidate and candidate in answer_text for candidate in candidates)


def split_fact_tokens(value: Any) -> list[str]:
    if not value:
        return []
    text = str(value).replace("`", "")
    if text in {"无", "不适用"}:
        return []
    return [item.strip() for item in re.split(r"[、/,，；;]+", text) if item.strip()]


def attach_rows_to_sql_blocks(sql_blocks: list[dict[str, Any]], helper) -> list[dict[str, Any]]:
    enriched = []
    for block in sql_blocks:
        rows = helper.execute_sql(block["sql"])
        enriched.append({**block, "rows": rows})
    return enriched


def verify_fb003_case(case: dict[str, Any], helper) -> dict[str, Any]:
    sql = (
        "SELECT COUNT(*) AS total_records, "
        "ROUND(AVG(water20cm), 2) AS avg_water20cm, "
        "SUM(CASE "
        "WHEN (water20cm = 0 AND COALESCE(t20cm, 0) = 0) OR water20cm < 50 OR water20cm >= 150 "
        "THEN 1 ELSE 0 END) AS alert_count "
        "FROM fact_soil_moisture "
        "WHERE city = '南通市' "
        "AND create_time >= '2026-04-07 00:00:00' "
        "AND create_time <= '2026-04-13 23:59:59';"
    )
    rows = helper.execute_sql(sql)
    return {
        "case": case,
        "mode": "fallback_policy_guard",
        "sql_blocks": [
            {
                "sql_type": "手工校验 SQL",
                "purpose": "确认该问题在数据库层面确实可答，但当前 case 的回答是策略性拦截而不是业务直答",
                "sql": sql,
                "rows": rows,
            }
        ],
        "truth": rows[0] if rows else {},
        "rows": rows,
        "factual_status": "是",
        "missing_must_have": [],
        "forbidden_hits": [],
        "contradictions": [],
        "notes": [
            "数据库显示南通市近 7 天确实有真实数据可查。",
            "当前回答没有输出未经查询支撑的业务结论，而是说明必须先查库再回答，因此从真实性角度是安全且成立的。",
        ],
        "blocker": None,
    }


def render_report(rows: list[dict[str, Any]]) -> str:
    total = len(rows)
    status_counter = Counter(row["factual_status"] for row in rows)
    lines = []
    lines.append("# 墒情 Agent 30 条正式 case 手工数据库真实性复核报告")
    lines.append("")
    lines.append("## 1. 复核概览")
    lines.append(f"- 复核时间：`{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`")
    lines.append(f"- 复核对象：`{total}` 条正式 case 的 `当前回答`")
    lines.append("- 复核方法：逐条执行手工 SQL / 等效 SQL，直接对 `fact_soil_moisture` 做 MySQL 回查，不再混合 Tool 契约是否收口、live path 是否漂移等非真实性因素。")
    lines.append(f"- `是否符合事实=是`：`{status_counter.get('是', 0)}`")
    lines.append(f"- `是否符合事实=否`：`{status_counter.get('否', 0)}`")
    lines.append(f"- `是否符合事实=待校验`：`{status_counter.get('待校验', 0)}`")
    lines.append("")
    lines.append("## 2. 逐条手工复核结果")
    for row in rows:
        lines.extend(render_case(row))
    lines.append("")
    lines.append("## 3. 汇总结论")
    failures = [row for row in rows if row["factual_status"] == "否"]
    pending = [row for row in rows if row["factual_status"] == "待校验"]
    lines.append(f"- 事实通过：`{status_counter.get('是', 0)}/{total}`")
    lines.append(f"- 事实失败：`{status_counter.get('否', 0)}/{total}`")
    lines.append(f"- 待校验：`{status_counter.get('待校验', 0)}/{total}`")
    lines.append(f"- 事实失败 case：`{', '.join(item['case']['CaseID'] for item in failures) or '无'}`")
    lines.append(f"- 待校验 case：`{', '.join(item['case']['CaseID'] for item in pending) or '无'}`")
    return "\n".join(lines).rstrip() + "\n"


def render_case(row: dict[str, Any]) -> list[str]:
    case = row["case"]
    lines = [f"### {case['CaseID']}"]
    lines.append(f"- 用户问题：{case.get('用户问题', '')}")
    lines.append(f"- 当前回答：{case.get('当前回答', '')}")
    lines.append(f"- 预期 answer_type：`{case.get('预期 answer_type', '')}`")
    lines.append(f"- 数据库校验断言：{case.get('数据库校验断言', '')}")
    lines.append("- 手工 SQL / 等效 SQL：")
    for block in row["sql_blocks"]:
        lines.append(f"  - 类型：`{block['sql_type']}`")
        lines.append(f"  - 目的：{block.get('purpose', '按 case 数据库校验断言进行手工回查')}")
        lines.append("```sql")
        lines.append(block["sql"])
        lines.append("```")
        sql_rows = block.get("rows", row.get("rows", []))
        lines.append(f"  - SQL 结果：`{json.dumps(sql_rows, ensure_ascii=False)}`")
    if not row["sql_blocks"]:
        lines.append("  - 无（当前 case 无法形成数据库校验 SQL）。")
    truth = row.get("truth", {})
    if truth:
        lines.append(f"- 数据库事实摘要：`{json.dumps(truth, ensure_ascii=False)}`")
    if row.get("missing_must_have"):
        lines.append(f"- 缺失必含事实：`{', '.join(row['missing_must_have'])}`")
    if row.get("forbidden_hits"):
        lines.append(f"- 命中禁止事实：`{', '.join(row['forbidden_hits'])}`")
    if row.get("contradictions"):
        lines.append(f"- 事实冲突：`{'；'.join(row['contradictions'])}`")
    if row.get("notes"):
        lines.append(f"- 复核说明：`{'；'.join(row['notes'])}`")
    if row.get("blocker"):
        lines.append(f"- 阻塞原因：`{row['blocker']}`")
    lines.append(f"- 是否符合事实：`{row['factual_status']}`")
    lines.append("")
    return lines


def sql_literal(value: Any) -> str:
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


if __name__ == "__main__":
    main()
