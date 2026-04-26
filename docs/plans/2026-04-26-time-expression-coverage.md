# Time Expression Coverage Expansion

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend time expression parsing to cover seven missing patterns — relative-anchor windows ("7天前的前7天"), single relative days ("3天前"), calendar-month/week labels ("上个月", "本月", "本周"), week rolling windows ("过去N周"), and specific calendar months ("3月份") — and fix a TOP_N_RE false positive on "前N天".

**Architecture:** All changes follow the existing two-layer pattern: `IntentSlotService._parse_time_range` produces a canonical label string (and optionally a `target_month` slot for the calendar-month case), then `TimeResolveService.resolve()` converts that label to concrete `start_time`/`end_time` boundaries against `latest_business_time`. The `fetch_latest_business_time_if_needed` guard in `SoilQueryService` needs no changes — all new labels are relative so they already require `latest_business_time`.

**Tech Stack:** Python 3.11, `re` (stdlib), `datetime`/`calendar` (stdlib), `unittest`

---

## File Map

| File | Changes |
|---|---|
| `apps/agent/app/services/intent_slot_service.py` | Fix `TOP_N_RE`; add `RELATIVE_ANCHOR_DAYS_RE`, `N_DAYS_AGO_RE`, `N_WEEKS_RE`, `CALENDAR_MONTH_RE`; update `_parse_time_range` and `_has_explicit_time_expression`; add `target_month` to `SUPPORTED_SLOT_KEYS` |
| `apps/agent/app/services/time_service.py` | Add `N_DAYS_AGO_LABEL_RE`, `RELATIVE_BEFORE_AT_AGO_RE`; add `elif` branches in `resolve()` for all new labels; import `calendar` |
| `apps/agent/tests/test_time_contract_unittest.py` | Add parse + resolve tests for each new pattern |
| `apps/agent/plans/1/1.plan.md` | Update `### 输入语义` section |

---

## Task 1: Fix TOP_N_RE false positive on "前N天"

**Problem:** `TOP_N_RE = re.compile(r"(?<!之)前\s*(\d+)")` matches `前7` in `"7天前的前7天"` and produces `top_n=7`. The lookbehind only blocks `之前N`; it does not block `的前N天`.

**Fix:** add a negative lookahead `(?!\s*天)` so `前7天` is never captured as top_n.

**Files:**
- Modify: `apps/agent/app/services/intent_slot_service.py:23`
- Test: `apps/agent/tests/test_time_contract_unittest.py`

- [ ] **Step 1: Write the failing test**

Add to `TimeContractTest` in `apps/agent/tests/test_time_contract_unittest.py`:

```python
def test_relative_anchor_phrase_should_not_produce_top_n(self) -> None:
    """Verify '7天前的前7天' does not produce a top_n slot."""
    import asyncio

    async def run_case() -> None:
        service = IntentSlotService(repository=self.repository, qwen_client=None)
        result = await service.parse("7天前的前7天的情况", "fix-relative-top-n")
        self.assertNotIn("top_n", result.slots)

    asyncio.run(run_case())
```

- [ ] **Step 2: Run the test to confirm it fails**

```bash
cd apps/agent
PYTHONPATH=.:tests python -m unittest tests.test_time_contract_unittest.TimeContractTest.test_relative_anchor_phrase_should_not_produce_top_n -v
```

Expected: FAIL — `top_n=7` is in slots.

- [ ] **Step 3: Apply the fix**

In `apps/agent/app/services/intent_slot_service.py`, change line 23:

```python
# Before
TOP_N_RE = re.compile(r"(?<!之)前\s*(\d+)")

# After
TOP_N_RE = re.compile(r"(?<!之)前\s*(\d+)(?!\s*天)")
```

- [ ] **Step 4: Run the new test and the regression test**

```bash
PYTHONPATH=.:tests python -m unittest \
  tests.test_time_contract_unittest.TimeContractTest.test_relative_anchor_phrase_should_not_produce_top_n \
  tests.test_time_contract_unittest.TimeContractTest.test_anchor_before_phrase_should_not_produce_top_n \
  tests.test_time_contract_unittest.TimeContractTest.test_explicit_top_n_still_works_after_fix -v
```

