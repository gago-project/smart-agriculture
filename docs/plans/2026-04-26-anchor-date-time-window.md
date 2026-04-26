# Anchor-Date Time Window Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Support time expressions like `"2025-12-01之前50天"`（50 days ending on Dec 1）and `"2025-12-01之后30天"`（30 days starting on Dec 1）in addition to existing relative and exact-date windows.

**Architecture:** Three isolated changes: (1) intent_slot_service parses the new pattern and fixes a TOP_N_RE false positive, (2) time_service resolves the new `anchor_before_N_days` / `anchor_after_N_days` labels into concrete start/end timestamps, (3) soil_query_service skips the latest_business_time DB fetch for anchor ranges. Documentation updated last.

**Tech Stack:** Python 3.11, re (stdlib), datetime (stdlib), unittest

---

## File Map

| File | Role |
|---|---|
| `apps/agent/app/services/intent_slot_service.py` | Add `ANCHOR_DAYS_RE`, fix `TOP_N_RE`, update `_parse_time_range` and `_has_explicit_time_expression` |
| `apps/agent/app/services/time_service.py` | Add `ANCHOR_BEFORE_RE` / `ANCHOR_AFTER_RE`, add `_parse_date`, add anchor resolution branches in `resolve()`, import `timedelta` |
| `apps/agent/app/services/soil_query_service.py` | Skip `latest_business_time` fetch when `time_range` starts with `anchor_` |
| `apps/agent/plans/1/1.plan.md` | Update time contract section with new input patterns |
| `apps/agent/tests/test_time_contract_unittest.py` | Anchor window resolution tests |

---

## Task 1: Fix TOP_N_RE false positive on "之前N天"

**Problem:** `TOP_N_RE = re.compile(r"前\s*(\d+)")` matches `"之前50"` in `"2025-12-01之前50天的哪些设备最严重"` and incorrectly extracts `top_n=50`.

**Files:**
- Modify: `apps/agent/app/services/intent_slot_service.py:24`
- Test: `apps/agent/tests/test_time_contract_unittest.py`

- [ ] **Step 1: Write the failing test**

Add to `TimeContractTest` in `apps/agent/tests/test_time_contract_unittest.py`:

```python
def test_anchor_before_phrase_should_not_produce_top_n(self) -> None:
    """Verify '之前50天' is not misread as top_n=50."""
    import asyncio

    async def run_case() -> None:
        service = IntentSlotService(repository=self.repository, qwen_client=None)
        result = await service.parse("2025-12-01之前50天的哪些设备最严重", "fix-top-n")
        self.assertNotEqual(result.slots.get("top_n"), 50)

    asyncio.run(run_case())

def test_explicit_top_n_still_works_after_fix(self) -> None:
    """Verify 前5 still produces top_n=5 after the lookbehind fix."""
    import asyncio

    async def run_case() -> None:
        service = IntentSlotService(repository=self.repository, qwen_client=None)
        result = await service.parse("过去一个月前5个最严重的设备", "fix-top-n-ok")
        self.assertEqual(result.slots.get("top_n"), 5)

    asyncio.run(run_case())
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd apps/agent
python -m unittest tests.test_time_contract_unittest.TimeContractTest.test_anchor_before_phrase_should_not_produce_top_n tests.test_time_contract_unittest.TimeContractTest.test_explicit_top_n_still_works_after_fix -v
```

Expected: `test_anchor_before_phrase_should_not_produce_top_n` FAIL (top_n is 50), second test may pass or fail.

- [ ] **Step 3: Fix TOP_N_RE with negative lookbehind**

In `apps/agent/app/services/intent_slot_service.py`, change line 24:

```python
# Before
TOP_N_RE = re.compile(r"前\s*(\d+)")

# After
TOP_N_RE = re.compile(r"(?<!之)前\s*(\d+)")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m unittest tests.test_time_contract_unittest.TimeContractTest.test_anchor_before_phrase_should_not_produce_top_n tests.test_time_contract_unittest.TimeContractTest.test_explicit_top_n_still_works_after_fix -v
```

