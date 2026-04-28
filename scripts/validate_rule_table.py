"""Compare hardcoded rule thresholds with metric_rule table values.

Usage (from repo root):
    python scripts/validate_rule_table.py

Exit 0  — all thresholds match.
Exit 1  — mismatch detected (diff printed to stdout).
Exit 2  — cannot connect to DB or USE_RULE_TABLE is false (skip, not a failure).
"""
from __future__ import annotations

import json
import os
import sys


# ── hardcoded fallback thresholds (mirror of rule_repository._FALLBACK_PROFILE) ──

_HARDCODED = {
    "heavy_drought_max": 20.0,
    "waterlogging_min": 80.0,
}


def _connect():
    try:
        import pymysql
    except ImportError:
        print("pymysql not installed — skipping validation.", file=sys.stderr)
        sys.exit(2)

    host = os.environ.get("DB_HOST", "127.0.0.1")
    port = int(os.environ.get("DB_PORT", "3306"))
    user = os.environ.get("DB_USER", "root")
    password = os.environ.get("DB_PASSWORD", "")
    database = os.environ.get("DB_NAME", "smart_agriculture")

    try:
        return pymysql.connect(
            host=host, port=port, user=user, password=password,
            database=database, charset="utf8mb4",
            connect_timeout=5,
        )
    except Exception as exc:
        print(f"DB connection failed: {exc}", file=sys.stderr)
        sys.exit(2)


def _load_db_thresholds(conn) -> dict[str, float]:
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT rule_definition_json FROM metric_rule "
            "WHERE rule_code = 'soil_warning_v1' AND enabled = 1 "
            "ORDER BY updated_at DESC LIMIT 1"
        )
        row = cursor.fetchone()
    if not row:
        print("No active soil_warning_v1 rule found in metric_rule table.", file=sys.stderr)
        sys.exit(2)

    try:
        definition = json.loads(row[0])
    except (json.JSONDecodeError, TypeError) as exc:
        print(f"Failed to parse rule_definition_json: {exc}", file=sys.stderr)
        sys.exit(2)

    result: dict[str, float] = {}
    for rule in definition.get("rules", []):
        conditions = rule.get("conditions", {})
        rtype = rule.get("rule_type", "")
        if rtype == "heavy_drought":
            if "water20cm_lt" in conditions:
                result["heavy_drought_max"] = float(conditions["water20cm_lt"])
        elif rtype == "waterlogging":
            if "water20cm_gt" in conditions:
                result["waterlogging_min"] = float(conditions["water20cm_gt"])
    return result


def main() -> None:
    use_rule_table = os.environ.get("USE_RULE_TABLE", "false").lower()
    if use_rule_table != "true":
        print("USE_RULE_TABLE is not 'true' — skipping rule table validation.")
        sys.exit(2)

    conn = _connect()
    try:
        db_thresholds = _load_db_thresholds(conn)
    finally:
        conn.close()

    mismatches: list[str] = []
    all_keys = set(_HARDCODED) | set(db_thresholds)
    for key in sorted(all_keys):
        hardcoded = _HARDCODED.get(key)
        db_val = db_thresholds.get(key)
        if hardcoded is None:
            mismatches.append(f"  {key}: DB={db_val}  hardcoded=MISSING")
        elif db_val is None:
            mismatches.append(f"  {key}: DB=MISSING  hardcoded={hardcoded}")
        elif abs(hardcoded - db_val) > 1e-9:
            mismatches.append(f"  {key}: DB={db_val}  hardcoded={hardcoded}  ← MISMATCH")
        else:
            print(f"  {key}: OK ({db_val})")

    if mismatches:
        print("\nThreshold mismatches detected:")
        for line in mismatches:
            print(line)
        sys.exit(1)
    else:
        print("\nAll thresholds match. Safe to enable USE_RULE_TABLE=true.")


if __name__ == "__main__":
    main()