Expected: all three PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/agent/app/services/intent_slot_service.py apps/agent/tests/test_time_contract_unittest.py
git commit -m "fix: exclude '前N天' from TOP_N_RE with negative lookahead"
```

---

## Task 2: Parse "N天前" and "N天前的前M天" in IntentSlotService

**Labels produced:**
- `"3天前"` → `time_range = "n_days_ago_3"`
- `"7天前的前7天"` → `time_range = "relative_before_7_at_7_ago"`

Both set `time_explicit = True`.

**Files:**
- Modify: `apps/agent/app/services/intent_slot_service.py`
- Test: `apps/agent/tests/test_time_contract_unittest.py`

- [ ] **Step 1: Write the failing tests**

Add to `TimeContractTest`:

```python
def test_n_days_ago_should_parse_to_label(self) -> None:
    """Verify '3天前的情况' sets time_range=n_days_ago_3 with time_explicit."""
    import asyncio

    async def run_case() -> None:
        service = IntentSlotService(repository=self.repository, qwen_client=None)
        result = await service.parse("3天前的情况", "n-days-ago")
        self.assertEqual(result.slots.get("time_range"), "n_days_ago_3")
        self.assertTrue(result.slots.get("time_explicit"))

    asyncio.run(run_case())

def test_relative_anchor_before_should_parse_to_label(self) -> None:
    """Verify '7天前的前7天' sets time_range=relative_before_7_at_7_ago with time_explicit."""
    import asyncio

    async def run_case() -> None:
        service = IntentSlotService(repository=self.repository, qwen_client=None)
        result = await service.parse("7天前的前7天的情况", "relative-anchor")
        self.assertEqual(result.slots.get("time_range"), "relative_before_7_at_7_ago")
        self.assertTrue(result.slots.get("time_explicit"))
        self.assertNotIn("top_n", result.slots)

    asyncio.run(run_case())
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
PYTHONPATH=.:tests python -m unittest \
  tests.test_time_contract_unittest.TimeContractTest.test_n_days_ago_should_parse_to_label \
  tests.test_time_contract_unittest.TimeContractTest.test_relative_anchor_before_should_parse_to_label -v
```

Expected: both FAIL.

- [ ] **Step 3: Add the two new regex constants**

In `apps/agent/app/services/intent_slot_service.py`, add after `ANCHOR_DAYS_RE` (line 25):

```python
RELATIVE_ANCHOR_DAYS_RE = re.compile(r"(\d{1,4})\s*天前\s*的\s*前\s*(\d{1,4})\s*天")
N_DAYS_AGO_RE = re.compile(r"(\d{1,4})\s*天前")
```

`RELATIVE_ANCHOR_DAYS_RE` must be defined before `N_DAYS_AGO_RE` so the constant is available at module level in the correct order.

- [ ] **Step 4: Update `_parse_time_range` to check both patterns before `ANCHOR_DAYS_RE`**

In `_parse_time_range`, insert as the **first two checks** (before the existing `anchor_match = ANCHOR_DAYS_RE.search(text)` line):

```python
def _parse_time_range(self, text: str) -> tuple[str | None, str | None]:
    """Map user time phrases to the finite time-window vocabulary."""
    # Relative-anchor patterns must be checked before ANCHOR_DAYS_RE and plain DATE_RE.
    relative_anchor_match = RELATIVE_ANCHOR_DAYS_RE.search(text)
    if relative_anchor_match:
        n_ago = int(relative_anchor_match.group(1))
        before_days = int(relative_anchor_match.group(2))
        return f"relative_before_{before_days}_at_{n_ago}_ago", relative_anchor_match.group(0)
    n_days_ago_match = N_DAYS_AGO_RE.search(text)
    if n_days_ago_match:
        n = int(n_days_ago_match.group(1))
        return f"n_days_ago_{n}", n_days_ago_match.group(0)
    # Anchored window must be checked before plain date …  (existing comment)
    anchor_match = ANCHOR_DAYS_RE.search(text)
    # … rest of method unchanged …
```

- [ ] **Step 5: Update `_has_explicit_time_expression` to recognise both patterns**

In `_has_explicit_time_expression`, extend the first `if` to include `N_DAYS_AGO_RE`:

```python
def _has_explicit_time_expression(self, text: str) -> bool:
    """Return whether text contains a user-facing time expression."""
    if DATE_RE.search(text) or LAST_N_DAYS_RE.search(text) or N_DAYS_AGO_RE.search(text):
        return True
    return any(
        token in text
        for token in [
            "今天", "昨天", "前天", "现在", "当前", "最新",
            "过去一个月", "近一个月", "最近一个月",
            "最近7天", "近7天", "上周", "最近", "今年以来",
            "过去两年", "近两年", "过去5年", "近5年", "近三年", "过去三年",
        ]
    )