Expected: both PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/agent/app/services/intent_slot_service.py apps/agent/tests/test_time_contract_unittest.py
git commit -m "fix: prevent '之前N天' from being misread as top_n by TOP_N_RE"
```

---

## Task 2: Parse anchor-date time expressions in IntentSlotService

**Files:**
- Modify: `apps/agent/app/services/intent_slot_service.py`
- Test: `apps/agent/tests/test_time_contract_unittest.py`

- [ ] **Step 1: Write the failing tests**

Add to `TimeContractTest`:

```python
def test_anchor_before_should_parse_to_correct_time_range_and_target_date(self) -> None:
    """Verify '2025-12-01之前50天' sets time_range and target_date correctly."""
    import asyncio

    async def run_case() -> None:
        service = IntentSlotService(repository=self.repository, qwen_client=None)
        result = await service.parse("2025-12-01之前50天的哪些设备最严重", "anchor-before")
        self.assertEqual(result.slots.get("time_range"), "anchor_before_50_days")
        self.assertEqual(result.slots.get("target_date"), "2025-12-01")
        self.assertTrue(result.slots.get("time_explicit"))

    asyncio.run(run_case())

def test_anchor_after_should_parse_to_correct_time_range_and_target_date(self) -> None:
    """Verify '2025-12-01之后30天' sets time_range and target_date correctly."""
    import asyncio

    async def run_case() -> None:
        service = IntentSlotService(repository=self.repository, qwen_client=None)
        result = await service.parse("2025-12-01之后30天整体墒情怎么样", "anchor-after")
        self.assertEqual(result.slots.get("time_range"), "anchor_after_30_days")
        self.assertEqual(result.slots.get("target_date"), "2025-12-01")
        self.assertTrue(result.slots.get("time_explicit"))

    asyncio.run(run_case())

def test_plain_iso_date_still_resolves_as_exact_date(self) -> None:
    """Verify bare YYYY-MM-DD with no direction still gives exact_date."""
    import asyncio

    async def run_case() -> None:
        service = IntentSlotService(repository=self.repository, qwen_client=None)
        result = await service.parse("2025-12-01如东县墒情", "exact-date")
        self.assertEqual(result.slots.get("time_range"), "exact_date")
        self.assertEqual(result.slots.get("target_date"), "2025-12-01")

    asyncio.run(run_case())
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m unittest \
  tests.test_time_contract_unittest.TimeContractTest.test_anchor_before_should_parse_to_correct_time_range_and_target_date \
  tests.test_time_contract_unittest.TimeContractTest.test_anchor_after_should_parse_to_correct_time_range_and_target_date \
  tests.test_time_contract_unittest.TimeContractTest.test_plain_iso_date_still_resolves_as_exact_date -v
```

Expected: first two FAIL (`time_range` will be `exact_date` or `None`), third PASS.

- [ ] **Step 3: Add ANCHOR_DAYS_RE constant and update _parse_time_range**

In `apps/agent/app/services/intent_slot_service.py`:

Add after `DATE_RE` (around line 24):
```python
ANCHOR_DAYS_RE = re.compile(r"(20\d{2}-\d{2}-\d{2})\s*(之前|之后)\s*(\d{1,4})\s*天")
```

Update `_parse_time_range` — the anchor check must come **before** the existing `DATE_RE` check:

```python
def _parse_time_range(self, text: str) -> tuple[str | None, str | None]:
    """Map user time phrases to the finite time-window vocabulary."""
    # Anchored window must be checked before plain date so "2025-12-01之前50天"
    # is not swallowed by the exact_date branch.
    anchor_match = ANCHOR_DAYS_RE.search(text)
    if anchor_match:
        anchor_date = anchor_match.group(1)
        direction = anchor_match.group(2)   # "之前" or "之后"
        n_days = int(anchor_match.group(3))
        direction_key = "before" if direction == "之前" else "after"
        raw_expr = f"{anchor_date}{direction}{n_days}天"
        return f"anchor_{direction_key}_{n_days}_days", raw_expr
    if DATE_RE.search(text):
        return "exact_date", DATE_RE.search(text).group(1)
    if "前天" in text:
        return "day_before_yesterday", "前天"
    # … rest of existing method unchanged …
```

- [ ] **Step 4: Update _has_explicit_time_expression to recognise anchor patterns**

The existing check already returns `True` when `DATE_RE` matches, and anchor expressions always contain the ISO date, so `DATE_RE` will still fire. **No change needed** — verify by tracing: `"2025-12-01之前50天"` → `DATE_RE.search(text)` matches `"2025-12-01"` → returns `True`. ✓

- [ ] **Step 5: Run tests to verify they pass**

```bash
python -m unittest \
  tests.test_time_contract_unittest.TimeContractTest.test_anchor_before_should_parse_to_correct_time_range_and_target_date \
  tests.test_time_contract_unittest.TimeContractTest.test_anchor_after_should_parse_to_correct_time_range_and_target_date \
  tests.test_time_contract_unittest.TimeContractTest.test_plain_iso_date_still_resolves_as_exact_date -v
