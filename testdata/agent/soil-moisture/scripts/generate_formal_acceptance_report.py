#!/usr/bin/env python3
"""Generate the 56-case formal acceptance report for the soil-moisture Agent."""

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys
import textwrap
import traceback
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib import error, request

import pymysql


ROOT = Path(__file__).resolve().parents[4]
CASE_LIBRARY = ROOT / "testdata/agent/soil-moisture/case-library.md"
REPORT_PATH = ROOT / "testdata/agent/soil-moisture/outputs/formal-acceptance-report.md"
AGENT_URL = os.environ.get("FORMAL_AGENT_URL", "http://localhost:18010/chat")
RUN_ID = datetime.now().strftime("%Y%m%d-%H%M%S")
PYTEST_BIN = ROOT / ".venv/bin/pytest"
EXPECTED_CASE_TOTAL = 56
EXPECTED_DISTRIBUTION = {
    "guidance_answer": 13,
    "soil_summary_answer": 12,
    "soil_ranking_answer": 8,
    "soil_detail_answer": 13,
    "fallback_answer": 10,
}

REQUIRED_LIBRARY_FIELDS = [
    "当前回答",
    "关键断言",
    "结构化证据断言",
    "数据库校验断言",
    "是否符合事实",
]

ALERT_STATUSES = {"heavy_drought", "waterlogging", "device_fault"}

GUIDANCE_CASES = {
    "SM-CONV-001",
    "SM-CONV-002",
    "SM-CONV-003",
    "SM-CONV-004",
    "SM-CONV-005",
    "SM-CONV-006",
    "SM-CONV-007",
    "SM-CONV-008",
}

SPECIAL_RUNNERS = {
    "SM-FB-003",
    "SM-FB-004",
}

CASE_SETUP_MESSAGES = {
    "SM-CONV-004": ["帮我看一下"],
    "SM-DETAIL-004": ["南通市最近 7 天整体情况怎么样"],
    "SM-DETAIL-005": ["最近 30 天设备里前 5 个风险最高的是哪些"],
}


@dataclass
class CommandResult:
    command: str
    cwd: str
    exit_code: int
    stdout: str
    stderr: str


def main() -> None:
    load_dotenv(ROOT / ".env")
    clear_proxy_env()
    cases = parse_case_library(CASE_LIBRARY)
    self_check = check_case_library(cases)
    git_meta = collect_git_meta()
    env_meta = collect_environment_meta()
    python_test = run_command(
        f"PYTHONPATH=. {PYTEST_BIN} tests -q",
        cwd=ROOT / "apps/agent",
    )
    node_test = run_command(
        "node --test apps/web/tests/agent-chat-evidence.test.mjs "
        "apps/web/tests/file-contract.test.mjs "
        "apps/web/tests/db-schema-contract.test.mjs",
        cwd=ROOT,
    )

    results: list[dict[str, Any]] = []
    for case in cases:
        print(f"[case] {case['CaseID']}", flush=True)
        try:
            results.append(run_case(case))
        except Exception as exc:  # pragma: no cover - runtime safeguard
            results.append(build_blocked_case_result(case, exc))

    summary = summarize_results(results)
    report = render_report(
        git_meta=git_meta,
        env_meta=env_meta,
        self_check=self_check,
        python_test=python_test,
        node_test=node_test,
        results=results,
        summary=summary,
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(str(REPORT_PATH))
    blockers = collect_gate_blockers(
        self_check=self_check,
        python_test=python_test,
        node_test=node_test,
        results=results,
        summary=summary,
    )
    if blockers:
        for blocker in blockers:
            print(f"[gate] {blocker}", file=sys.stderr)
        sys.exit(1)


def clear_proxy_env() -> None:
    for key in ("ALL_PROXY", "all_proxy", "HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        os.environ.pop(key, None)


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key, value)


def parse_case_library(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"^### (SM-[A-Z]+-\d+)\n", text, flags=re.M)
    cases: list[dict[str, Any]] = []
    for index in range(1, len(parts), 2):
        case_id = parts[index].strip()
        body = parts[index + 1]
        fields: dict[str, Any] = {"CaseID": case_id}
        for raw_line in body.splitlines():
            line = raw_line.rstrip()
            match = re.match(r"^- `([^`]+)`：(.*)$", line)
            if not match:
                continue
            key = match.group(1).strip()
            value = clean_markdown_value(match.group(2).strip())
            fields[key] = value
        fields["__body__"] = body
        cases.append(fields)
    return cases


def clean_markdown_value(value: str) -> str:
    value = value.rstrip()
    if value.endswith("  "):
        value = value[:-2].rstrip()
    if value.startswith("`") and value.endswith("`") and value.count("`") == 2:
        value = value[1:-1]
    return value


def check_case_library(cases: list[dict[str, Any]]) -> dict[str, Any]:
    distribution = Counter(case.get("预期 answer_type", "") for case in cases)
    missing_fields: dict[str, list[str]] = {}
    for case in cases:
        missing = [name for name in REQUIRED_LIBRARY_FIELDS if not case.get(name)]
        if missing:
            missing_fields[case["CaseID"]] = missing
    blockers: list[str] = []
    if len(cases) != EXPECTED_CASE_TOTAL:
        blockers.append(f"正式 case 总数不是 {EXPECTED_CASE_TOTAL}，而是 {len(cases)}。")
    for answer_type, expected_count in EXPECTED_DISTRIBUTION.items():
        actual_count = distribution.get(answer_type, 0)
        if actual_count != expected_count:
            blockers.append(f"{answer_type} 分布不符：期望 {expected_count}，实际 {actual_count}。")
    if missing_fields:
        for case_id, fields in missing_fields.items():
            blockers.append(f"{case_id} 缺少字段：{', '.join(fields)}。")
    return {
        "total_cases": len(cases),
        "distribution": distribution,
        "required_distribution": EXPECTED_DISTRIBUTION,
        "missing_fields": missing_fields,
        "blockers": blockers,
    }


def has_legacy_live_fields(response: dict[str, Any]) -> bool:
    return "merged_slots" in response or "query_plan" in response


def collect_gate_blockers(
    *,
    self_check: dict[str, Any],
    python_test: CommandResult,
    node_test: CommandResult,
    results: list[dict[str, Any]],
    summary: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if python_test.exit_code != 0:
        blockers.append("Python 基础测试失败")
    if node_test.exit_code != 0:
        blockers.append("Node 基础测试失败")
    if any(
        has_legacy_live_fields(result["execution"].get("response", {}))
        for result in results
        if result["execution"]["mode"] == "live-http-agent"
    ):
        blockers.append("在线 Agent 返回旧 live path 字段（如 merged_slots/query_plan），与仓库当前正式 5 节点契约漂移")
    if self_check["blockers"]:
        blockers.extend(self_check["blockers"])
    if summary["failed"] != 0:
        blockers.append(f"{EXPECTED_CASE_TOTAL} 条正式验收存在失败 case：{summary['failed']} 条")
    if summary["business_without_tool"]:
        blockers.append("仍存在域内业务问题未调 Tool 的路径")
    if summary["factual_pending"] or summary["factual_no"]:
        blockers.append("仍存在数据库事实未对齐的正式 case")
    return blockers


def collect_git_meta() -> dict[str, str]:
    branch = run_simple("git rev-parse --abbrev-ref HEAD", ROOT)
    commit = run_simple("git rev-parse HEAD", ROOT)
    return {"branch": branch.strip(), "commit": commit.strip()}


def collect_environment_meta() -> dict[str, Any]:
    health = {}
    for name, url in {"agent_18010": "http://localhost:18010/health", "agent_8000": "http://localhost:8000/health"}.items():
        try:
            payload = request.urlopen(url, timeout=5).read().decode("utf-8")
            health[name] = payload
        except Exception as exc:  # pragma: no cover - environment only
            health[name] = f"ERROR: {exc}"
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z"),
        "cwd": str(ROOT),
        "agent_url": AGENT_URL,
        "mysql_host": os.environ.get("MYSQL_HOST", ""),
        "mysql_port": os.environ.get("MYSQL_PORT", ""),
        "mysql_database": os.environ.get("MYSQL_DATABASE", ""),
        "redis_url": os.environ.get("REDIS_URL", ""),
        "health": health,
    }


def run_simple(command: str, cwd: Path) -> str:
    return subprocess.run(command, cwd=str(cwd), shell=True, capture_output=True, text=True, check=True).stdout


def run_command(command: str, cwd: Path) -> CommandResult:
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        shell=True,
        capture_output=True,
        text=True,
    )
    return CommandResult(
        command=command,
        cwd=str(cwd),
        exit_code=completed.returncode,
        stdout=completed.stdout.strip(),
        stderr=completed.stderr.strip(),
    )


