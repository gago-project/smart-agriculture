# Business Answer Template Standardization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Unify business-template answer text across device registry, warning, and template-output routes with one shared Markdown structure.

**Architecture:** Keep the existing deterministic routing and block payloads, but centralize `final_text` rendering into a few reusable helpers inside `data_answer_service.py`. Update focused tests to lock the new structure and prevent future drift.

**Tech Stack:** Python, unittest, Next.js chat renderer, Markdown final text

---

### Task 1: Lock the new text shape with focused tests

**Files:**
- Modify: `apps/agent/tests/test_data_answer_service_unittest.py`

**Step 1: Write the failing test**

Add focused assertions for:

- `device_registry_distribution` uses Markdown bullet lines
- `warning_group` uses Markdown bullet lines and explicit rule anchor
- `warning_disposal` uses Markdown bullet lines in fixed status order

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=apps/agent:apps/agent/tests .venv/bin/python -m unittest apps.agent.tests.test_data_answer_service_unittest.DataAnswerServiceTest.test_device_registry_distribution_returns_city_breakdown apps.agent.tests.test_data_answer_service_unittest.DataAnswerServiceTest.test_warning_group_returns_group_table_and_standardized_text apps.agent.tests.test_data_answer_service_unittest.DataAnswerServiceTest.test_warning_group_follow_up_can_switch_to_warning_disposal_and_status_focus -v`

Expected: one or more assertions fail because the current `final_text` still uses mixed formatting.

**Step 3: Write minimal implementation**

Implement shared text helpers and update the targeted reply branches.

**Step 4: Run test to verify it passes**

Run the same unittest command and confirm all targeted cases pass.

**Step 5: Commit**

```bash
git add apps/agent/tests/test_data_answer_service_unittest.py apps/agent/app/services/data_answer_service.py docs/plans/2026-05-08-business-answer-template-standardization-design.md docs/plans/2026-05-08-business-answer-template-standardization-implementation-plan.md
git commit -m "refactor: standardize business answer templates"
```

### Task 2: Refactor device registry answer text

**Files:**
- Modify: `apps/agent/app/services/data_answer_service.py`
- Test: `apps/agent/tests/test_data_answer_service_unittest.py`

**Step 1: Write the failing test**

Extend assertions to require:

- device total stays single-line with fixed prefix
- province distribution and city county distribution use bullet lines
- wording remains aligned with acceptance language

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=apps/agent:apps/agent/tests .venv/bin/python -m unittest apps.agent.tests.test_data_answer_service_unittest.DataAnswerServiceTest.test_device_registry_count_returns_correct_answer apps.agent.tests.test_data_answer_service_unittest.DataAnswerServiceTest.test_device_registry_distribution_returns_city_breakdown apps.agent.tests.test_data_answer_service_unittest.DataAnswerServiceTest.test_device_registry_county_detail_returns_county_breakdown -v`

Expected: failures on new format assertions.

**Step 3: Write minimal implementation**

Route device registry text through shared helper methods.

**Step 4: Run test to verify it passes**

Run the same tests and confirm green.

**Step 5: Commit**

```bash
git add apps/agent/app/services/data_answer_service.py apps/agent/tests/test_data_answer_service_unittest.py
git commit -m "refactor: unify device registry answer text"
```

### Task 3: Refactor warning and disposal answer text

**Files:**
- Modify: `apps/agent/app/services/data_answer_service.py`
- Test: `apps/agent/tests/test_data_answer_service_unittest.py`

**Step 1: Write the failing test**

Add assertions for:

- warning count includes “满足当前预警规则”
- warning group uses bullet lines and rule anchor
- warning disposal uses fixed four-status bullet list

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=apps/agent:apps/agent/tests .venv/bin/python -m unittest apps.agent.tests.test_data_answer_service_unittest.DataAnswerServiceTest.test_warning_group_returns_standardized_region_distribution_text apps.agent.tests.test_data_answer_service_unittest.DataAnswerServiceTest.test_warning_count_type_filter_returns_matching_totals apps.agent.tests.test_data_answer_service_unittest.DataAnswerServiceTest.test_warning_group_follow_up_can_switch_to_warning_disposal_and_status_focus -v`

Expected: failures on text-shape assertions before implementation.

**Step 3: Write minimal implementation**

Apply the shared warning/disposal text helpers.

**Step 4: Run test to verify it passes**

Run the same tests and confirm green.

**Step 5: Commit**

```bash
git add apps/agent/app/services/data_answer_service.py apps/agent/tests/test_data_answer_service_unittest.py
git commit -m "refactor: unify warning and disposal answer text"
```

### Task 4: Verify broader regression

**Files:**
- Modify if needed: `testdata/agent/soil-moisture/formal-acceptance-library.md`
- Modify if needed: `testdata/agent/soil-moisture/real-conversations/cases/real-conversation-library.md`

**Step 1: Run the focused agent suite**

Run: `PYTHONPATH=apps/agent:apps/agent/tests .venv/bin/python -m unittest apps.agent.tests.test_data_answer_service_unittest -v`

Expected: PASS

**Step 2: Run web contract verification if text/block shape touched renderer expectations**

Run: `npm test -- --runInBand apps/web/tests/file-contract.test.mjs`

Expected: PASS

**Step 3: Sync docs only if examples became stale**

Update the acceptance or real-conversation libraries if a stored “当前回答” example no longer reflects the new standard style.

**Step 4: Commit**

```bash
git add apps/agent/app/services/data_answer_service.py apps/agent/tests/test_data_answer_service_unittest.py testdata/agent/soil-moisture/formal-acceptance-library.md testdata/agent/soil-moisture/real-conversations/cases/real-conversation-library.md
git commit -m "test: sync business answer template expectations"
```
