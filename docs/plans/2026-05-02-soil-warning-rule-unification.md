# Soil Warning Rule Unification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Unify all warning-related soil answers around one rule-evaluated data set, so answers, SQL evidence, and follow-up behavior all agree.

**Architecture:** Keep the current deterministic soil answer pipeline, but make `warning_only` an explicit first-class truth that flows through summary/count/list/group, log evidence, and response text. The service should still read raw soil facts first, but every warning-facing answer must expose the active rule summary, the filtered result set, and the same row set in both answer and audit text. No compatibility work is needed.

**Tech Stack:** Python services, existing MySQL repositories, pytest/unittest, Markdown docs.

---

### Task 1: Lock the warning-rule truth into tests first

**Files:**
- Modify: `apps/agent/tests/test_query_profile_governance_unittest.py`
- Modify: `apps/agent/tests/test_data_answer_service_unittest.py`

**Step 1: Add failing assertions for warning-focused answers**

- `recent 30 days have focus regions` must mention analysis language, not just totals.
- warning count zero must clearly say it is zero under the active warning rule.
- warning ranking / group answers must expose the leading county or top counties, not only "N groups".
- warning query logs should expose the warning-rule summary in evidence text or digest.

**Step 2: Run the targeted tests and confirm they fail**

Run:
```bash
pytest apps/agent/tests/test_query_profile_governance_unittest.py -k warning -v
pytest apps/agent/tests/test_data_answer_service_unittest.py -k warning -v
```

Expected: current text/evidence assertions fail on the warning-focused cases.

### Task 2: Add one shared warning-rule summary helper and reuse it

**Files:**
- Modify: `apps/agent/app/services/data_answer_service.py`
- Modify: `apps/agent/app/repositories/soil_repository.py` only if a small audit-string helper is needed

**Step 1: Add a helper that renders the active warning rule in human-readable form**

- Parse `metric_rule.rule_definition_json`.
- Render a short stable sentence such as:
  - `当前预警规则：water20cm < 50 为重旱，water20cm >= 150 为涝渍，water20cm = 0 且 t20cm = 0 为设备故障。`
- Reuse it across summary/count/group/list warning answers and query logs.

**Step 2: Add an audit-text helper for warning queries**

- Keep the existing raw fact SQL.
- Append a short warning-rule note so the admin evidence shows both:
  - the raw fact query
  - the rule used to interpret the returned rows

**Step 3: Keep the same filtering source**

- Do not change the actual warning predicate evaluation path yet.
- Continue filtering with the shared `WarningPredicateService`.
- The change is about making the rule truth visible and stable everywhere.

### Task 3: Reword warning-facing answers so they analyze, not just count

**Files:**
- Modify: `apps/agent/app/services/data_answer_service.py`

**Step 1: Update warning summary text**

- For `warning_only` summary:
  - say `按当前预警规则筛选后`
  - include `record_count / device_count / region_count`
  - include a preview of the leading focus regions
  - avoid a bare statistics-only answer

**Step 2: Update warning count text**

- For warning counts:
  - say the result is after warning-rule filtering
  - keep the zero-case explicit and reassuring

**Step 3: Update warning group / ranking text**

- For `最近30天哪个县最需要关注` and `最近30天预警最多的前5个县是哪些`:
  - expose the top county / top counties
  - include `alert_device_count`, `alert_record_count`, and latest warning time when available
  - stop returning only `共 N 组`

**Step 4: Carry the warning-rule summary into log entries**

- Add the warning-rule brief to `executed_result_json`, `result_digest_json`, or the query-plan summary so evidence is readable.

### Task 4: Reclassify the 60-case analysis docs

**Files:**
- Modify: `testdata/agent/soil-moisture/real-conversations/analysis-60.md`
- Modify: `testdata/agent/soil-moisture/real-conversations/cases/real-60-case-library.md` if needed

**Step 1: Remove case 54 from the failure list**

- It is a new-topic-after-closing case, not a warning-rule bug.

**Step 2: Mark the manually confirmed warning cases as the same root cause**

- Group `6 / 24 / 31 / 33 / 34 / 53` under warning-rule unification and answer-shape mismatch.

**Step 3: Leave unmentioned manual-review items as pass**

- If the user did not call them out, do not turn them into new work.

### Task 5: Verify the unified behavior end to end

**Files:**
- No new files; verify the modified ones

**Step 1: Run the focused unit tests**

Run:
```bash
pytest apps/agent/tests/test_query_profile_governance_unittest.py -v
pytest apps/agent/tests/test_data_answer_service_unittest.py -v
```

**Step 2: Spot-check the 60-case analysis outputs**

- Confirm the updated wording for the warning-focused cases.
- Confirm `54` is no longer treated as a failure.

**Step 3: Commit the result**

```bash
git add apps/agent/app/services/data_answer_service.py apps/agent/tests/test_query_profile_governance_unittest.py apps/agent/tests/test_data_answer_service_unittest.py testdata/agent/soil-moisture/real-conversations/analysis-60.md testdata/agent/soil-moisture/real-conversations/cases/real-60-case-library.md docs/plans/2026-05-02-soil-warning-rule-unification.md
git commit -m "fix: unify warning-rule soil answers"
```
