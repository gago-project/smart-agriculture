"""
导入 sys_region.xls 到 sys_region 表。

用法：
    PYTHONPATH=apps/agent python scripts/import/import_sys_region.py \
        --file /path/to/sys_region.xls

依赖：pip install xlrd==1.2.0
"""

from __future__ import annotations

import argparse
import os

import pymysql
import pymysql.cursors
import xlrd


DB_CONFIG = {
    "host": os.environ.get("MYSQL_HOST", "127.0.0.1"),
    "port": int(os.environ.get("MYSQL_PORT", 3306)),
    "user": os.environ.get("MYSQL_USER", "smart_agriculture"),
    "password": os.environ.get("MYSQL_PASSWORD", ""),
    "database": os.environ.get("MYSQL_DATABASE", "smart_agriculture"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}

FIELD_MAP = {
    "id": ["id"],
    "region_code": ["region_code", "code"],
    "region_name": ["region_name", "name"],
    "parent_code": ["parent_code", "parent"],
    "region_level": ["level", "region_level"],
    "lon": ["lon", "longitude"],
    "lat": ["lat", "latitude"],
    "created_at": ["create_time", "created_at"],
    "updated_at": ["update_time", "updated_at"],
}


def infer_level(code: str) -> int:
    """按编码长度推断行政层级。"""
    length = len(str(code).strip())
    if length <= 2:
        return 1
    if length <= 6:
        return 2
    return 4


def resolve_column(row: dict, key: str):
    """从多组候选表头中取值。"""
    for alias in FIELD_MAP.get(key, [key]):
        if alias in row:
            value = row[alias]
            return None if value == "" else value
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    args = parser.parse_args()

    workbook = xlrd.open_workbook(args.file)
    worksheet = workbook.sheet_by_index(0)
    headers = [str(worksheet.cell_value(0, index)).strip() for index in range(worksheet.ncols)]
    print(f"Headers: {headers}")
    print(f"Total rows: {worksheet.nrows - 1}")

    connection = pymysql.connect(**DB_CONFIG)
    inserted = 0
    skipped = 0
    try:
        with connection.cursor() as cursor:
            for row_index in range(1, worksheet.nrows):
                row_values = [worksheet.cell_value(row_index, index) for index in range(worksheet.ncols)]
                row = dict(zip(headers, row_values))

                region_id = resolve_column(row, "id")
                region_code = str(resolve_column(row, "region_code") or "").strip()
                region_name = str(resolve_column(row, "region_name") or "").strip()
                parent_code = resolve_column(row, "parent_code")
                region_level_raw = resolve_column(row, "region_level")
                region_level = int(region_level_raw) if region_level_raw else infer_level(region_code)
                lon = resolve_column(row, "lon")
                lat = resolve_column(row, "lat")
                created_at = resolve_column(row, "created_at")
                updated_at = resolve_column(row, "updated_at")

                if not region_code or not region_name:
                    skipped += 1
                    continue

                cursor.execute(
                    """
                    INSERT INTO sys_region
                      (id, region_code, region_name, parent_code, region_level,
                       lon, lat, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                      region_name = VALUES(region_name),
                      parent_code = VALUES(parent_code),
                      region_level = VALUES(region_level),
                      updated_at = VALUES(updated_at)
                    """,
                    (
                        region_id,
                        region_code,
                        region_name,
                        parent_code,
                        region_level,
                        lon,
                        lat,
                        created_at,
                        updated_at,
                    ),
                )
                inserted += 1

        connection.commit()
        print(f"Done: inserted/updated={inserted}, skipped={skipped}")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