```

`N_DAYS_AGO_RE` matches `\d+天前` which is a substring of both `"N天前"` and `"N天前的前M天"`, so one check covers both patterns.

- [ ] **Step 6: Run the new tests and the full suite**

```bash
PYTHONPATH=.:tests python -m unittest tests.test_time_contract_unittest -v
```

Expected: all tests PASS (original 16 + 2 new = 18, or more if Task 1 test was added first).

- [ ] **Step 7: Commit**

```bash
git add apps/agent/app/services/intent_slot_service.py apps/agent/tests/test_time_contract_unittest.py
git commit -m "feat: parse 'N天前' and 'N天前的前M天' relative-anchor time labels"
```

---

## Task 3: Resolve "n_days_ago_N" and "relative_before_M_at_N_ago" in TimeResolveService

Using `latest_business_time = "2026-04-13 23:59:17"` (from `SeedSoilRepository`):
- `n_days_ago_3` → `start=2026-04-10 00:00:00`, `end=2026-04-10 23:59:59`
- `relative_before_7_at_7_ago` → `start=2026-03-31 00:00:00`, `end=2026-04-06 23:59:59`

**Files:**
- Modify: `apps/agent/app/services/time_service.py`
- Test: `apps/agent/tests/test_time_contract_unittest.py`

- [ ] **Step 1: Write the failing tests**

Add to `TimeContractTest`:

```python
def test_n_days_ago_3_should_resolve_to_single_day(self) -> None:
    """Verify n_days_ago_3 resolves to the full day 3 days before latest_business_time."""
    result = self.time_service.resolve(
        slots={"time_range": "n_days_ago_3"},
        latest_business_time="2026-04-13 23:59:17",
    )
    self.assertEqual(result["start_time"], "2026-04-10 00:00:00")
    self.assertEqual(result["end_time"], "2026-04-10 23:59:59")
    self.assertEqual(result["resolved_time_range"], "n_days_ago_3")
    self.assertEqual(result["resolution_mode"], "relative_window")

def test_relative_before_7_at_7_ago_should_resolve_to_correct_window(self) -> None:
    """Verify relative_before_7_at_7_ago gives the 7-day window ending 7 days ago.

    Latest=Apr 13. Anchor=Apr 6 (7 days ago). 7-day window ending Apr 6:
    Mar 31 (day 1) … Apr 6 (day 7).
    """
    result = self.time_service.resolve(
        slots={"time_range": "relative_before_7_at_7_ago"},
        latest_business_time="2026-04-13 23:59:17",
    )
    self.assertEqual(result["start_time"], "2026-03-31 00:00:00")
    self.assertEqual(result["end_time"], "2026-04-06 23:59:59")
    self.assertEqual(result["resolved_time_range"], "relative_before_7_at_7_ago")
    self.assertEqual(result["resolution_mode"], "relative_window")
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
PYTHONPATH=.:tests python -m unittest \
  tests.test_time_contract_unittest.TimeContractTest.test_n_days_ago_3_should_resolve_to_single_day \
  tests.test_time_contract_unittest.TimeContractTest.test_relative_before_7_at_7_ago_should_resolve_to_correct_window -v
```

Expected: both FAIL.

- [ ] **Step 3: Add two module-level regex constants in time_service.py**

In `apps/agent/app/services/time_service.py`, add after `ANCHOR_AFTER_RE` (line 19):

```python
N_DAYS_AGO_LABEL_RE = re.compile(r"^n_days_ago_(\d+)$")
RELATIVE_BEFORE_AT_AGO_RE = re.compile(r"^relative_before_(\d+)_at_(\d+)_ago$")
```

- [ ] **Step 4: Add the two elif branches in `resolve()`**

In `apps/agent/app/services/time_service.py`, insert the two new branches **after** the existing `anchor_after` branch and **before** the existing `elif dynamic_days` branch:

```python
        elif (m := N_DAYS_AGO_LABEL_RE.match(resolved_time_range)) and latest_dt:
            n = int(m.group(1))
            payload.update(
                {
                    "resolution_mode": "relative_window",
                    "time_basis": "latest_business_time",
                    **self._offset_day_window(latest_dt, day_offset=n),
                }
            )
        elif (m := RELATIVE_BEFORE_AT_AGO_RE.match(resolved_time_range)) and latest_dt:
            before_days = int(m.group(1))
            n_ago = int(m.group(2))
            anchor = latest_dt - timedelta(days=n_ago)
            payload.update(
                {
                    "resolution_mode": "relative_window",
                    "time_basis": "latest_business_time",
                    **self._day_window(anchor, days=before_days),
                }
            )
        elif dynamic_days and latest_dt:
```

- [ ] **Step 5: Run the new tests and the full suite**

```bash
PYTHONPATH=.:tests python -m unittest tests.test_time_contract_unittest -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/agent/app/services/time_service.py apps/agent/tests/test_time_contract_unittest.py
git commit -m "feat: resolve n_days_ago_N and relative_before_M_at_N_ago in TimeResolveService"
```

---

## Task 4: Parse calendar-period labels (上个月, 本月, 本周, 过去N周)

**Labels produced:**
- `"上个月"` / `"上一个月"` → `time_range = "last_calendar_month"`
- `"本月"` → `time_range = "current_calendar_month"`
- `"本周"` → `time_range = "current_week"`
- `"过去3周"` / `"近3周"` → `time_range = "last_21_days"` (folds to existing label; no new resolver needed)

**Files:**
- Modify: `apps/agent/app/services/intent_slot_service.py`
- Test: `apps/agent/tests/test_time_contract_unittest.py`

- [ ] **Step 1: Write the failing tests**

Add to `TimeContractTest`:

```python
def test_last_calendar_month_should_parse_to_label(self) -> None:
    """Verify '上个月的墒情' produces time_range=last_calendar_month."""
    import asyncio

    async def run_case() -> None:
        service = IntentSlotService(repository=self.repository, qwen_client=None)
        result = await service.parse("上个月的墒情", "last-cal-month")
        self.assertEqual(result.slots.get("time_range"), "last_calendar_month")
        self.assertTrue(result.slots.get("time_explicit"))

    asyncio.run(run_case())

def test_current_calendar_month_should_parse_to_label(self) -> None:
    """Verify '本月的情况' produces time_range=current_calendar_month."""
    import asyncio

    async def run_case() -> None:
        service = IntentSlotService(repository=self.repository, qwen_client=None)
        result = await service.parse("本月的情况", "cur-cal-month")
        self.assertEqual(result.slots.get("time_range"), "current_calendar_month")
        self.assertTrue(result.slots.get("time_explicit"))

    asyncio.run(run_case())

def test_current_week_should_parse_to_label(self) -> None:
    """Verify '本周异常' produces time_range=current_week."""
    import asyncio

    async def run_case() -> None:
        service = IntentSlotService(repository=self.repository, qwen_client=None)
        result = await service.parse("本周异常", "cur-week")
        self.assertEqual(result.slots.get("time_range"), "current_week")
        self.assertTrue(result.slots.get("time_explicit"))

    asyncio.run(run_case())

def test_n_weeks_should_fold_to_days_label(self) -> None:
    """Verify '过去3周' folds to time_range=last_21_days."""
    import asyncio

    async def run_case() -> None:
        service = IntentSlotService(repository=self.repository, qwen_client=None)
        result = await service.parse("过去3周的墒情", "n-weeks")
        self.assertEqual(result.slots.get("time_range"), "last_21_days")
        self.assertTrue(result.slots.get("time_explicit"))

    asyncio.run(run_case())
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
PYTHONPATH=.:tests python -m unittest \
  tests.test_time_contract_unittest.TimeContractTest.test_last_calendar_month_should_parse_to_label \
  tests.test_time_contract_unittest.TimeContractTest.test_current_calendar_month_should_parse_to_label \
  tests.test_time_contract_unittest.TimeContractTest.test_current_week_should_parse_to_label \
  tests.test_time_contract_unittest.TimeContractTest.test_n_weeks_should_fold_to_days_label -v
