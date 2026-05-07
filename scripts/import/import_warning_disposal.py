"""
导入 1111.xlsx 到 warning_disposal_record 表。
仅导入 warn_type = '墒情预警' 的行。
city / county 优先从 address 字段解析（「苏州市昆山市」→ city=苏州市，county=昆山市）；
若解析失败，从 sys_region 表通过 region_code 查询。

用法：
    PYTHONPATH=apps/agent python scripts/import/import_warning_disposal.py \
        --file /path/to/1111.xlsx
"""

from __future__ import annotations

import argparse
import os

import openpyxl
import pymysql
import pymysql.cursors


DB_CONFIG = {
    "host": os.environ.get("MYSQL_HOST", "127.0.0.1"),
    "port": int(os.environ.get("MYSQL_PORT", 3306)),
    "user": os.environ.get("MYSQL_USER", "smart_agriculture"),
    "password": os.environ.get("MYSQL_PASSWORD", ""),
    "database": os.environ.get("MYSQL_DATABASE", "smart_agriculture"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}

JIANGSU_CITIES = [
    "南京市",
    "无锡市",
    "常州市",
    "苏州市",
    "镇江市",
    "南通市",
    "扬州市",
    "泰州市",
    "徐州市",
    "连云港市",
    "淮安市",
    "盐城市",
    "宿迁市",
]


def parse_address(address: str) -> tuple[str | None, str | None]:
    """从「苏州市昆山市」格式解析 city / county。"""
    normalized = str(address or "").strip()
    city = next((item for item in JIANGSU_CITIES if item in normalized), None)
    county = normalized.replace(city, "").strip() if city else None
    return city, county or None


def lookup_city_county_from_region(cursor, region_code: str) -> tuple[str | None, str | None]:
    """
    通过 sys_region 层级查询 city 和 county。
    region_code 是乡镇级（9位），向上找父级：
      乡镇 → 区县（level=3）→ 市（level=2）
    """
    cursor.execute(
        "SELECT region_code, region_name, parent_code, region_level "
        "FROM sys_region WHERE region_code = %s",
        (region_code,),
    )
    row = cursor.fetchone()
    if not row:
        return None, None

    city_name = None
    county_name = None
    for _ in range(2):
        level = int(row.get("region_level") or 0)
        if level == 3:
            county_name = row["region_name"]
        elif level == 2:
            city_name = row["region_name"]
            break

        parent_code = row.get("parent_code")
        if not parent_code:
            break
        cursor.execute(
            "SELECT region_code, region_name, parent_code, region_level "
            "FROM sys_region WHERE region_code = %s",
            (parent_code,),
        )
        row = cursor.fetchone()
        if not row:
            break

    return city_name, county_name


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--truncate", action="store_true", help="清空表后重新导入（幂等用）")
    args = parser.parse_args()

    workbook = openpyxl.load_workbook(args.file, read_only=True, data_only=True)
    worksheet = workbook["Sheet1"]
    all_rows = list(worksheet.iter_rows(values_only=True))
    headers = all_rows[0]
    rows = [dict(zip(headers, row)) for row in all_rows[1:]]
    soil_rows = [row for row in rows if row.get("warn_type") == "墒情预警"]
    print(f"Total rows: {len(rows)}, 墒情预警: {len(soil_rows)}")
    workbook.close()

    connection = pymysql.connect(**DB_CONFIG)
    inserted = 0
    skipped = 0
    fallback_count = 0

    try:
        with connection.cursor() as cursor:
            if args.truncate:
                cursor.execute("TRUNCATE TABLE warning_disposal_record")
                print("Table truncated.")

            for row in soil_rows:
                record_id = str(row.get("id") or "").strip()
                if not record_id:
                    skipped += 1
                    continue

                sn = str(row.get("sn") or "").strip().upper()
                warn_time = row.get("warn_time")
                create_time = row.get("create_time")
                pub_time = row.get("pub_time")
                pub_status = int(row.get("pub_status") or 0)
                warn_level = str(row.get("warn_level") or "").strip()
                warn_level_code = row.get("warn_level_code")
                warn_value = str(row.get("warn_value") or "").strip() or None
                region_code = str(row.get("region_code") or "").strip() or None
                address = str(row.get("address") or "").strip() or None
                do_advice = row.get("do_advice")
                pub_user = str(row.get("pub_user") or "").strip() or None
                pub_user_name = str(row.get("pub_user_name") or "").strip() or None
                pub_short_message_flag = row.get("pub_short_message_flag")
                content = row.get("content")

                city, county = parse_address(address or "")
                if not city and region_code:
                    city, county = lookup_city_county_from_region(cursor, region_code)
                    if city:
                        fallback_count += 1

                cursor.execute(
                    """
                    INSERT INTO warning_disposal_record
                      (id, sn, warn_time, create_time, pub_time, pub_status,
                       warn_level, warn_level_code, warn_value,
                       city, county, region_code, address,
                       do_advice, pub_user, pub_user_name,
                       pub_short_message_flag, content)
                    VALUES
                      (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                      pub_time = VALUES(pub_time),
                      pub_status = VALUES(pub_status),
                      do_advice = VALUES(do_advice)
                    """,
                    (
                        record_id,
                        sn,
                        warn_time,
                        create_time,
                        pub_time,
                        pub_status,
                        warn_level,
                        warn_level_code,
                        warn_value,
                        city,
                        county,
                        region_code,
                        address,
                        do_advice,
                        pub_user,
                        pub_user_name,
                        pub_short_message_flag,
                        content,
                    ),
                )
                inserted += 1

        connection.commit()
        print(
            f"Done: inserted/updated={inserted}, skipped={skipped}, "
            f"sys_region fallback used={fallback_count}"
        )
    finally:
        connection.close()


if __name__ == "__main__":
    main()