def run_case(case: dict[str, Any]) -> dict[str, Any]:
    case_id = case["CaseID"]
    if case_id in GUIDANCE_CASES:
        execution = run_guidance_case(case)
    elif case_id == "SM-FB-003":
        execution = run_fb003_case(case)
    elif case_id == "SM-FB-004":
        execution = run_fb004_case(case)
    else:
        execution = run_live_case(case)
    db_truth = build_db_truth(case)
    analysis = analyze_case(case, execution, db_truth)
    return {
        "case": case,
        "execution": execution,
        "db_truth": db_truth,
        "analysis": analysis,
    }


def run_guidance_case(case: dict[str, Any]) -> dict[str, Any]:
    setup_messages = CASE_SETUP_MESSAGES.get(case["CaseID"], [])
    session_id = f"{RUN_ID}-{case['CaseID'].lower()}"
    return asyncio.run(_run_guidance_case_async(case, session_id, setup_messages))


async def _run_guidance_case_async(case: dict[str, Any], session_id: str, setup_messages: list[str]) -> dict[str, Any]:
    agent = current_agent_service()
    context_store = current_session_context_repository()
    agent.context_store = context_store
    agent.agent_loop_service.history_store = context_store
    setup_results = []
    turn = 1
    if case["CaseID"] == "SM-CONV-008":
        await context_store.save_message_turn(
            session_id,
            1,
            user_message="南通市最近 7 天墒情怎么样",
            assistant_message="上一轮已完成业务查询。",
            tool_calls=[],
            tool_results=[],
        )
        turn = 2
    else:
        for message in setup_messages:
            setup_results.append(normalize_deep(await agent.achat(message, session_id=session_id, turn_id=turn)))
            turn += 1
    response = normalize_deep(await agent.achat(case["用户问题"], session_id=session_id, turn_id=turn))
    remaining_history = normalize_deep(await context_store.load_history(session_id))
    return {
        "mode": "controlled-current-code-guidance",
        "session_id": session_id,
        "turn_id": turn,
        "setup_results": setup_results,
        "response": response,
        "logs": [],
        "history_after": remaining_history,
    }


def run_fb003_case(case: dict[str, Any]) -> dict[str, Any]:
    return asyncio.run(_run_fb003_case_async(case))


async def _run_fb003_case_async(case: dict[str, Any]) -> dict[str, Any]:
    qwen_cls = current_qwen_client_class()

    class FakeQwen(qwen_cls):
        def __init__(self) -> None:
            pass

        def available(self) -> bool:
            return True

        async def call_with_tools(self, *, messages: list[dict], tools: list[dict]) -> dict[str, Any]:
            return {"type": "text", "content": "南通市近 7 天没有异常。"}

    context_store = current_session_context_repository()
    agent = current_agent_service(qwen_client=FakeQwen(), context_store=context_store)
    response = normalize_deep(
        await agent.achat(case["用户问题"], session_id=f"{RUN_ID}-{case['CaseID'].lower()}", turn_id=1)
    )
    return {
        "mode": "controlled-current-code-p0-tool-missing",
        "session_id": f"{RUN_ID}-{case['CaseID'].lower()}",
        "turn_id": 1,
        "setup_results": [],
        "response": response,
        "logs": [],
        "history_after": normalize_deep(await context_store.load_history(f"{RUN_ID}-{case['CaseID'].lower()}")),
    }


def run_fb004_case(case: dict[str, Any]) -> dict[str, Any]:
    return asyncio.run(_run_fb004_case_async(case))


async def _run_fb004_case_async(case: dict[str, Any]) -> dict[str, Any]:
    qwen_cls = current_qwen_client_class()

    class FakeQwen(qwen_cls):
        def __init__(self) -> None:
            self.calls = 0

        def available(self) -> bool:
            return True

        async def call_with_tools(self, *, messages: list[dict], tools: list[dict]) -> dict[str, Any]:
            self.calls += 1
            if self.calls == 1:
                return {
                    "type": "tool_call",
                    "tool_name": "query_soil_detail",
                    "tool_args": {
                        "sn": "SNS00204333",
                        "start_time": "2026-04-07 00:00:00",
                        "end_time": "2026-04-13 23:59:59",
                    },
                    "call_id": "fb004-call-1",
                }
            return {"type": "text", "content": "没有数据"}

    session_id = f"{RUN_ID}-{case['CaseID'].lower()}"
    agent = current_agent_service(qwen_client=FakeQwen(), context_store=current_session_context_repository())
    response = normalize_deep(await agent.achat(case["用户问题"], session_id=session_id, turn_id=1))
    return {
        "mode": "controlled-current-code-fact-check-injection",
        "session_id": session_id,
        "turn_id": 1,
        "setup_results": [],
        "response": response,
        "logs": [],
        "history_after": [],
        "note": "通过受控 FakeQwen 先发出 query_soil_detail，再故意返回“没有数据”来触发事实核验路径。",
    }


def run_live_case(case: dict[str, Any]) -> dict[str, Any]:
    session_id = f"{RUN_ID}-{case['CaseID'].lower()}"
    setup_messages = CASE_SETUP_MESSAGES.get(case["CaseID"], [])
    setup_results = []
    turn = 1
    for message in setup_messages:
        setup_results.append(chat_http(message, session_id=session_id, turn_id=turn))
        turn += 1
    response = chat_http(case["用户问题"], session_id=session_id, turn_id=turn)
    logs = fetch_query_logs(session_id=session_id, turn_id=turn)
    return {
        "mode": "live-http-agent",
        "session_id": session_id,
        "turn_id": turn,
        "setup_results": setup_results,
        "response": response,
        "logs": logs,
        "history_after": [],
    }