```

Expected: all four FAIL.

- [ ] **Step 3: Add N_WEEKS_RE constant**

In `apps/agent/app/services/intent_slot_service.py`, add after `LAST_N_DAYS_RE` (around line 26):

```python
N_WEEKS_RE = re.compile(r"(?:过去|近)\s*(\d{1,3})\s*周")
```

- [ ] **Step 4: Update `_parse_time_range` — add calendar patterns after the existing "过去一个月" block**

In `_parse_time_range`, insert the new checks after the `"过去一个月"` block and before `LAST_N_DAYS_RE`:

```python
        if any(token in text for token in ["过去一个月", "近一个月", "最近一个月"]):
            raw_expr = next(token for token in ["过去一个月", "近一个月", "最近一个月"] if token in text)
            return "last_30_days", raw_expr
        if "上个月" in text or "上一个月" in text:
            return "last_calendar_month", "上个月" if "上个月" in text else "上一个月"
        if "本月" in text:
            return "current_calendar_month", "本月"
        if "本周" in text:
            return "current_week", "本周"
        day_match = LAST_N_DAYS_RE.search(text)
        if day_match:
            return f"last_{max(int(day_match.group(1)), 1)}_days", day_match.group(0)
        week_match = N_WEEKS_RE.search(text)
        if week_match:
            n_weeks = int(week_match.group(1))
            return f"last_{n_weeks * 7}_days", week_match.group(0)
        if "最近7天" in text or "近7天" in text:
            # … existing code continues unchanged …
```

- [ ] **Step 5: Update `_has_explicit_time_expression` to recognise calendar tokens and N_WEEKS_RE**

```python
def _has_explicit_time_expression(self, text: str) -> bool:
    """Return whether text contains a user-facing time expression."""
    if DATE_RE.search(text) or LAST_N_DAYS_RE.search(text) or N_DAYS_AGO_RE.search(text) or N_WEEKS_RE.search(text):
        return True
    return any(
        token in text
        for token in [
            "今天", "昨天", "前天", "现在", "当前", "最新",
            "过去一个月", "近一个月", "最近一个月",
            "上个月", "上一个月", "本月", "本周",
            "最近7天", "近7天", "上周", "最近", "今年以来",
            "过去两年", "近两年", "过去5年", "近5年", "近三年", "过去三年",
        ]
    )
```

- [ ] **Step 6: Run all tests**

```bash
PYTHONPATH=.:tests python -m unittest tests.test_time_contract_unittest -v
```

Expected: all tests PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/agent/app/services/intent_slot_service.py apps/agent/tests/test_time_contract_unittest.py
git commit -m "feat: parse 上个月/本月/本周/过去N周 calendar-period labels"
```

---

## Task 5: Resolve calendar-period labels in TimeResolveService

Using `latest_business_time = "2026-04-13 23:59:17"` (April 13, 2026 is a Monday):
- `last_calendar_month` → `start=2026-03-01 00:00:00`, `end=2026-03-31 23:59:59`
- `current_calendar_month` → `start=2026-04-01 00:00:00`, `end=2026-04-13 23:59:59`
- `current_week` → `start=2026-04-13 00:00:00`, `end=2026-04-13 23:59:59`

(`last_21_days` already works via the existing `dynamic_days` resolver — no new code needed for that label.)

**Files:**
- Modify: `apps/agent/app/services/time_service.py`
- Test: `apps/agent/tests/test_time_contract_unittest.py`

- [ ] **Step 1: Write the failing tests**

Add to `TimeContractTest`:

```python
def test_last_calendar_month_should_resolve_to_march_2026(self) -> None:
    """Verify last_calendar_month from April 2026 gives all of March 2026."""
    result = self.time_service.resolve(
        slots={"time_range": "last_calendar_month"},
        latest_business_time="2026-04-13 23:59:17",
    )
    self.assertEqual(result["start_time"], "2026-03-01 00:00:00")
    self.assertEqual(result["end_time"], "2026-03-31 23:59:59")
    self.assertEqual(result["resolved_time_range"], "last_calendar_month")
    self.assertEqual(result["resolution_mode"], "relative_window")

def test_current_calendar_month_should_resolve_to_april_2026(self) -> None:
    """Verify current_calendar_month from Apr 13 gives Apr 1 to Apr 13."""
    result = self.time_service.resolve(
        slots={"time_range": "current_calendar_month"},
        latest_business_time="2026-04-13 23:59:17",
    )
    self.assertEqual(result["start_time"], "2026-04-01 00:00:00")
    self.assertEqual(result["end_time"], "2026-04-13 23:59:59")
    self.assertEqual(result["resolved_time_range"], "current_calendar_month")
    self.assertEqual(result["resolution_mode"], "relative_window")

def test_current_week_should_resolve_to_monday_only(self) -> None:
    """Verify current_week from Monday Apr 13 gives Apr 13 only (Mon=day 1)."""
    result = self.time_service.resolve(
        slots={"time_range": "current_week"},
        latest_business_time="2026-04-13 23:59:17",
    )
    self.assertEqual(result["start_time"], "2026-04-13 00:00:00")
    self.assertEqual(result["end_time"], "2026-04-13 23:59:59")
    self.assertEqual(result["resolved_time_range"], "current_week")
    self.assertEqual(result["resolution_mode"], "relative_window")
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
PYTHONPATH=.:tests python -m unittest \
  tests.test_time_contract_unittest.TimeContractTest.test_last_calendar_month_should_resolve_to_march_2026 \
  tests.test_time_contract_unittest.TimeContractTest.test_current_calendar_month_should_resolve_to_april_2026 \
  tests.test_time_contract_unittest.TimeContractTest.test_current_week_should_resolve_to_monday_only -v
```

