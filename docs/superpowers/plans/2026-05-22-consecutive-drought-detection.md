# Consecutive Drought State Detection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增"持续状态识别"能力——用户可以问"哪些地区连续3天以上出现重旱预警"，agent 返回具体地区、起止日期、连续天数。

**Architecture:** 新建 `ConsecutiveDroughtService` 用 SQL gaps-and-islands 算法（ROW_NUMBER 窗口函数）在 MySQL 里计算连续干旱天数。`TurnRouteDecisionService` 新增关键词检测路由到 `consecutive_drought`，`DataAnswerService` 新增 `_reply_consecutive_drought` 处理并返回确定性字符串结果。全程无 LLM 参与。

**Tech Stack:** Python / FastAPI (agent), MySQL 8（ROW_NUMBER 窗口函数）

---

## 背景知识（执行前必读）

### 干旱判定逻辑
`metric_rule` 表 `soil_warning_v1` 定义：
- **重旱**：`water20cm < 50 AND NOT (water20cm = 0 AND t20cm = 0)`（排除设备故障）
- **涝渍**：`water20cm >= 150`（6-10月暂停）
- **设备故障**：`water20cm = 0 AND t20cm = 0`

### 连续天数算法（Gaps and Islands）
```sql
-- 每个地区每天是否有干旱设备
daily_drought(city, county, day, drought_device_count)

-- 从连续日期中减去 ROW_NUMBER，相同组 = 连续天
grp = DATE_SUB(day, INTERVAL ROW_NUMBER() OVER (PARTITION BY city, county ORDER BY day) DAY)

-- 每个 (city, county, grp) 的连续跨度即为一个"岛"
```

### 数据密度
`fact_soil_moisture` 约 145,000 条，最新日期 2026-04-13，每个 county 每天约 5-15 条记录，查询时间窗口建议 ≤ 90 天。

---

## File Map

| 文件 | 变更类型 | 职责 |
|---|---|---|
| `apps/agent/app/services/consecutive_drought_service.py` | Create | SQL 查询：返回连续干旱区域列表 |
| `apps/agent/app/services/turn_route_decision_service.py` | Modify | 新增 `_is_consecutive_drought_query` + `_classify_subject` 分支 |
| `apps/agent/app/services/data_answer_service.py` | Modify | 新增路由分发 + `_reply_consecutive_drought` 处理方法 |
| `apps/agent/tests/test_consecutive_drought_service_unittest.py` | Create | SQL 服务单测 |
| `apps/agent/tests/test_turn_route_decision_service_unittest.py` | Modify | 新增路由检测测试用例 |

---

## Task 1: `ConsecutiveDroughtService` — SQL gaps-and-islands 查询

**Files:**
- Create: `apps/agent/app/services/consecutive_drought_service.py`
- Create: `apps/agent/tests/test_consecutive_drought_service_unittest.py`

### Step 1: 写失败测试

- [ ] 新建 `apps/agent/tests/test_consecutive_drought_service_unittest.py`：