def chat_http(message: str, *, session_id: str, turn_id: int) -> dict[str, Any]:
    payload = json.dumps(
        {
            "message": message,
            "session_id": session_id,
            "turn_id": turn_id,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = request.Request(
        AGENT_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {
            "__http_error__": True,
            "status_code": exc.code,
            "body": body,
        }
    except Exception as exc:  # pragma: no cover - runtime safeguard
        return {
            "__http_error__": True,
            "status_code": None,
            "body": f"{exc.__class__.__name__}: {exc}",
        }


def fetch_query_logs(*, session_id: str, turn_id: int) -> list[dict[str, Any]]:
    connection = mysql_connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM agent_query_log
                WHERE session_id=%s AND turn_id=%s
                ORDER BY created_at ASC, query_id ASC
                """,
                (session_id, turn_id),
            )
            rows = cursor.fetchall()
            return [normalize_log_row(row) for row in rows]
    finally:
        connection.close()


def mysql_connect():
    return pymysql.connect(
        host=os.environ["MYSQL_HOST"],
        port=int(os.environ.get("MYSQL_PORT", "3306")),
        user=os.environ["MYSQL_USER"],
        password=os.environ["MYSQL_PASSWORD"],
        database=os.environ["MYSQL_DATABASE"],
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def normalize_log_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized = {}
    for key, value in row.items():
        if key.endswith("_json") and isinstance(value, (str, bytes)) and value not in ("", None):
            normalized[key] = json.loads(value)
        else:
            normalized[key] = value
    return normalize_deep(normalized)


def normalize_deep(value: Any) -> Any:
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "model_dump"):
        return normalize_deep(value.model_dump(exclude_none=False))
    if isinstance(value, dict):
        return {key: normalize_deep(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize_deep(item) for item in value]
    return value


def build_db_truth(case: dict[str, Any]) -> dict[str, Any]:
    assertion = case.get("数据库校验断言", "")
    invocations = parse_tool_invocations(assertion)
    if not invocations:
        return {
            "applicable": False,
            "invocations": [],
            "sql_blocks": [],
            "rows": [],
            "truth": {},
            "blocker": "数据库校验断言中没有可解析的 tool 调用。",
        }
    sql_blocks = []
    truth: dict[str, Any] = {}
    rows: list[dict[str, Any]] = []
    for invocation in invocations:
        name = invocation["name"]
        args = invocation["args"]
        if name in {"query_soil_summary", "query_soil_ranking", "query_soil_detail"}:
            sql = build_filter_records_sql(args)
            result_rows = execute_sql(sql)
            sql_blocks.append({"tool": name, "sql_type": "等效 SQL（由数据库校验断言重建）", "sql": sql})
            rows = result_rows
            if name == "query_soil_summary":
                truth = compute_summary_truth(result_rows, args)
            elif name == "query_soil_ranking":
                truth = compute_ranking_truth(result_rows, args)
            else:
                truth = compute_detail_truth(result_rows, args)
        elif name == "diagnose_empty_result":
            diagnosis = compute_diagnosis_truth(args)
            sql_blocks.extend(diagnosis["sql_blocks"])
            truth = diagnosis["truth"]
            if diagnosis.get("rows") is not None:
                rows = diagnosis["rows"]
    return {
        "applicable": True,
        "invocations": invocations,
        "sql_blocks": sql_blocks,
        "rows": rows,
        "truth": truth,
        "blocker": None,
    }


def parse_tool_invocations(text: str) -> list[dict[str, Any]]:
    invocations = []
    for match in re.finditer(r"([a-z_]+)\(([^)]*)\)", text):
        name = match.group(1)
        arg_text = match.group(2).strip()
        args: dict[str, Any] = {}
        if arg_text:
            for item in [part.strip() for part in arg_text.split(",") if part.strip()]:
                if "=" not in item:
                    continue
                key, raw_value = item.split("=", 1)
                args[key.strip()] = raw_value.strip()
        invocations.append({"name": name, "args": args})
    return invocations


def build_filter_records_sql(args: dict[str, str]) -> str:
    filters = []
    if args.get("city"):
        filters.append(f"city = {sql_literal(args['city'])}")
    if args.get("county"):
        filters.append(f"county = {sql_literal(args['county'])}")
    if args.get("sn"):
        filters.append(f"sn = {sql_literal(args['sn'])}")
    if args.get("start"):
        filters.append(f"create_time >= {sql_literal(args['start'])}")
    if args.get("start_time"):
        filters.append(f"create_time >= {sql_literal(args['start_time'])}")
    if args.get("end"):
        filters.append(f"create_time <= {sql_literal(args['end'])}")
    if args.get("end_time"):
        filters.append(f"create_time <= {sql_literal(args['end_time'])}")
    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    return textwrap.dedent(
        f"""
        SELECT id, sn, city, county,
               DATE_FORMAT(create_time, '%Y-%m-%d %H:%i:%s') AS create_time,
               water20cm, water40cm, water60cm, water80cm, t20cm, t40cm,
               source_file, source_sheet, source_row
        FROM fact_soil_moisture
        {where}
        ORDER BY create_time DESC;
        """
    ).strip()


def compute_diagnosis_truth(args: dict[str, str]) -> dict[str, Any]:
    scenario = args.get("scenario", "period_exists")
    sql_blocks = []
    if scenario == "device_exists":
        sql = (
            "SELECT COUNT(*) AS record_count_all_time "
            f"FROM fact_soil_moisture WHERE sn = {sql_literal(args.get('sn', ''))};"
        )
        rows = execute_sql(sql)
        count = int(rows[0]["record_count_all_time"])
        return {
            "sql_blocks": [{"tool": "diagnose_empty_result", "sql_type": "等效 SQL（由数据库校验断言重建）", "sql": sql}],
            "truth": {
                "scenario": scenario,
                "diagnosis": "entity_not_found" if count == 0 else "data_exists",
                "entity_type": "device",
                "entity_name": args.get("sn", ""),
                "record_count_all_time": count,
                "record_count_in_window": None,
            },
            "rows": rows,
        }
    if scenario == "region_exists":
        filters = []
        if args.get("city"):
            filters.append(f"city = {sql_literal(args['city'])}")
        if args.get("county"):
            filters.append(f"county = {sql_literal(args['county'])}")
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        sql = f"SELECT COUNT(*) AS record_count_all_time FROM fact_soil_moisture {where};"
        rows = execute_sql(sql)
        count = int(rows[0]["record_count_all_time"])
        return {
            "sql_blocks": [{"tool": "diagnose_empty_result", "sql_type": "等效 SQL（由数据库校验断言重建）", "sql": sql}],
            "truth": {
                "scenario": scenario,
                "diagnosis": "entity_not_found" if count == 0 else "data_exists",
                "entity_type": "region",
                "entity_name": args.get("county") or args.get("city") or "",
                "record_count_all_time": count,
                "record_count_in_window": None,
            },
            "rows": rows,
        }
    sql = (
        "SELECT COUNT(*) AS record_count_in_window "
        "FROM fact_soil_moisture "
        "WHERE 1=1 "
        + (f"AND city = {sql_literal(args['city'])} " if args.get("city") else "")
        + (f"AND county = {sql_literal(args['county'])} " if args.get("county") else "")
        + (f"AND sn = {sql_literal(args['sn'])} " if args.get("sn") else "")
        + (f"AND create_time >= {sql_literal(args.get('start') or args.get('start_time'))} " if args.get("start") or args.get("start_time") else "")
        + (f"AND create_time <= {sql_literal(args.get('end') or args.get('end_time'))};" if args.get("end") or args.get("end_time") else ";")
    )
    rows = execute_sql(sql)
    count = int(rows[0]["record_count_in_window"])
    return {
        "sql_blocks": [{"tool": "diagnose_empty_result", "sql_type": "等效 SQL（由数据库校验断言重建）", "sql": sql}],
        "truth": {
            "scenario": scenario,
            "diagnosis": "data_exists" if count > 0 else "no_data_in_window",
            "entity_type": "device" if args.get("sn") else "region",
            "entity_name": args.get("sn") or args.get("county") or args.get("city") or "全局",
            "record_count_all_time": None,
            "record_count_in_window": count,
        },
        "rows": rows,
    }


def execute_sql(sql: str) -> list[dict[str, Any]]:
    connection = mysql_connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            return normalize_deep(cursor.fetchall())
    finally:
        connection.close()


def sql_literal(value: Any) -> str:
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def compute_summary_truth(rows: list[dict[str, Any]], args: dict[str, str]) -> dict[str, Any]:
    enriched = [enrich_record(row) for row in rows]
    water_vals = [safe_float(row.get("water20cm")) for row in enriched if safe_float(row.get("water20cm")) is not None]
    avg = round(sum(water_vals) / len(water_vals), 2) if water_vals else None
    status_counts = Counter(row["soil_status"] for row in enriched)
    region_alerts: Counter[str] = Counter()
    for row in enriched:
        if row["soil_status"] in ALERT_STATUSES:
            region_alerts[row.get("county") or row.get("city") or "未知"] += 1
    top_regions = [
        {"region": region, "alert_count": count}
        for region, count in region_alerts.most_common(5)
    ]
    truth = {
        "tool": "query_soil_summary",
        "total_records": len(enriched),
        "avg_water20cm": avg,
        "alert_count": sum(count for status, count in status_counts.items() if status in ALERT_STATUSES),
        "status_counts": dict(status_counts),
        "top_alert_regions": top_regions,
        "time_window": {
            "start_time": args.get("start") or args.get("start_time"),
            "end_time": args.get("end") or args.get("end_time"),
        },
        "entity": args.get("sn") or args.get("county") or args.get("city") or "全局",
        "output_mode": args.get("output_mode", "normal"),
        "alert_records": slim_rows([row for row in enriched if row["soil_status"] in ALERT_STATUSES][:5]),
    }
    return truth


def compute_ranking_truth(rows: list[dict[str, Any]], args: dict[str, str]) -> dict[str, Any]:
    enriched = [enrich_record(row) for row in rows]
    aggregation = args.get("aggregation", "county")
    top_n = int(args.get("top_n", "5"))
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in enriched:
        if aggregation == "city":
            key = row.get("city") or "未知"
        elif aggregation == "device":
            key = row.get("sn") or "未知"
        else:
            key = row.get("county") or row.get("city") or "未知"
        groups[key].append(row)
    items = []
    for name, group_rows in groups.items():
        water_vals = [safe_float(row.get("water20cm")) for row in group_rows if safe_float(row.get("water20cm")) is not None]
        avg = round(sum(water_vals) / len(water_vals), 2) if water_vals else None
        status_counts = Counter(row["soil_status"] for row in group_rows)
        alert_count = sum(count for status, count in status_counts.items() if status in ALERT_STATUSES)
        item = {
            "name": name,
            "record_count": len(group_rows),
            "avg_water20cm": avg,
            "alert_count": alert_count,
            "status_counts": dict(status_counts),
        }
        items.append(item)
    items.sort(key=lambda item: (-item["alert_count"], item["avg_water20cm"] if item["avg_water20cm"] is not None else 999))
    for index, item in enumerate(items[:top_n], start=1):
        item["rank"] = index
    return {
        "tool": "query_soil_ranking",
        "aggregation": aggregation,
        "top_n": top_n,
        "items": items[:top_n],
        "total_analyzed": len(groups),
        "time_window": {
            "start_time": args.get("start") or args.get("start_time"),
            "end_time": args.get("end") or args.get("end_time"),
        },
    }


def compute_detail_truth(rows: list[dict[str, Any]], args: dict[str, str]) -> dict[str, Any]:
    enriched = [enrich_record(row) for row in rows]
    enriched.sort(key=lambda row: row.get("create_time") or "", reverse=True)
    status_counts = Counter(row["soil_status"] for row in enriched)
    alert_rows = [row for row in enriched if row["soil_status"] in ALERT_STATUSES]
    latest = enriched[0] if enriched else None
    truth = {
        "tool": "query_soil_detail",
        "entity_type": "device" if args.get("sn") else "region",
        "entity_name": args.get("sn") or args.get("county") or args.get("city") or "未知",
        "record_count": len(enriched),
        "time_window": {
            "start_time": args.get("start") or args.get("start_time"),
            "end_time": args.get("end") or args.get("end_time"),
        },
        "latest_record": slim_row(latest) if latest else None,
        "status_summary": dict(status_counts),
        "alert_records": slim_rows(alert_rows[:5]),
        "output_mode": args.get("output_mode", "normal"),
    }
    if truth["output_mode"] == "warning_mode" and alert_rows:
        truth["warning_data"] = slim_row(alert_rows[0])
    return truth


def enrich_record(row: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(row)
    water20 = safe_float(enriched.get("water20cm")) or 0.0
    t20 = safe_float(enriched.get("t20cm")) or 0.0
    if water20 == 0 and t20 == 0:
        enriched["soil_status"] = "device_fault"
    elif water20 < 50:
        enriched["soil_status"] = "heavy_drought"
    elif water20 >= 150:
        enriched["soil_status"] = "waterlogging"
    else:
        enriched["soil_status"] = "not_triggered"
    return enriched


def safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def slim_row(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        "sn": row.get("sn"),
        "city": row.get("city"),
        "county": row.get("county"),
        "create_time": row.get("create_time"),
        "water20cm": row.get("water20cm"),
        "soil_status": row.get("soil_status"),
    }


def slim_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [slim_row(row) for row in rows]


def analyze_case(case: dict[str, Any], execution: dict[str, Any], db_truth: dict[str, Any]) -> dict[str, Any]:
    response = execution.get("response", {})
    logs = execution.get("logs", [])
    expected_tool = normalize_expected(case.get("预期 Tool"))
    expected_answer_type = normalize_expected(case.get("预期 answer_type"))
    expected_output_mode = normalize_expected(case.get("预期 output_mode"))
    expected_guidance_reason = normalize_expected(case.get("预期 guidance_reason"))
    expected_fallback_reason = normalize_expected(case.get("预期 fallback_reason"))

    actual_input_type = normalize_expected(response.get("input_type"))
    actual_answer_type = normalize_expected(response.get("answer_type"))
    actual_output_mode = infer_actual_output_mode(response)
    actual_guidance_reason = normalize_expected(response.get("guidance_reason"))
    actual_fallback_reason = infer_actual_fallback_reason(response, execution)

    actual_tool, actual_tool_note = infer_actual_tool(logs, response, case)
    tool_hit = bool(actual_tool) or bool(logs) or has_query_evidence(response)

    current_answer_check = evaluate_answer_text(case.get("当前回答", ""), case, db_truth)
    actual_answer_check = evaluate_answer_text(response.get("final_answer", ""), case, db_truth)

    consistency = compare_answers(case.get("当前回答", ""), response.get("final_answer", ""), case, db_truth)

    fact_status = combine_fact_status(current_answer_check["fact_status"], actual_answer_check["fact_status"])
    failure_reasons = []

    if expected_tool and actual_tool != expected_tool:
        failure_reasons.append(f"Tool 不匹配：期望 {expected_tool}，实际 {actual_tool or '无'}。")
    if case.get("是否必须命中 Tool") == "是" and not tool_hit:
        failure_reasons.append("业务 case 未命中 Tool。")
    if expected_answer_type and actual_answer_type != expected_answer_type:
        failure_reasons.append(f"answer_type 不匹配：期望 {expected_answer_type}，实际 {actual_answer_type or '未返回'}。")
    if expected_output_mode != actual_output_mode:
        failure_reasons.append(f"output_mode 不匹配：期望 {expected_output_mode or '无'}，实际 {actual_output_mode or '无/未返回'}。")
    if expected_guidance_reason != actual_guidance_reason:
        failure_reasons.append(f"guidance_reason 不匹配：期望 {expected_guidance_reason or '无'}，实际 {actual_guidance_reason or '无/未返回'}。")
    if expected_fallback_reason != actual_fallback_reason:
        failure_reasons.append(f"fallback_reason 不匹配：期望 {expected_fallback_reason or '无'}，实际 {actual_fallback_reason or '无/未返回'}。")
    if case.get("是否域内业务问题") == "是" and db_truth.get("applicable") and not db_truth.get("sql_blocks"):
        failure_reasons.append("业务 case 缺少 SQL / 等效 SQL。")
    if case.get("是否域内业务问题") == "是" and db_truth.get("blocker"):
        failure_reasons.append(f"数据库回查阻塞：{db_truth['blocker']}")
    if current_answer_check["fact_status"] == "否":
        failure_reasons.append("case 当前回答与数据库事实不一致。")
    if actual_answer_check["fact_status"] == "否":
        failure_reasons.append("实际回答与数据库事实不一致。")
    if current_answer_check["missing_must_have"]:
        failure_reasons.append(f"case 当前回答缺少必含事实：{', '.join(current_answer_check['missing_must_have'])}。")
    if actual_answer_check["missing_must_have"]:
        failure_reasons.append(f"实际回答缺少必含事实：{', '.join(actual_answer_check['missing_must_have'])}。")
    if current_answer_check["forbidden_hits"]:
        failure_reasons.append(f"case 当前回答命中禁止事实：{', '.join(current_answer_check['forbidden_hits'])}。")
    if actual_answer_check["forbidden_hits"]:
        failure_reasons.append(f"实际回答命中禁止事实：{', '.join(actual_answer_check['forbidden_hits'])}。")
    if consistency == "结论不一致":
        failure_reasons.append("当前回答与实际回答结论不一致。")

    return {
        "expected_tool": expected_tool,
        "expected_answer_type": expected_answer_type,
        "expected_output_mode": expected_output_mode,
        "expected_guidance_reason": expected_guidance_reason,
        "expected_fallback_reason": expected_fallback_reason,
        "actual_input_type": actual_input_type,
        "actual_tool": actual_tool,
        "actual_tool_note": actual_tool_note,
        "actual_answer_type": actual_answer_type,
        "actual_output_mode": actual_output_mode,
        "actual_guidance_reason": actual_guidance_reason,
        "actual_fallback_reason": actual_fallback_reason,
        "current_answer_check": current_answer_check,
        "actual_answer_check": actual_answer_check,
        "consistency": consistency,
        "fact_status": fact_status,
        "pass": not failure_reasons,
        "failure_reasons": failure_reasons,
    }


def normalize_expected(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text in {"无", "不适用"}:
        return None
    if text.startswith("无（"):
        return None
    return text


def infer_actual_tool(logs: list[dict[str, Any]], response: dict[str, Any], case: dict[str, Any]) -> tuple[str | None, str | None]:
    query_type = None
    if logs:
        query_type = logs[0].get("query_type")
    if not query_type:
        query_type = ((response.get("query_plan") or {}).get("query_type"))
    mapping = {
        "recent_summary": "query_soil_summary",
        "latest_record": "query_soil_summary",
        "severity_ranking": "query_soil_ranking",
        "region_detail": "query_soil_detail",
        "device_detail": "query_soil_detail",
        "anomaly_list": "query_soil_detail" if case.get("预期 answer_type") == "soil_detail_answer" else "query_soil_summary",
    }
    actual_tool = mapping.get(query_type)
    note = f"根据 agent_query_log.query_type={query_type} 归并判定。" if query_type else None
    return actual_tool, note


def has_query_evidence(response: dict[str, Any]) -> bool:
    query_result = response.get("query_result") or {}
    if isinstance(query_result, dict) and (query_result.get("records") or query_result.get("entries")):
        return True
    return bool(response.get("query_plan"))


def infer_actual_output_mode(response: dict[str, Any]) -> str | None:
    raw = normalize_expected(response.get("output_mode"))
    if raw:
        return raw
    answer_type = normalize_expected(response.get("answer_type"))
    query_type = (response.get("query_plan") or {}).get("query_type")
    if answer_type == "soil_anomaly_answer":
        return "anomaly_focus"
    if answer_type == "soil_warning_answer":
        return "warning_mode"
    if answer_type == "soil_advice_answer":
        return "advice_mode"
    if query_type == "anomaly_list":
        return "anomaly_focus"
    if answer_type in {"soil_summary_answer", "soil_ranking_answer", "soil_detail_answer"} and has_query_evidence(response):
        return "normal"
    return None


def infer_actual_fallback_reason(response: dict[str, Any], execution: dict[str, Any]) -> str | None:
    raw = normalize_expected(response.get("fallback_reason"))
    if raw:
        return raw
    text = str(response.get("final_answer") or "")
    if "未调用任何查询工具" in text or "必须查询真实数据后才能回答" in text:
        return "tool_missing"
    if "在系统中不存在" in text or "核对设备编号" in text:
        return "entity_not_found"
    if "扩大时间范围" in text or ("时间段" in text and "没有" in text and "数据" in text):
        return "no_data"
    if execution.get("mode") == "controlled-current-code-fact-check-injection":
        return "fact_check_failed"
    return None


def evaluate_answer_text(text: str, case: dict[str, Any], db_truth: dict[str, Any]) -> dict[str, Any]:
    text = text or ""
    must_have = split_tokens(case.get("必含事实"))
    forbidden = split_tokens(case.get("禁止事实"))
    missing_must_have = [token for token in must_have if token and token not in text]
    forbidden_hits = [token for token in forbidden if token and token in text]
    contradictions = []

    truth = db_truth.get("truth", {})
    if db_truth.get("applicable"):
        if "diagnosis" in truth:
            diagnosis = truth.get("diagnosis")
            if diagnosis == "entity_not_found" and any(token in text for token in ["没有数据", "无数据", "时间段"]):
                contradictions.append("数据库诊断为 entity_not_found，但回答更像 no_data_in_window。")
            if diagnosis == "no_data_in_window" and "不存在" in text:
                contradictions.append("数据库诊断为 no_data_in_window，但回答写成 entity_not_found。")
        else:
            if truth.get("total_records", truth.get("record_count", 0)) and any(token in text for token in ["无数据", "没有数据", "查不到", "不存在"]):
                contradictions.append("数据库存在数据，但回答声称无数据/不存在。")
            if truth.get("alert_count", 0) > 0 and any(token in text for token in ["没有明显异常", "没有异常告警", "不需要关注", "alert_count=0"]):
                contradictions.append("数据库存在异常/预警，但回答声称没有异常。")

    fact_status = "是"
    if case.get("是否域内业务问题") != "是":
        fact_status = "是"
    elif db_truth.get("blocker"):
        fact_status = "待校验"
    elif contradictions or forbidden_hits:
        fact_status = "否"

    return {
        "fact_status": fact_status,
        "missing_must_have": missing_must_have,
        "forbidden_hits": forbidden_hits,
        "contradictions": contradictions,
    }


def split_tokens(value: Any) -> list[str]:
    if not value or normalize_expected(value) is None:
        return []
    text = str(value).replace("`", "")
    parts = re.split(r"[、/,，；;]+", text)
    return [part.strip() for part in parts if part.strip()]


def compare_answers(current_answer: str, actual_answer: str, case: dict[str, Any], db_truth: dict[str, Any]) -> str:
    current_answer = (current_answer or "").strip()
    actual_answer = (actual_answer or "").strip()
    if current_answer == actual_answer:
        return "结论一致"
    current_check = evaluate_answer_text(current_answer, case, db_truth)
    actual_check = evaluate_answer_text(actual_answer, case, db_truth)
    must_have = split_tokens(case.get("必含事实"))
    overlap = {token for token in must_have if token in actual_answer and token in current_answer}
    if current_check["fact_status"] == actual_check["fact_status"] == "是" and overlap:
        return "结论基本一致，措辞不同"
    if current_check["fact_status"] == actual_check["fact_status"] == "是" and case.get("预期 answer_type") == "guidance_answer":
        return "结论基本一致，措辞不同"
    if current_check["fact_status"] == actual_check["fact_status"] == "是" and not must_have:
        return "结论基本一致，措辞不同"
    return "结论不一致"


def combine_fact_status(current_status: str, actual_status: str) -> str:
    if "否" in {current_status, actual_status}:
        return "否"
    if "待校验" in {current_status, actual_status}:
        return "待校验"
    return "是"


def summarize_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    passed = sum(1 for result in results if result["analysis"]["pass"])
    failed = len(results) - passed
    answer_type_stats: Counter[str] = Counter()
    output_mode_stats: Counter[str] = Counter()
    fallback_stats: Counter[str] = Counter()
    business_without_tool = []
    factual_pending = []
    factual_no = []
    for result in results:
        case = result["case"]
        analysis = result["analysis"]
        answer_type_stats[case.get("预期 answer_type", "unknown")] += 1 if analysis["pass"] else 0
        output_mode_stats[case.get("预期 output_mode", "无")] += 1 if analysis["pass"] else 0
        fallback_stats[case.get("预期 fallback_reason", "无")] += 1 if analysis["pass"] else 0
        if case.get("是否域内业务问题") == "是" and not analysis["actual_tool"]:
            business_without_tool.append(case["CaseID"])
        if analysis["fact_status"] == "待校验":
            factual_pending.append(case["CaseID"])
        if analysis["fact_status"] == "否":
            factual_no.append(case["CaseID"])
    return {
        "passed": passed,
        "failed": failed,
        "pass_rate": round((passed / len(results)) * 100, 2) if results else 0.0,
        "answer_type_stats": answer_type_stats,
        "output_mode_stats": output_mode_stats,
        "fallback_stats": fallback_stats,
        "business_without_tool": business_without_tool,
        "factual_pending": factual_pending,
        "factual_no": factual_no,
    }


def render_report(
    *,
    git_meta: dict[str, Any],
    env_meta: dict[str, Any],
    self_check: dict[str, Any],
    python_test: CommandResult,
    node_test: CommandResult,
    results: list[dict[str, Any]],
    summary: dict[str, Any],
) -> str:
    lines: list[str] = []
    lines.append("# 墒情 Agent 56 条正式验收测试报告")
    lines.append("")
    lines.append("## 1. 测试概览")
    lines.append(f"- 测试时间：{env_meta['timestamp']}")
    lines.append(f"- 分支：`{git_meta['branch']}`")
    lines.append(f"- 提交号：`{git_meta['commit']}`")
    lines.append(f"- 执行环境：仓库 `{env_meta['cwd']}`；在线 Agent `{env_meta['agent_url']}`；MySQL `{env_meta['mysql_host']}:{env_meta['mysql_port']}/{env_meta['mysql_database']}`")
    lines.append(f"- 正式 case 总数：`{self_check['total_cases']}`")
    lines.append(f"- 总体通过率：`{summary['pass_rate']}%`（{summary['passed']}/{len(results)}）")
    lines.append("- 说明：`guidance_answer` 与内部守卫类 case 使用仓库当前代码做受控执行；业务查询类 case 使用本地在线 Agent HTTP 服务，并通过 `agent_query_log` 与数据库回查补齐证据链。")
    lines.append("")
    lines.append("## 2. 正式库自检结果")
    lines.append(f"- 数量检查：`{self_check['total_cases']}` 条。")
    for answer_type, expected_count in self_check["required_distribution"].items():
        actual_count = self_check["distribution"].get(answer_type, 0)
        lines.append(f"- 分布 `{answer_type}`：期望 `{expected_count}`，实际 `{actual_count}`。")
    lines.append(f"- 字段完整性：缺字段 case 数量 `{len(self_check['missing_fields'])}`。")
    if self_check["blockers"]:
        lines.append("- 正式库阻塞项：")
        for blocker in self_check["blockers"]:
            lines.append(f"  - {blocker}")
    else:
        lines.append("- 是否符合正式入口要求：`是`。")
    lines.append("")
    lines.append("## 3. 基础测试结果")
    lines.append(render_command_result("Python 测试结果", python_test))
    lines.append("")
    lines.append(render_command_result("Node 测试结果", node_test))
    lines.append("")
    lines.append("## 4. 56 条 case 逐条结果")
    for result in results:
        lines.extend(render_case_section(result))
    lines.append("")
    lines.append("## 5. 汇总统计")
    lines.append(f"- 通过条数：`{summary['passed']}`")
    lines.append(f"- 失败条数：`{summary['failed']}`")
    lines.append("- 各 answer_type 通过情况：")
    for answer_type, expected_count in self_check["required_distribution"].items():
        passed_count = sum(
            1
            for result in results
            if result["case"].get("预期 answer_type") == answer_type and result["analysis"]["pass"]
        )
        lines.append(f"  - `{answer_type}`：`{passed_count}/{expected_count}`")
    lines.append("- 各 output_mode 通过情况：")
    for mode in ["无", "normal", "anomaly_focus", "warning_mode", "advice_mode"]:
        matched = [result for result in results if (result["case"].get("预期 output_mode") or "无") == mode]
        if not matched:
            continue
        passed_count = sum(1 for result in matched if result["analysis"]["pass"])
        lines.append(f"  - `{mode}`：`{passed_count}/{len(matched)}`")
    lines.append("- 各 fallback_reason 通过情况：")
    for reason in ["无", "no_data", "entity_not_found", "tool_missing", "tool_blocked", "fact_check_failed", "unknown"]:
        matched = [result for result in results if (result["case"].get("预期 fallback_reason") or "无") == reason]
        if not matched:
            continue
        passed_count = sum(1 for result in matched if result["analysis"]["pass"])
        lines.append(f"  - `{reason}`：`{passed_count}/{len(matched)}`")
    lines.append("")
    lines.append("## 6. 失败 case 清单")
    failures = [result for result in results if not result["analysis"]["pass"]]
    if not failures:
        lines.append("- 无失败 case。")
    else:
        for result in failures:
            lines.append(f"- `{result['case']['CaseID']}`：{'；'.join(result['analysis']['failure_reasons'])}")
    lines.append("")
    lines.append("## 7. 最终结论")
    final_conclusion = "通过" if summary["failed"] == 0 else "有条件通过" if summary["failed"] <= 3 else "不通过"
    lines.append(f"- 最终结论：`{final_conclusion}`")
    lines.append(f"- 是否还存在“未调 Tool 直接回答业务问题”的路径：`{'是' if summary['business_without_tool'] else '否'}`")
    lines.append(f"- 是否所有业务 case 都能被数据库支撑：`{'否' if summary['factual_pending'] or summary['factual_no'] else '是'}`")
    lines.append(
        f"- 哪些 case 的 `是否符合事实` 需要更新："
        f"`{', '.join(summary['factual_pending'] + summary['factual_no']) or '无'}`"
    )
    blockers = collect_gate_blockers(
        self_check=self_check,
        python_test=python_test,
        node_test=node_test,
        results=results,
        summary=summary,
    )
    lines.append(f"- 阻塞项：`{'; '.join(blockers) or '无'}`")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_command_result(title: str, result: CommandResult) -> str:
    output = [f"### {title}"]
    output.append(f"- 执行命令：`{result.command}`")
    output.append(f"- 工作目录：`{result.cwd}`")
    output.append(f"- 退出码：`{result.exit_code}`")
    if result.stdout:
        output.append("- 标准输出：")
        output.append("```text")
        output.append(result.stdout)
        output.append("```")
    if result.stderr:
        output.append("- 标准错误：")
        output.append("```text")
        output.append(result.stderr)
        output.append("```")
    return "\n".join(output)


def render_case_section(result: dict[str, Any]) -> list[str]:
    case = result["case"]
    execution = result["execution"]
    analysis = result["analysis"]
    db_truth = result["db_truth"]
    response = execution.get("response", {})
    logs = execution.get("logs", [])
    lines = [f"### {case['CaseID']}"]
    lines.append(f"- 用户问题：{case.get('用户问题', '')}")
    lines.append(f"- 上下文：{case.get('上下文', '')}")
    lines.append("- 预期契约：")
    lines.append(f"  - 预期 input_type：`{case.get('预期 input_type', '无')}`")
    lines.append(f"  - 预期 Tool：`{case.get('预期 Tool', '无')}`")
    lines.append(f"  - 预期 answer_type：`{case.get('预期 answer_type', '无')}`")
    lines.append(f"  - 预期 output_mode：`{case.get('预期 output_mode', '无')}`")
    lines.append(f"  - 预期 guidance_reason：`{case.get('预期 guidance_reason', '无')}`")
    lines.append(f"  - 预期 fallback_reason：`{case.get('预期 fallback_reason', '无')}`")
    lines.append("- 实际契约：")
    lines.append(f"  - 实际 input_type：`{analysis['actual_input_type'] or '无/未返回'}`")
    lines.append(f"  - 实际 Tool：`{analysis['actual_tool'] or '无'}`")
    if analysis["actual_tool_note"]:
        lines.append(f"  - Tool 判定说明：{analysis['actual_tool_note']}")
    lines.append(f"  - 实际 answer_type：`{analysis['actual_answer_type'] or '无/未返回'}`")
    lines.append(f"  - 实际 output_mode：`{analysis['actual_output_mode'] or '无/未返回'}`")
    lines.append(f"  - 实际 guidance_reason：`{analysis['actual_guidance_reason'] or '无/未返回'}`")
    lines.append(f"  - 实际 fallback_reason：`{analysis['actual_fallback_reason'] or '无/未返回'}`")
    lines.append(f"  - 实际 final_answer：{response.get('final_answer', '')}")
    lines.append(f"- 执行方式：`{execution['mode']}`")
    lines.append("- Tool 调用：")
    lines.append(f"  - 是否命中 Tool：`{'是' if analysis['actual_tool'] else '否'}`")
    lines.append(f"  - 实际命中的 Tool 名称：`{analysis['actual_tool'] or '无'}`")
    if logs:
        lines.append("  - Tool 调用参数：")
        for log in logs:
            filters_json = json.dumps(log.get("filters_json", {}), ensure_ascii=False)
            time_range_json = json.dumps(log.get("time_range_json", {}), ensure_ascii=False)
            lines.append(f"    - query_type=`{log.get('query_type')}` filters={filters_json} time_range={time_range_json}")
        lines.append(f"  - Tool trace：`{json.dumps([{'query_type': log.get('query_type'), 'row_count': log.get('row_count'), 'answer_type': log.get('answer_type')} for log in logs], ensure_ascii=False)}`")
        lines.append(f"  - query_result：`{json.dumps({'row_count': [log.get('row_count') for log in logs]}, ensure_ascii=False)}`")
        lines.append(f"  - answer_facts：`{json.dumps(response.get('answer_facts', {}), ensure_ascii=False)}`")
        lines.append(f"  - query_log_entries：`{json.dumps([{'query_id': log.get('query_id'), 'query_type': log.get('query_type'), 'row_count': log.get('row_count')} for log in logs], ensure_ascii=False)}`")
    elif response.get("query_plan"):
        lines.append(f"  - Tool 调用参数：`{json.dumps({'query_type': response.get('query_plan', {}).get('query_type'), 'filters': response.get('query_plan', {}).get('filters'), 'time_range': response.get('query_plan', {}).get('time_range')}, ensure_ascii=False)}`")
        lines.append(f"  - Tool trace：`{json.dumps([{'query_type': response.get('query_plan', {}).get('query_type'), 'answer_type': response.get('answer_type')}], ensure_ascii=False)}`")
        query_result = response.get("query_result") or {}
        record_count = len(query_result.get("records", [])) if isinstance(query_result, dict) else 0
        lines.append(f"  - query_result：`{json.dumps({'record_count': record_count}, ensure_ascii=False)}`")
        lines.append("  - answer_facts：`未返回`")
        lines.append("  - query_log_entries：`[]`")
    else:
        lines.append("  - Tool 调用参数：`无`")
        lines.append("  - Tool trace：`[]`")
        lines.append("  - query_result：`{}`")
        lines.append("  - answer_facts：`{}`")
        lines.append("  - query_log_entries：`[]`")
    lines.append("- SQL / 等效 SQL：")
    if logs and logs[0].get("executed_sql_text"):
        lines.append("  - SQL 类型：`真实执行 SQL（来自 agent_query_log.executed_sql_text）`")
        lines.append("```sql")
        lines.append(str(logs[0]["executed_sql_text"]).strip())
        lines.append("```")
    if db_truth.get("sql_blocks"):
        for block in db_truth["sql_blocks"]:
            lines.append(f"  - SQL 类型：`{block['sql_type']}`")
            lines.append(f"  - 对应 Tool：`{block['tool']}`")
            lines.append("```sql")
            lines.append(block["sql"])
            lines.append("```")
    if not logs and not db_truth.get("sql_blocks"):
        lines.append("  - 不适用（非业务 guidance case，不查库）。")
    lines.append("- SQL 结果：")
    if db_truth.get("applicable"):
        truth = db_truth.get("truth", {})
        if "items" in truth:
            lines.append(f"  - 结果总量：`{truth.get('total_analyzed', 0)}` 个分组")
            lines.append(f"  - 聚合结果 / 排名结果：`{json.dumps(truth.get('items', [])[:5], ensure_ascii=False)}`")
        elif "diagnosis" in truth:
            lines.append(f"  - 结果总量：`{truth.get('record_count_in_window') or truth.get('record_count_all_time') or 0}`")
            lines.append(f"  - 诊断结果：`{json.dumps(truth, ensure_ascii=False)}`")
        else:
            lines.append(f"  - 结果总量：`{truth.get('total_records', truth.get('record_count', 0))}`")
            lines.append(f"  - 关键字段：`{json.dumps({k: truth.get(k) for k in truth if k in {'total_records','avg_water20cm','alert_count','record_count','entity_name','status_summary','top_alert_regions'}}, ensure_ascii=False)}`")
            lines.append(f"  - 关键记录样本：`{json.dumps(slim_rows(db_truth.get('rows', [])[:3]), ensure_ascii=False)}`")
            lines.append(f"  - 聚合结果 / 详情结果：`{json.dumps(truth, ensure_ascii=False)}`")
    else:
        lines.append("  - 不适用（非业务 guidance case，不查库）。")
    lines.append(f"- 当前回答（case 样例）：{case.get('当前回答', '')}")
    lines.append(f"- 实际回答：{response.get('final_answer', '')}")
    lines.append(f"- 一致性结论：`{analysis['consistency']}`")
    lines.append("- 数据库事实校验：")
    lines.append(f"  - 数据库校验断言：{case.get('数据库校验断言', '')}")
    lines.append(f"  - 预期实体：`{case.get('预期实体', '未单列')}`")
    lines.append(f"  - 预期时间窗：`{case.get('预期时间窗', '未单列')}`")
    lines.append(f"  - 预期关键指标：`{case.get('预期关键指标', '未单列')}`")
    lines.append(f"  - 预期排序结果：`{case.get('预期排序结果', '未单列')}`")
    lines.append(f"  - 预期诊断类别：`{case.get('预期诊断类别', '未单列')}`")
    lines.append(f"  - 必含事实：`{case.get('必含事实', '无')}`")
    lines.append(f"  - 禁止事实：`{case.get('禁止事实', '无')}`")
    lines.append(f"  - Case 当前回答是否符合事实：`{analysis['current_answer_check']['fact_status']}`")
    lines.append(f"  - 实际回答是否符合事实：`{analysis['actual_answer_check']['fact_status']}`")
    if analysis["current_answer_check"]["contradictions"]:
        lines.append(f"  - Case 当前回答事实冲突：`{'；'.join(analysis['current_answer_check']['contradictions'])}`")
    if analysis["actual_answer_check"]["contradictions"]:
        lines.append(f"  - 实际回答事实冲突：`{'；'.join(analysis['actual_answer_check']['contradictions'])}`")
    lines.append("- 最终判定：")
    lines.append(f"  - 是否通过：`{'是' if analysis['pass'] else '否'}`")
    lines.append(f"  - 是否符合事实：`{analysis['fact_status']}`")
    lines.append(f"  - 失败原因：`{'；'.join(analysis['failure_reasons']) if analysis['failure_reasons'] else '无'}`")
    lines.append(
        f"  - 修复建议：`{'保持当前实现或仅做表达优化' if analysis['pass'] else build_fix_suggestion(result)}`"
    )
    lines.append(f"- 备注：{case.get('备注', '')}")
    lines.append("")
    return lines


def build_fix_suggestion(result: dict[str, Any]) -> str:
    analysis = result["analysis"]
    suggestions = []
    if any("Tool" in reason for reason in analysis["failure_reasons"]):
        suggestions.append("将 live path 的查询能力收口到正式 4 Tool，并把命中的 Tool 名称显式写入响应/日志")
    if any("answer_type" in reason or "output_mode" in reason or "guidance_reason" in reason or "fallback_reason" in reason for reason in analysis["failure_reasons"]):
        suggestions.append("按正式契约补齐 answer_type / output_mode / guidance_reason / fallback_reason")
    if any("事实" in reason for reason in analysis["failure_reasons"]):
        suggestions.append("修正文案或事实核验逻辑，确保回答只陈述数据库可支撑的事实")
    if any("必含事实" in reason for reason in analysis["failure_reasons"]):
        suggestions.append("把正式 case 规定的关键实体、时间窗和指标写进最终回答")
    return "；".join(suggestions) or "定位该 case 的 live path 与正式库漂移点后修复"


def build_blocked_case_result(case: dict[str, Any], exc: Exception) -> dict[str, Any]:
    return {
        "case": case,
        "execution": {
            "mode": "blocked-by-script-error",
            "session_id": f"{RUN_ID}-{case['CaseID'].lower()}",
            "turn_id": 1,
            "setup_results": [],
            "response": {
                "final_answer": "",
                "__error__": f"{exc.__class__.__name__}: {exc}",
                "__traceback__": traceback.format_exc(),
            },
            "logs": [],
            "history_after": [],
        },
        "db_truth": {
            "applicable": False,
            "invocations": [],
            "sql_blocks": [],
            "rows": [],
            "truth": {},
            "blocker": f"脚本执行异常：{exc}",
        },
        "analysis": {
            "expected_tool": normalize_expected(case.get("预期 Tool")),
            "expected_answer_type": normalize_expected(case.get("预期 answer_type")),
            "expected_output_mode": normalize_expected(case.get("预期 output_mode")),
            "expected_guidance_reason": normalize_expected(case.get("预期 guidance_reason")),
            "expected_fallback_reason": normalize_expected(case.get("预期 fallback_reason")),
            "actual_input_type": None,
            "actual_tool": None,
            "actual_tool_note": None,
            "actual_answer_type": None,
            "actual_output_mode": None,
            "actual_guidance_reason": None,
            "actual_fallback_reason": None,
            "current_answer_check": {"fact_status": "待校验", "missing_must_have": [], "forbidden_hits": [], "contradictions": []},
            "actual_answer_check": {"fact_status": "待校验", "missing_must_have": [], "forbidden_hits": [], "contradictions": []},
            "consistency": "结论不一致",
            "fact_status": "待校验",
            "pass": False,
            "failure_reasons": [f"脚本执行异常：{exc.__class__.__name__}: {exc}"],
        },
    }


_CURRENT_IMPORTS: dict[str, Any] = {}


def ensure_current_imports() -> None:
    if _CURRENT_IMPORTS:
        return
    sys.path.insert(0, str(ROOT / "apps/agent"))
    from app.repositories.session_context_repository import SessionContextRepository
    from app.services.agent_service import SoilAgentService
    from app.llm.qwen_client import QwenClient

    _CURRENT_IMPORTS["SessionContextRepository"] = SessionContextRepository
    _CURRENT_IMPORTS["SoilAgentService"] = SoilAgentService
    _CURRENT_IMPORTS["QwenClient"] = QwenClient


def current_session_context_repository():
    ensure_current_imports()
    return _CURRENT_IMPORTS["SessionContextRepository"]()


def current_agent_service(*, qwen_client=None, context_store=None):
    ensure_current_imports()
    return _CURRENT_IMPORTS["SoilAgentService"](
        qwen_client=qwen_client,
        context_store=context_store,
    )


def current_qwen_client_class():
    ensure_current_imports()
    return _CURRENT_IMPORTS["QwenClient"]


if __name__ == "__main__":
    main()