```

Expected: all three PASS.

- [ ] **Step 6: Run the full time contract suite to check for regressions**

```bash
python -m unittest tests.test_time_contract_unittest -v
```

Expected: all tests PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/agent/app/services/intent_slot_service.py apps/agent/tests/test_time_contract_unittest.py
git commit -m "feat: parse anchor-date time windows (2025-12-01之前/之后N天) in IntentSlotService"
```

---

## Task 3: Resolve anchor time ranges to start/end timestamps in TimeResolveService

**Files:**
- Modify: `apps/agent/app/services/time_service.py`
- Modify: `apps/agent/app/services/soil_query_service.py`
- Test: `apps/agent/tests/test_time_contract_unittest.py`

- [ ] **Step 1: Write the failing tests**

Add to `TimeContractTest`:

```python
def test_anchor_before_50_days_should_resolve_to_correct_window(self) -> None:
    """Verify anchor_before_50_days ending on 2025-12-01 gives correct boundaries.

    Dec 1 inclusive, counting back 50 calendar days:
    Oct 13 (day 1) ... Dec 1 (day 50) → 19 Oct days + 30 Nov days + 1 Dec day = 50.
    """
    result = self.time_service.resolve(
        slots={"time_range": "anchor_before_50_days", "target_date": "2025-12-01"},
    )
    self.assertEqual(result["start_time"], "2025-10-13 00:00:00")
    self.assertEqual(result["end_time"], "2025-12-01 23:59:59")
    self.assertEqual(result["resolved_time_range"], "anchor_before_50_days")
    self.assertEqual(result["resolution_mode"], "anchor_window")
    self.assertEqual(result["time_basis"], "anchor_date")

def test_anchor_after_30_days_should_resolve_to_correct_window(self) -> None:
    """Verify anchor_after_30_days starting on 2025-12-01 gives correct boundaries.

    Dec 1 inclusive, counting forward 30 calendar days:
    Dec 1 (day 1) ... Dec 30 (day 30).
    """
    result = self.time_service.resolve(
        slots={"time_range": "anchor_after_30_days", "target_date": "2025-12-01"},
    )
    self.assertEqual(result["start_time"], "2025-12-01 00:00:00")
    self.assertEqual(result["end_time"], "2025-12-30 23:59:59")
    self.assertEqual(result["resolved_time_range"], "anchor_after_30_days")
    self.assertEqual(result["resolution_mode"], "anchor_window")

def test_anchor_window_does_not_need_latest_business_time_fetch(self) -> None:
    """Verify anchor ranges skip the latest_business_time DB query."""
    import asyncio

    async def run_case() -> None:
        result = await self.query_service.fetch_latest_business_time_if_needed(
            slots={"time_range": "anchor_before_50_days", "target_date": "2025-12-01"},
            intent="soil_severity_ranking",
        )
        self.assertIsNone(result)

    asyncio.run(run_case())
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m unittest \
  tests.test_time_contract_unittest.TimeContractTest.test_anchor_before_50_days_should_resolve_to_correct_window \
  tests.test_time_contract_unittest.TimeContractTest.test_anchor_after_30_days_should_resolve_to_correct_window \
  tests.test_time_contract_unittest.TimeContractTest.test_anchor_window_does_not_need_latest_business_time_fetch -v
```

Expected: all three FAIL.

- [ ] **Step 3: Add anchor resolution to TimeResolveService**

In `apps/agent/app/services/time_service.py`:

1. Add `timedelta` to the existing import (line 7):
```python
from datetime import datetime, time, timedelta
```

2. Add two module-level constants after `LAST_N_DAYS_RANGE_RE`:
```python
ANCHOR_BEFORE_RE = re.compile(r"^anchor_before_(\d+)_days$")
ANCHOR_AFTER_RE = re.compile(r"^anchor_after_(\d+)_days$")
```

3. Add a `_parse_date` static method to the class (alongside `_parse_datetime`):
```python
@staticmethod
def _parse_date(value: str | None) -> datetime | None:
    """Parse a bare YYYY-MM-DD anchor date into a datetime at midnight."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None
```

4. In `resolve()`, add the anchor branches **before** the existing `dynamic_days` branch (insert after the `elif resolved_time_range in {"last_2_years", ...}` block, before the `elif dynamic_days` block):