```python
"""Unit tests for ConsecutiveDroughtService."""

from __future__ import annotations

import unittest
from datetime import date
from typing import Any


class FakeSoilRepository:
    """Returns pre-built daily_drought rows as if queried from MySQL."""

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def query_raw(self, sql: str, params: tuple) -> list[dict[str, Any]]:
        return self._rows


class ConsecutiveDroughtServiceTest(unittest.TestCase):

    def _make_service(self, rows):
        from app.services.consecutive_drought_service import ConsecutiveDroughtService
        repo = FakeSoilRepository(rows)
        svc = ConsecutiveDroughtService(soil_repository=repo)
        return svc

    def test_returns_streaks_meeting_min_days(self):
        svc = self._make_service([
            {"city": "常州市", "county": "溧阳市", "streak_start": date(2026, 4, 11),
             "streak_end": date(2026, 4, 13), "consecutive_days": 3},
        ])
        result = svc.query(min_consecutive_days=3, window_days=30)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["city"], "常州市")
        self.assertEqual(result[0]["consecutive_days"], 3)

    def test_empty_when_no_streaks(self):
        svc = self._make_service([])
        result = svc.query(min_consecutive_days=3, window_days=30)
        self.assertEqual(result, [])

    def test_streaks_below_min_days_excluded(self):
        svc = self._make_service([
            {"city": "南京市", "county": "六合区", "streak_start": date(2026, 4, 1),
             "streak_end": date(2026, 4, 2), "consecutive_days": 2},
        ])
        result = svc.query(min_consecutive_days=3, window_days=30)
        self.assertEqual(result, [])

    def test_build_sql_contains_window_functions(self):
        from app.services.consecutive_drought_service import ConsecutiveDroughtService
        sql = ConsecutiveDroughtService._build_sql(
            min_consecutive_days=3, window_days=30, warning_type="heavy_drought", region_filter=""
        )
        self.assertIn("ROW_NUMBER()", sql)
        self.assertIn("PARTITION BY", sql)
        self.assertIn("water20cm < 50", sql)
        self.assertIn("3", sql)

    def test_build_sql_waterlogging(self):
        from app.services.consecutive_drought_service import ConsecutiveDroughtService
        sql = ConsecutiveDroughtService._build_sql(
            min_consecutive_days=2, window_days=30, warning_type="waterlogging", region_filter=""
        )
        self.assertIn("water20cm >= 150", sql)

    def test_build_sql_any_warning(self):
        from app.services.consecutive_drought_service import ConsecutiveDroughtService
        sql = ConsecutiveDroughtService._build_sql(
            min_consecutive_days=3, window_days=30, warning_type=None, region_filter=""
        )
        self.assertIn("water20cm < 50", sql)
        self.assertIn("water20cm >= 150", sql)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **运行测试，确认失败**

```bash
cd apps/agent
python -m pytest tests/test_consecutive_drought_service_unittest.py -v
```

Expected: `ModuleNotFoundError: consecutive_drought_service`

### Step 2: 实现 `ConsecutiveDroughtService`

- [ ] 新建 `apps/agent/app/services/consecutive_drought_service.py`：

```python
"""Query regions with consecutive drought days using gaps-and-islands SQL."""

from __future__ import annotations

from typing import Any


_HEAVY_DROUGHT_PREDICATE = (
    "water20cm < 50 AND NOT (water20cm = 0 AND t20cm = 0)"
)
_WATERLOGGING_PREDICATE = "water20cm >= 150"
_ANY_WARNING_PREDICATE = (
    "(water20cm < 50 AND NOT (water20cm = 0 AND t20cm = 0)) OR water20cm >= 150"
)


def _warning_predicate(warning_type: str | None) -> str:
    if warning_type == "heavy_drought":
        return _HEAVY_DROUGHT_PREDICATE
    if warning_type == "waterlogging":
        return _WATERLOGGING_PREDICATE
    return _ANY_WARNING_PREDICATE