Expected: all three FAIL.

- [ ] **Step 3: Add three elif branches in `resolve()`**

In `apps/agent/app/services/time_service.py`, insert after the existing `elif resolved_time_range == "year_to_date"` block and before the existing `elif resolved_time_range in {"last_2_years", ...}` block:

```python
        elif resolved_time_range == "last_calendar_month" and latest_dt:
            first_of_this_month = latest_dt.replace(day=1)
            last_day_of_prev = first_of_this_month - timedelta(days=1)
            first_day_of_prev = last_day_of_prev.replace(day=1)
            payload.update(
                {
                    "resolution_mode": "relative_window",
                    "time_basis": "latest_business_time",
                    "start_time": self._format_datetime(self._start_of_day(first_day_of_prev)),
                    "end_time": self._format_datetime(self._end_of_day(last_day_of_prev)),
                }
            )
        elif resolved_time_range == "current_calendar_month" and latest_dt:
            first_day = latest_dt.replace(day=1)
            payload.update(
                {
                    "resolution_mode": "relative_window",
                    "time_basis": "latest_business_time",
                    "start_time": self._format_datetime(self._start_of_day(first_day)),
                    "end_time": self._format_datetime(self._end_of_day(latest_dt)),
                }
            )
        elif resolved_time_range == "current_week" and latest_dt:
            current_monday = latest_dt.date() - timedelta(days=latest_dt.weekday())
            payload.update(
                {
                    "resolution_mode": "relative_window",
                    "time_basis": "latest_business_time",
                    "start_time": self._format_datetime(datetime.combine(current_monday, time.min)),
                    "end_time": self._format_datetime(self._end_of_day(latest_dt)),
                }
            )
        elif resolved_time_range in {"last_2_years", "last_3_years", "last_5_years"} and latest_dt:
```

- [ ] **Step 4: Run the new tests and the full suite**

```bash
PYTHONPATH=.:tests python -m unittest tests.test_time_contract_unittest -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/agent/app/services/time_service.py apps/agent/tests/test_time_contract_unittest.py
git commit -m "feat: resolve last_calendar_month, current_calendar_month, current_week labels"
```

---

## Task 6: Parse and resolve "N月份" / "N月" (specific calendar month)

**Label produced:** `time_range = "calendar_month"`, new slot `target_month = "3"` (string `"1"`–`"12"`).

**Year inference in resolver:** if `target_month ≤ latest_dt.month` use `latest_dt.year`, else use `latest_dt.year - 1`.

Using `latest_business_time = "2026-04-13 23:59:17"` (April = month 4):
- `"3月份"` → month 3 ≤ 4 → year 2026 → `start=2026-03-01 00:00:00`, `end=2026-03-31 23:59:59`
- `"5月份"` → month 5 > 4 → year 2025 → `start=2025-05-01 00:00:00`, `end=2025-05-31 23:59:59`

**Files:**
- Modify: `apps/agent/app/services/intent_slot_service.py`
- Modify: `apps/agent/app/services/time_service.py`
- Test: `apps/agent/tests/test_time_contract_unittest.py`

- [ ] **Step 1: Write the failing tests**

Add to `TimeContractTest`:

```python
def test_calendar_month_march_should_parse_to_label_and_target_month(self) -> None:
    """Verify '3月份墒情' produces time_range=calendar_month and target_month='3'."""
    import asyncio

    async def run_case() -> None:
        service = IntentSlotService(repository=self.repository, qwen_client=None)
        result = await service.parse("3月份墒情", "cal-month-3")
        self.assertEqual(result.slots.get("time_range"), "calendar_month")
        self.assertEqual(result.slots.get("target_month"), "3")
        self.assertTrue(result.slots.get("time_explicit"))

    asyncio.run(run_case())

def test_calendar_month_march_should_resolve_to_march_2026(self) -> None:
    """Verify calendar_month target_month=3 from April 2026 gives all of March 2026."""
    result = self.time_service.resolve(
        slots={"time_range": "calendar_month", "target_month": "3"},
        latest_business_time="2026-04-13 23:59:17",
    )
    self.assertEqual(result["start_time"], "2026-03-01 00:00:00")
    self.assertEqual(result["end_time"], "2026-03-31 23:59:59")
    self.assertEqual(result["resolved_time_range"], "calendar_month")
    self.assertEqual(result["resolution_mode"], "relative_window")

def test_calendar_month_may_should_resolve_to_may_2025(self) -> None:
    """Verify calendar_month target_month=5 from April 2026 infers year 2025."""
    result = self.time_service.resolve(
        slots={"time_range": "calendar_month", "target_month": "5"},
        latest_business_time="2026-04-13 23:59:17",
    )
    self.assertEqual(result["start_time"], "2025-05-01 00:00:00")
    self.assertEqual(result["end_time"], "2025-05-31 23:59:59")
    self.assertEqual(result["resolved_time_range"], "calendar_month")
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
PYTHONPATH=.:tests python -m unittest \
  tests.test_time_contract_unittest.TimeContractTest.test_calendar_month_march_should_parse_to_label_and_target_month \
  tests.test_time_contract_unittest.TimeContractTest.test_calendar_month_march_should_resolve_to_march_2026 \
  tests.test_time_contract_unittest.TimeContractTest.test_calendar_month_may_should_resolve_to_may_2025 -v
```

Expected: all three FAIL.

- [ ] **Step 3: Add CALENDAR_MONTH_RE and target_month to SUPPORTED_SLOT_KEYS**

In `apps/agent/app/services/intent_slot_service.py`:

After `N_WEEKS_RE`, add:

```python
CALENDAR_MONTH_RE = re.compile(r"(?<!\d)(?<!年)(\d{1,2})\s*月份?(?!\d)")
```

Add `"target_month"` to `SUPPORTED_SLOT_KEYS`:

```python
SUPPORTED_SLOT_KEYS = {
    "aggregation",
    "audience",
    "batch_devices",
    "city",
    "county",
    "end_time",
    "follow_up",
    "metric",
    "need_template",
    "raw_time_expr",
    "render_mode",
    "sn",
    "start_time",
    "target_date",
    "target_month",
    "time_explicit",
    "time_range",
    "top_n",
    "_region_resolution_status",
}
```

- [ ] **Step 4: Update `_parse_time_range` — append the calendar-month check at the end**

In `_parse_time_range`, add as the **last pattern check** before the final `return None, None`:

```python
        cal_month_match = CALENDAR_MONTH_RE.search(text)
        if cal_month_match:
            month_str = cal_month_match.group(1)
            if 1 <= int(month_str) <= 12:
                return "calendar_month", cal_month_match.group(0)
        return None, None
```

Note: `_parse_time_range` only returns the `time_range` and `raw_time_expr`. The `target_month` slot must be set in `_parse_deterministic`. After the `if time_range:` block, add:

```python
        time_range, raw_time_expr = self._parse_time_range(semantic_text)
        if time_range:
            slots["time_range"] = time_range
            slots["time_explicit"] = True
            slots["raw_time_expr"] = raw_time_expr
            if time_range == "calendar_month":
                cal_m = CALENDAR_MONTH_RE.search(semantic_text)
                if cal_m:
                    slots["target_month"] = cal_m.group(1)
```

- [ ] **Step 5: Update `_has_explicit_time_expression` to check CALENDAR_MONTH_RE**

Extend the first `if` condition:

```python
    if (
        DATE_RE.search(text)
        or LAST_N_DAYS_RE.search(text)
        or N_DAYS_AGO_RE.search(text)
        or N_WEEKS_RE.search(text)
        or CALENDAR_MONTH_RE.search(text)
    ):
        return True
```

- [ ] **Step 6: Add the resolver branch in time_service.py — import `calendar` at top**

In `apps/agent/app/services/time_service.py`, add to the imports:

```python
import calendar as _calendar
```

(Using `_calendar` alias to avoid shadowing any local variable named `calendar`.)

Then add the elif branch in `resolve()` — insert after the `current_week` branch, before `last_2_years`:

```python
        elif resolved_time_range == "calendar_month" and slots.get("target_month") and latest_dt:
            month = int(slots["target_month"])
            if 1 <= month <= 12:
                year = latest_dt.year if month <= latest_dt.month else latest_dt.year - 1
                last_day_num = _calendar.monthrange(year, month)[1]
                first_day = datetime(year, month, 1)
                last_day = datetime(year, month, last_day_num)
                payload.update(
                    {
                        "resolution_mode": "relative_window",
                        "time_basis": "latest_business_time",
                        "start_time": self._format_datetime(self._start_of_day(first_day)),
                        "end_time": self._format_datetime(self._end_of_day(last_day)),
                    }
                )
```

- [ ] **Step 7: Run all tests**

```bash
PYTHONPATH=.:tests python -m unittest tests.test_time_contract_unittest -v
```

Expected: all tests PASS.

- [ ] **Step 8: Run the broader suite to catch regressions**

```bash
PYTHONPATH=.:tests python -m unittest discover -s tests -p "test_*.py" -v 2>&1 | tail -30
```

Expected: no new failures.

- [ ] **Step 9: Commit**

```bash
git add apps/agent/app/services/intent_slot_service.py apps/agent/app/services/time_service.py apps/agent/tests/test_time_contract_unittest.py
git commit -m "feat: parse and resolve 'N月份' specific calendar month with year inference"
```

---

## Task 7: Update time contract documentation

**Files:**
- Modify: `apps/agent/plans/1/1.plan.md`

- [ ] **Step 1: Update `### 输入语义`**

In `apps/agent/plans/1/1.plan.md`, replace the `### 输入语义` list (currently ending at `YYYY-MM-DD之前N天` and `YYYY-MM-DD之后N天`) with:

```markdown
### 输入语义

- `今天` / `昨天` / `前天`
- `N天前`（N 天前的完整一天）
- `N天前的前M天`（以 N 天前为锚点，向前 M 天的完整窗口）
- `最近N天` / `近N天` / `过去N天`
- `过去N周` / `近N周`（折算为 N×7 天）
- `最近一个月`（滚动 30 天）
- `上周`（上一个完整自然周 Mon–Sun）
- `本周`（本周一至最新业务时间）
- `上个月`（上一个完整自然月）
- `本月`（本月一日至最新业务时间）
- `N月份` / `N月`（指定月；年份自动推断：月份 ≤ 当前月取今年，否则取去年）
- `YYYY-MM-DD`
- `YYYY-MM-DD之前N天`（N 天窗口，以指定日期为结束边界，含当天）
- `YYYY-MM-DD之后N天`（N 天窗口，以指定日期为起始边界，含当天）
- `今年以来`
- `过去2/3/5年`
```

Also add to `### 解析结果` notes:

```markdown
- 相对锚窗口（`n_days_ago_N` / `relative_before_M_at_N_ago`）和日历周期标签均依赖最新业务时间，
  `resolution_mode` 输出为 `relative_window`
- `calendar_month` 标签需额外的 `target_month` slot（字符串 `"1"`–`"12"`）
```

- [ ] **Step 2: Commit**

```bash
git add apps/agent/plans/1/1.plan.md
git commit -m "docs: update time contract with full input expression coverage"
```

---

## Self-Review

**Spec coverage:**
- TOP_N_RE false positive on "前N天" → Task 1 ✓
- Parse "N天前" → Task 2 ✓
- Parse "N天前的前M天" → Task 2 ✓
- Resolve both → Task 3 ✓
- Parse 上个月/本月/本周/过去N周 → Task 4 ✓
- Resolve 上个月/本月/本周 → Task 5 ✓ (`过去N周` folds to existing `last_N_days` — no new resolver)
- Parse N月份 → Task 6 ✓
- Resolve N月份 with year inference → Task 6 ✓
- Documentation → Task 7 ✓

**Placeholder scan:** none found.

**Type consistency:**
- Label `"n_days_ago_3"` produced by `N_DAYS_AGO_RE` in Task 2 matched by `N_DAYS_AGO_LABEL_RE` in Task 3 ✓
- Label `"relative_before_7_at_7_ago"` produced by `RELATIVE_ANCHOR_DAYS_RE` in Task 2 matched by `RELATIVE_BEFORE_AT_AGO_RE` in Task 3 ✓
- Labels `"last_calendar_month"`, `"current_calendar_month"`, `"current_week"` produced in Task 4 matched as string literals in Task 5 ✓
- Label `"calendar_month"` + slot `"target_month"` produced in Task 6 (parse) consumed in Task 6 (resolve) ✓
- `"target_month"` added to `SUPPORTED_SLOT_KEYS` in Task 6 so it survives LLM-path `_sanitize_slots` ✓
