from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


FALLBACK_RECORDS = [
    {
        "device_sn": "SNS00204333",
        "city_name": "南通市",
        "county_name": "如东县",
        "record_time": "2026-04-20 00:00:00",
        "water20cm": 83.18,
        "water40cm": 82.40,
        "water60cm": 80.12,
        "water80cm": 78.55,
    },
    {
        "device_sn": "SNS00213807",
        "city_name": "镇江市",
        "county_name": "镇江经开区",
        "record_time": "2026-04-20 00:00:00",
        "water20cm": 42.30,
        "water40cm": 48.20,
        "water60cm": 51.00,
        "water80cm": 55.10,
    },
]


@dataclass
class SoilRepository:
    mysql_host: str | None = None
    mysql_port: int | None = None
    mysql_database: str | None = None
    mysql_user: str | None = None
    mysql_password: str | None = None

    @classmethod
    def from_env(cls) -> "SoilRepository":
        return cls(
            mysql_host=os.getenv("MYSQL_HOST"),
            mysql_port=int(os.getenv("MYSQL_PORT", "3306")),
            mysql_database=os.getenv("MYSQL_DATABASE"),
            mysql_user=os.getenv("MYSQL_USER"),
            mysql_password=os.getenv("MYSQL_PASSWORD"),
        )

    def _connect(self):
        if not all([self.mysql_host, self.mysql_database, self.mysql_user, self.mysql_password]):
            return None
        try:
            import pymysql
            return pymysql.connect(
                host=self.mysql_host,
                port=self.mysql_port or 3306,
                user=self.mysql_user,
                password=self.mysql_password,
                database=self.mysql_database,
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=2,
                read_timeout=3,
                write_timeout=3,
            )
        except Exception:
            return None

    def latest_records(self, limit: int = 20) -> list[dict[str, Any]]:
        connection = self._connect()
        if not connection:
            return FALLBACK_RECORDS[:limit]
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT device_sn, city_name, county_name,
                           DATE_FORMAT(record_time, '%%Y-%%m-%%d %%H:%%i:%%s') AS record_time,
                           water20cm, water40cm, water60cm, water80cm
                    FROM fact_soil_moisture
                    ORDER BY record_time DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                rows = cursor.fetchall()
                return rows or FALLBACK_RECORDS[:limit]
        finally:
            connection.close()

    def latest_record_by_device(self, device_sn: str) -> dict[str, Any] | None:
        connection = self._connect()
        if not connection:
            return next((record for record in FALLBACK_RECORDS if record["device_sn"] == device_sn), None)
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT device_sn, city_name, county_name,
                           DATE_FORMAT(record_time, '%%Y-%%m-%%d %%H:%%i:%%s') AS record_time,
                           water20cm, water40cm, water60cm, water80cm
                    FROM fact_soil_moisture
                    WHERE device_sn = %s
                    ORDER BY record_time DESC
                    LIMIT 1
                    """,
                    (device_sn,),
                )
                row = cursor.fetchone()
                return row or next((record for record in FALLBACK_RECORDS if record["device_sn"] == device_sn), None)
        finally:
            connection.close()