class ConsecutiveDroughtService:
    """Find city/county regions with consecutive drought days."""

    def __init__(self, soil_repository: Any) -> None:
        self._repo = soil_repository

    def query(
        self,
        *,
        min_consecutive_days: int = 3,
        window_days: int = 30,
        warning_type: str | None = "heavy_drought",
        city_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        region_filter = f"AND city = '{city_filter}'" if city_filter else ""
        sql = self._build_sql(
            min_consecutive_days=min_consecutive_days,
            window_days=window_days,
            warning_type=warning_type,
            region_filter=region_filter,
        )
        rows = self._repo.query_raw(sql, ())
        return [
            r for r in rows
            if int(r.get("consecutive_days") or 0) >= min_consecutive_days
        ]

    @staticmethod
    def _build_sql(
        *,
        min_consecutive_days: int,
        window_days: int,
        warning_type: str | None,
        region_filter: str,
    ) -> str:
        predicate = _warning_predicate(warning_type)
        return f"""
WITH daily_drought AS (
  SELECT
    city,
    county,
    DATE(create_time) AS day,
    SUM(CASE WHEN {predicate} THEN 1 ELSE 0 END) AS drought_device_count
  FROM fact_soil_moisture
  WHERE create_time >= DATE_SUB(CURDATE(), INTERVAL {window_days} DAY)
    {region_filter}
  GROUP BY city, county, DATE(create_time)
  HAVING drought_device_count > 0
),
numbered AS (
  SELECT
    city, county, day,
    DATE_SUB(day, INTERVAL ROW_NUMBER() OVER (
      PARTITION BY city, county ORDER BY day
    ) DAY) AS grp
  FROM daily_drought
),
streaks AS (
  SELECT
    city, county,
    MIN(day) AS streak_start,
    MAX(day) AS streak_end,
    COUNT(*) AS consecutive_days
  FROM numbered
  GROUP BY city, county, grp
)
SELECT city, county, streak_start, streak_end, consecutive_days
FROM streaks
WHERE consecutive_days >= {min_consecutive_days}
ORDER BY consecutive_days DESC, streak_end DESC
"""
```

### Step 3: `SoilRepository.query_raw` 验证

- [ ] 检查 `SoilRepository` 是否已有 `query_raw` 方法：

```bash
grep -n "def query_raw\|def execute\|def fetch" apps/agent/app/repositories/soil_repository.py | head -10
```

如果不存在，在 `soil_repository.py` 中添加：

```python
def query_raw(self, sql: str, params: tuple) -> list[dict[str, Any]]:
    """Execute a raw SELECT and return rows as dicts."""
    connection = self._connect()
    if not connection:
        return []
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return list(cursor.fetchall())
    finally:
        connection.close()
```

### Step 4: 运行测试，确认通过

- [ ] 

```bash
cd apps/agent
python -m pytest tests/test_consecutive_drought_service_unittest.py -v
```

Expected: `6 passed`

### Step 5: Commit

- [ ] 

```bash
git add apps/agent/app/services/consecutive_drought_service.py \
        apps/agent/app/repositories/soil_repository.py \
        apps/agent/tests/test_consecutive_drought_service_unittest.py
git commit -m "feat(agent): add ConsecutiveDroughtService with gaps-and-islands SQL"
```

---

## Task 2: 路由检测 — `TurnRouteDecisionService`

**Files:**
- Modify: `apps/agent/app/services/turn_route_decision_service.py`
- Modify: `apps/agent/tests/test_turn_route_decision_service_unittest.py`（或对应测试文件）

### Step 1: 写路由检测测试

- [ ] 在现有路由测试文件末尾加测试（找到 `test_turn_route_decision_service_unittest.py`）：

```python
class ConsecutiveDroughtRouteTest(unittest.TestCase):
    """TurnRouteDecisionService must route consecutive drought queries correctly."""

    def setUp(self):
        from app.services.turn_route_decision_service import TurnRouteDecisionService
        self.svc = TurnRouteDecisionService()

    def _route(self, text):
        result = self.svc.decide(message=text)
        return result.route

    def test_consecutive_drought_basic(self):
        self.assertEqual(self._route("哪些地区连续3天以上出现重旱预警"), "consecutive_drought")

    def test_consecutive_drought_without_number(self):
        self.assertEqual(self._route("哪些地区连续出现干旱"), "consecutive_drought")

    def test_consecutive_drought_chixu(self):
        self.assertEqual(self._route("持续3天干旱的地区有哪些"), "consecutive_drought")

    def test_normal_warning_not_routed_to_consecutive(self):
        route = self._route("最近有哪些预警记录")
        self.assertNotEqual(route, "consecutive_drought")

    def test_summary_not_routed_to_consecutive(self):
        route = self._route("南京最近墒情怎么样")
        self.assertNotEqual(route, "consecutive_drought")
```

- [ ] **运行，确认失败**

```bash
cd apps/agent
python -m pytest tests/test_turn_route_decision_service_unittest.py::ConsecutiveDroughtRouteTest -v
```

Expected: `FAILED` — route 返回 `warning_record` 或 `safe_hint`，不是 `consecutive_drought`

### Step 2: 在 `turn_route_decision_service.py` 中添加检测方法

- [ ] 在 `_is_warning_disposal_query` 方法附近（约第 744 行后）添加静态方法：

```python
@staticmethod
def _is_consecutive_drought_query(text: str) -> bool:
    has_consecutive = "连续" in text or "持续" in text
    has_warning_context = any(
        token in text
        for token in ("干旱", "重旱", "涝渍", "预警", "异常")
    )
    return has_consecutive and has_warning_context
```

- [ ] 在 `_classify_subject` 方法中，在第一行（`template` 检测）**之后**、`_is_warning_rule_query` **之前**加入新分支：

```python
@staticmethod
def _classify_subject(text: str, has_city_entity: bool = False, has_time_signal: bool = False) -> str:
    if any(token in text for token in TEMPLATE_TOKENS):
        return "template"
    if TurnRouteDecisionService._is_consecutive_drought_query(text):   # ← 新增，必须在 warning_record 之前
        return "consecutive_drought"
    if TurnRouteDecisionService._is_warning_rule_query(text):
        return "warning_rule"
    # ... 其余不变
```

- [ ] 在 `_decide_from_raw` 方法（约第 284 行，`subject == "unsupported_derived"` 分支前后），加入：

```python
if subject == "consecutive_drought":
    return self._decision(
        route="consecutive_drought",
        normalized_text=normalized_text,
        normalized_changed=normalized_changed,
        query_shape=QueryShape(subject="soil", action="consecutive_drought", grain="region", mode="standalone"),
        reason_codes=("consecutive_drought_query",),
        entities=extracted_entities,
        extra={
            "time_start": getattr(time_evidence, "start_time", None),
            "time_end": getattr(time_evidence, "end_time", None),
        },
        route_source="direct",
    )
```

### Step 3: 运行测试，确认通过

- [ ] 

```bash
cd apps/agent
python -m pytest tests/test_turn_route_decision_service_unittest.py::ConsecutiveDroughtRouteTest -v
```

Expected: `5 passed`

### Step 4: 全量路由测试，无回归

- [ ] 

```bash
cd apps/agent
python -m pytest tests/test_turn_route_decision_service_unittest.py -v --tb=short 2>&1 | tail -10
```

Expected: 无新 failure。

### Step 5: Commit

- [ ] 

```bash
git add apps/agent/app/services/turn_route_decision_service.py \
        apps/agent/tests/test_turn_route_decision_service_unittest.py
git commit -m "feat(agent): route consecutive drought queries to consecutive_drought"
```

---

## Task 3: 回答处理 — `DataAnswerService._reply_consecutive_drought`

**Files:**
- Modify: `apps/agent/app/services/data_answer_service.py`

### Step 1: 注入 `ConsecutiveDroughtService`

- [ ] 在 `DataAnswerService.__init__` 参数列表（约第 162 行）中加入：

```python
consecutive_drought_service: Any | None = None,
```

- [ ] 在 `__init__` 方法体中初始化（加在其他 service 初始化的末尾）：

```python
if consecutive_drought_service is not None:
    self.consecutive_drought_service = consecutive_drought_service
else:
    from app.services.consecutive_drought_service import ConsecutiveDroughtService
    self.consecutive_drought_service = ConsecutiveDroughtService(
        soil_repository=self.soil_repository
    )
```

### Step 2: 在路由分发处加入 `consecutive_drought` 分支

- [ ] 在 `_reply_impl` 中找到 warning_disposal/warning_group 路由分发区域（约第 300-360 行），在第一个 `if route_decision.route` 块之前加入：

```python
if route_decision.route == "consecutive_drought":
    return await self._reply_consecutive_drought(
        message=text,
        session_id=session_id,
        turn_id=turn_id,
        current_context=context,
    )
```

### Step 3: 添加参数提取辅助方法

- [ ] 在 `DataAnswerService` 中加入静态方法（放在 `_is_unsupported_derived_analysis_request` 附近）：

```python
@staticmethod
def _extract_consecutive_days(text: str) -> int:
    """Extract minimum consecutive days from text; default 3."""
    import re
    match = re.search(r"(\d+)\s*天", text)
    if match:
        n = int(match.group(1))
        return max(1, min(n, 90))
    return 3

@staticmethod
def _extract_warning_type_for_consecutive(text: str) -> str | None:
    """Detect warning type from text for consecutive drought query."""
    if "涝渍" in text:
        return "waterlogging"
    if any(t in text for t in ("重旱", "干旱")):
        return "heavy_drought"
    return "heavy_drought"  # default
```

### Step 4: 实现 `_reply_consecutive_drought`

- [ ] 在 `DataAnswerService` 中加入方法（放在 `_reply_warning_count` 附近）：

```python
async def _reply_consecutive_drought(
    self,
    *,
    message: str,
    session_id: str,
    turn_id: int,
    current_context: dict[str, Any],
) -> dict[str, Any]:
    min_days = self._extract_consecutive_days(message)
    warning_type = self._extract_warning_type_for_consecutive(message)
    window_days = 30

    warning_label = {"heavy_drought": "重旱", "waterlogging": "涝渍"}.get(warning_type or "", "预警")

    rows = await asyncio.to_thread(
        self.consecutive_drought_service.query,
        min_consecutive_days=min_days,
        window_days=window_days,
        warning_type=warning_type,
    )

    query_id = f"cd_{session_id}_{turn_id}"

    if not rows:
        final_text = f"近{window_days}天内，未发现连续{min_days}天以上出现{warning_label}的地区。"
        return {
            "turn_id": turn_id,
            "answer_kind": "data",
            "capability": "consecutive_drought",
            "output_mode": "normal",
            "final_text": final_text,
            "blocks": [{"block_id": f"block_{query_id}", "block_type": "text", "text": final_text}],
            "topic": self._topic_payload(current_context),
            "turn_context": current_context,
            "query_ref": {"has_query": False, "snapshot_ids": []},
            "conversation_closed": False,
            "session_reset": False,
            "query_log_entries": [],
        }

    lines = []
    for row in rows:
        start = str(row.get("streak_start") or "")[:10]
        end = str(row.get("streak_end") or "")[:10]
        days = row.get("consecutive_days", 0)
        city = row.get("city", "")
        county = row.get("county", "")
        region = f"{city}{county}" if county and county not in city else city
        lines.append(f"- {region}：连续 {days} 天（{start} 至 {end}）")

    max_days = max(int(r.get("consecutive_days") or 0) for r in rows)
    summary = (
        f"近{window_days}天内，共 {len(rows)} 个地区出现连续{min_days}天以上{warning_label}，"
        f"最长连续 {max_days} 天："
    )
    final_text = summary + "\n" + "\n".join(lines)

    return {
        "turn_id": turn_id,
        "answer_kind": "data",
        "capability": "consecutive_drought",
        "output_mode": "normal",
        "final_text": final_text,
        "blocks": [{"block_id": f"block_{query_id}", "block_type": "text", "text": final_text}],
        "topic": self._topic_payload(current_context),
        "turn_context": current_context,
        "query_ref": {"has_query": False, "snapshot_ids": []},
        "conversation_closed": False,
        "session_reset": False,
        "query_log_entries": [],
    }
```

### Step 5: 写集成测试

- [ ] 在 `test_data_answer_service_unittest.py` 末尾加：

```python
class ConsecutiveDroughtAnswerTest(unittest.IsolatedAsyncioTestCase):
    """DataAnswerService._reply_consecutive_drought produces correct responses."""

    def _make_service(self, drought_rows):
        from app.services.data_answer_service import DataAnswerService
        from app.services.consecutive_drought_service import ConsecutiveDroughtService

        class FakeDroughtService:
            def __init__(self, rows):
                self._rows = rows
            def query(self, **_kwargs):
                return self._rows

        return DataAnswerService(
            soil_repository=SeedSoilRepository(),
            consecutive_drought_service=FakeDroughtService(drought_rows),
        )

    async def test_empty_result_text(self):
        svc = self._make_service([])
        result = await svc.reply(
            message="哪些地区连续3天以上出现重旱预警",
            session_id="s1", turn_id=1, current_context=None,
        )
        self.assertIn("未发现", result["final_text"])
        self.assertEqual(result["answer_kind"], "data")

    async def test_with_results_text(self):
        from datetime import date
        svc = self._make_service([
            {"city": "常州市", "county": "溧阳市",
             "streak_start": date(2026, 4, 11), "streak_end": date(2026, 4, 13),
             "consecutive_days": 3},
        ])
        result = await svc.reply(
            message="哪些地区连续3天以上出现重旱预警",
            session_id="s1", turn_id=1, current_context=None,
        )
        self.assertIn("常州市", result["final_text"])
        self.assertIn("3 天", result["final_text"])
        self.assertEqual(result["capability"], "consecutive_drought")

    async def test_min_days_extracted_from_message(self):
        from datetime import date
        svc = self._make_service([
            {"city": "南京市", "county": "六合区",
             "streak_start": date(2026, 4, 1), "streak_end": date(2026, 4, 5),
             "consecutive_days": 5},
        ])
        result = await svc.reply(
            message="连续5天干旱的地区",
            session_id="s1", turn_id=1, current_context=None,
        )
        self.assertIn("5 天", result["final_text"])
```

- [ ] **运行全量测试**

```bash
cd apps/agent
python -m pytest tests/test_data_answer_service_unittest.py::ConsecutiveDroughtAnswerTest -v
```

Expected: `3 passed`

### Step 6: 全量 agent 单测，无回归

- [ ] 

```bash
cd apps/agent
python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: 全部 pass。

### Step 7: Commit

- [ ] 

```bash
git add apps/agent/app/services/data_answer_service.py \
        apps/agent/tests/test_data_answer_service_unittest.py
git commit -m "feat(agent): add _reply_consecutive_drought handler"
```

---

## Task 4: 更新 SAFE_HINT_TEXT 和 DOMAIN_INTENT_TOKENS

**Files:**
- Modify: `apps/agent/app/services/data_answer_service.py`

让系统知道这是支持的能力，`InputGuard` 不会误拦截。

- [ ] 找到 `SAFE_HINT_TEXT`（约第 115 行），把说明扩展：

将：
```python
SAFE_HINT_TEXT = "我可以帮你查墒情概况、地区/墒情仪/记录明细、按地区汇总，以及查看预警规则和模板。你可以直接说地区、设备或时间范围，例如：南京最近7天墒情怎么样，或最近30天按地区汇总墒情数据。"
```

改为：
```python
SAFE_HINT_TEXT = "我可以帮你查墒情概况、地区/墒情仪/记录明细、按地区汇总、连续干旱地区识别，以及查看预警规则和模板。你可以直接说地区、设备或时间范围，例如：哪些地区连续3天以上出现重旱预警，或最近30天按地区汇总墒情数据。"
```

- [ ] 找到 `DOMAIN_INTENT_TOKENS`（约第 91 行），加入"连续"和"持续"：

```python
DOMAIN_INTENT_TOKENS = (
    "墒情",
    "预警",
    "异常",
    "情况",
    "数据",
    "点位",
    "设备",
    "记录",
    "详情",
    "明细",
    "排名",
    "严重",
    "规则",
    "模板",
    "模版",
    "连续",   # ← 新增
    "持续",   # ← 新增
)
```

- [ ] **Commit**

```bash
git add apps/agent/app/services/data_answer_service.py
git commit -m "feat(agent): add consecutive drought to domain tokens and help text"
```

---

## Task 5: 端到端验活

- [ ] **重启 agent**

```bash
pkill -f "uvicorn app.main:app" 2>/dev/null || true
bash scripts/dev/start-local-agent.sh > /tmp/agent.log 2>&1 &
sleep 5
```

- [ ] **直接调用 agent 测试**

```bash
source .env
curl -fsS -X POST "http://localhost:18010/chat-v2" \
  -H "Content-Type: application/json" \
  -d '{"message":"哪些地区连续3天以上出现重旱预警","session_id":"test-cd","turn_id":1,"current_context":null}' \
  | python3 -c '
import json, sys
d = json.load(sys.stdin)
print("capability:", d.get("capability"))
print("answer_kind:", d.get("answer_kind"))
print("final_text:", d.get("final_text", "")[:300])
'
```

Expected:
```
capability: consecutive_drought
answer_kind: data
final_text: 近30天内，共 X 个地区出现连续3天以上重旱...
```

- [ ] **测试"无结果"场景**

```bash
source .env
curl -fsS -X POST "http://localhost:18010/chat-v2" \
  -H "Content-Type: application/json" \
  -d '{"message":"哪些地区连续30天以上出现重旱预警","session_id":"test-cd","turn_id":2,"current_context":null}' \
  | python3 -c '
import json, sys
d = json.load(sys.stdin)
print(d.get("final_text", "")[:200])
'
```

Expected: 包含"未发现"。

- [ ] **通过 web BFF 测试（完整链路）**

```bash
source .env
AUTH_TOKEN=$(curl -fsS -X POST "http://localhost:3000/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$HEALTH_USERNAME\",\"password\":\"$HEALTH_PASSWORD\"}" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin).get("token",""))')

curl -fsS -X POST "http://localhost:3000/api/agent/chat" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{"message":"哪些地区连续3天以上出现重旱预警","session_id":"test-cd2","turn_id":1,"client_message_id":"cd-1"}' \
  | python3 -c '
import json, sys
d = json.load(sys.stdin)
print("answer_kind:", d.get("answer_kind"))
print(d.get("final_text","")[:300])
'
```

- [ ] **按 `/deploy` skill 完整走一遍发布**（bump version, build, restart, smoke test）