```python
elif ANCHOR_BEFORE_RE.match(resolved_time_range):
    anchor_before_match = ANCHOR_BEFORE_RE.match(resolved_time_range)
    n = int(anchor_before_match.group(1))
    anchor_dt = self._parse_date(slots.get("target_date"))
    if anchor_dt:
        payload.update({
            "resolution_mode": "anchor_window",
            "time_basis": "anchor_date",
            **self._day_window(anchor_dt, days=n),
        })
elif ANCHOR_AFTER_RE.match(resolved_time_range):
    anchor_after_match = ANCHOR_AFTER_RE.match(resolved_time_range)
    n = int(anchor_after_match.group(1))
    anchor_dt = self._parse_date(slots.get("target_date"))
    if anchor_dt:
        payload.update({
            "resolution_mode": "anchor_window",
            "time_basis": "anchor_date",
            "start_time": self._format_datetime(self._start_of_day(anchor_dt)),
            "end_time": self._format_datetime(self._end_of_day(anchor_dt + timedelta(days=n - 1))),
        })
```

- [ ] **Step 4: Skip latest_business_time fetch for anchor ranges in SoilQueryService**

In `apps/agent/app/services/soil_query_service.py`, update `fetch_latest_business_time_if_needed`:

```python
async def fetch_latest_business_time_if_needed(self, *, slots: dict[str, Any], intent: str) -> str | None:
    """Fetch latest business time only for relative/latest time windows."""
    del intent
    time_range = str(slots.get("time_range") or "")
    if time_range == "exact_date" or time_range.startswith("anchor_"):
        return None
    return await self.repository.latest_business_time_async()
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
python -m unittest \
  tests.test_time_contract_unittest.TimeContractTest.test_anchor_before_50_days_should_resolve_to_correct_window \
  tests.test_time_contract_unittest.TimeContractTest.test_anchor_after_30_days_should_resolve_to_correct_window \
  tests.test_time_contract_unittest.TimeContractTest.test_anchor_window_does_not_need_latest_business_time_fetch -v
```

Expected: all three PASS.

- [ ] **Step 6: Run the full time contract suite**

```bash
python -m unittest tests.test_time_contract_unittest -v
```

Expected: all tests PASS.

- [ ] **Step 7: Run the broader agent test suite to catch regressions**

```bash
python -m unittest discover -s tests -p "test_*.py" -v 2>&1 | tail -20
```

Expected: no new failures.

- [ ] **Step 8: Commit**

```bash
git add apps/agent/app/services/time_service.py apps/agent/app/services/soil_query_service.py apps/agent/tests/test_time_contract_unittest.py
git commit -m "feat: resolve anchor_before/after_N_days time windows in TimeResolveService"
```

---

## Task 4: Update time contract documentation

**Files:**
- Modify: `apps/agent/plans/1/1.plan.md`

- [ ] **Step 1: Update the time contract section**

In `apps/agent/plans/1/1.plan.md`, find the `## 当前时间契约` section and update the `### 输入语义` subsection to add the two new patterns:

```markdown
### 输入语义

- `今天`
- `昨天`
- `前天`
- `最近7天`
- `近N天 / 最近N天 / 过去N天`
- `最近一个月`
- `上周`
- `YYYY-MM-DD`
- `YYYY-MM-DD之前N天`（N 天窗口，以指定日期为结束边界，含当天）
- `YYYY-MM-DD之后N天`（N 天窗口，以指定日期为起始边界，含当天）
```

Also add a note under `### 解析结果`:

```markdown
- 锚点型时间窗（`anchor_before_N_days` / `anchor_after_N_days`）不依赖库内最新业务时间，
  `time_basis` 输出为 `anchor_date`，`resolution_mode` 输出为 `anchor_window`
```

- [ ] **Step 2: Commit**

```bash
git add apps/agent/plans/1/1.plan.md
git commit -m "docs: add anchor-date time window patterns to time contract"
```

---

## Self-Review

**Spec coverage:**
- TOP_N_RE false positive → Task 1 ✓
- Parse `YYYY-MM-DD之前N天` and `YYYY-MM-DD之后N天` → Task 2 ✓
- Resolve anchor labels to concrete start/end → Task 3 ✓
- Skip DB fetch for anchor ranges → Task 3 ✓
- Documentation update → Task 4 ✓
- Regressions caught → Task 3 Step 7 ✓

**Placeholder scan:** None found.

**Type consistency:**
- `ANCHOR_DAYS_RE` defined in Task 2, used in Task 2 only ✓
- `ANCHOR_BEFORE_RE` / `ANCHOR_AFTER_RE` defined and used in Task 3 only ✓
- `_parse_date` defined and used in Task 3 only ✓
- `time_range` slot string format `anchor_before_N_days` consistent across Tasks 2 and 3 ✓
- `target_date` slot key consistent across all tasks ✓
