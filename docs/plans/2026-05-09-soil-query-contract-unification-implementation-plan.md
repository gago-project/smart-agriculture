# Soil Query Contract Unification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Introduce one shared interpretation contract for soil chat turns so context, routing, query semantics, and rendered labels all use the same truth.

**Architecture:** Keep the deterministic chat pipeline and existing repositories, but insert a new `TurnInterpretation` layer between raw input parsing and capability execution. Refactor route selection, query profile generation, and output labels to consume that object instead of independently re-parsing the original message. Task 2 establishes upstream ownership of business semantics; Tasks 3-4 finish removing any remaining downstream raw-text branching.

**Tech Stack:** Python services, unittest/pytest, existing soil repositories, Markdown chat answers.

---

### Task 1: Lock the contract drift into failing tests

**Files:**
- Modify: `apps/agent/tests/test_follow_up_intent_resolver_service_unittest.py`
- Modify: `apps/agent/tests/test_turn_route_decision_service_unittest.py`
- Modify: `apps/agent/tests/test_query_profile_governance_unittest.py`
- Modify: `apps/agent/tests/test_data_answer_service_unittest.py`

**Step 1: Write the failing tests**

Add focused tests that describe the target contract:

- closed conversation + contextual phrase returns blocked guidance
- closed conversation + explicit full restart returns standalone
- generic compare after warning compare does not inherit warning metric
- short region follow-up like `那徐州市呢` keeps inherited time and follow-up mode
- subset/filter follow-up like `这些地区里只看睢宁县` stays `subset`, not `standalone`
- output text must say `墒情记录` or `预警记录`, never ambiguous `记录`

**Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/mac/Desktop/gago-cloud/code/smart-agriculture/apps/agent
PYTHONPATH=. python -m pytest tests/test_follow_up_intent_resolver_service_unittest.py -v
PYTHONPATH=. python -m pytest tests/test_turn_route_decision_service_unittest.py -v
PYTHONPATH=. python -m pytest tests/test_query_profile_governance_unittest.py -v
PYTHONPATH=. python -m pytest tests/test_data_answer_service_unittest.py -k "closed_context or compare or warning_only or follow_up_mode" -v
```

Expected: one or more tests fail because the current code still resolves the same concept in multiple places.

**Step 3: Write minimal implementation**

Do not change output text or routing yet beyond what is necessary to support the new test seams.

**Step 4: Run test to verify it passes**

Run the same commands and confirm the new contract tests are green.

**Step 5: Commit**

```bash
git add apps/agent/tests/test_follow_up_intent_resolver_service_unittest.py apps/agent/tests/test_turn_route_decision_service_unittest.py apps/agent/tests/test_query_profile_governance_unittest.py apps/agent/tests/test_data_answer_service_unittest.py docs/plans/2026-05-09-soil-query-contract-unification-design.md docs/plans/2026-05-09-soil-query-contract-unification-implementation-plan.md
git commit -m "test: lock soil query contract behavior"
```

### Task 2: Introduce the shared `TurnInterpretation` layer

**Files:**
- Create: `apps/agent/app/services/turn_interpretation_service.py`
- Modify: `apps/agent/app/services/data_answer_service.py`
- Modify: `apps/agent/app/services/follow_up_intent_resolver_service.py`
- Modify: `apps/agent/app/services/follow_up_action_resolver_service.py`
- Test: `apps/agent/tests/test_follow_up_intent_resolver_service_unittest.py`
- Test: `apps/agent/tests/test_data_answer_service_unittest.py`

**Step 1: Write the failing test**

Add tests for a new interpretation object or helper method that exposes:

- `conversation_state`
- `follow_up_mode`
- `subject_family`
- `answer_intent`
- `data_focus`
- `compare_mode`
- `measure`
- `blocked_reason`

Example:

```python
result = service.resolve(...)
assert result.conversation_state == "closed"
assert result.follow_up_mode == "blocked"
assert result.blocked_reason == "closed_context"
```

Also add a subset-focused case:

```python
result = service.resolve(...)
assert result.follow_up_mode == "subset"
assert result.answer_intent == "group"
```

**Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/mac/Desktop/gago-cloud/code/smart-agriculture/apps/agent
PYTHONPATH=. python -m pytest tests/test_follow_up_intent_resolver_service_unittest.py -k "closed_context or subset" -v
PYTHONPATH=. python -m pytest tests/test_data_answer_service_unittest.py -k "closed_context or subset" -v
```

Expected: one or more failures because `TurnInterpretation` does not exist yet and the new subset/closed-context contract is not fully wired.

**Step 3: Write minimal implementation**

Implement:

- `TurnInterpretation` dataclass
- `TurnInterpretationService.resolve(...)`
- integration at the top of `DataAnswerService._reply_impl`

Minimal expected skeleton:

```python
@dataclass(frozen=True)
class TurnInterpretation:
    normalized_text: str
    conversation_state: str
    follow_up_mode: str  # standalone / inherit / replace_slot / correct_slot / subset / action_expand / blocked
    subject_family: str
    answer_intent: str
    entities: dict[str, Any]
    time_window: dict[str, Any]
    data_focus: str
    compare_mode: str | None = None
    measure: str | None = None
    warning_type: str | None = None
    status_focus: str | None = None
    list_target: str | None = None
    group_by: str | None = None
    blocked_reason: str | None = None
```

Add an explicit acceptance rule in this task:

- all newly introduced business semantics must be surfaced from `TurnInterpretationService`
- temporary downstream compatibility branches may remain during Tasks 2-3
- by the end of Tasks 3-4, downstream business-semantic branching on raw text must be removed

**Step 4: Run test to verify it passes**

Run the targeted closed-context and follow-up tests again.

**Step 5: Commit**

```bash
git add apps/agent/app/services/turn_interpretation_service.py apps/agent/app/services/data_answer_service.py apps/agent/app/services/follow_up_intent_resolver_service.py apps/agent/app/services/follow_up_action_resolver_service.py apps/agent/tests/test_follow_up_intent_resolver_service_unittest.py apps/agent/tests/test_data_answer_service_unittest.py
git commit -m "refactor: add turn interpretation layer"
```

### Task 3: Make route selection consume interpretation instead of raw re-parsing

**Files:**
- Modify: `apps/agent/app/services/turn_route_decision_service.py`
- Modify: `apps/agent/app/services/data_answer_service.py`
- Test: `apps/agent/tests/test_turn_route_decision_service_unittest.py`
- Test: `apps/agent/tests/test_turn_route_query_shape_matrix_unittest.py`

**Step 1: Write the failing test**

Add tests showing route selection only maps the interpretation:

- blocked interpretation returns guidance route
- `subject_family=device_registry + answer_intent=distribution` returns `device_registry_distribution`
- `subject_family=warning + answer_intent=group` returns `warning_group`

**Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/mac/Desktop/gago-cloud/code/smart-agriculture/apps/agent
PYTHONPATH=. python -m pytest tests/test_turn_route_decision_service_unittest.py -v
PYTHONPATH=. python -m pytest tests/test_turn_route_query_shape_matrix_unittest.py -v
```

Expected: failures because the current route service still depends on raw text heuristics.

**Step 3: Write minimal implementation**

Refactor the route service so it accepts a prepared interpretation object and reduces to capability mapping. Keep text-normalization helpers only where still needed to build the interpretation upstream.

Required guardrail:

- remove business-semantic branching on raw `message` from `TurnRouteDecisionService`
- if route needs extra meaning, add it to `TurnInterpretation` upstream instead of re-parsing text here

**Step 4: Run test to verify it passes**

Re-run the route suites and confirm green.

**Step 5: Commit**

```bash
git add apps/agent/app/services/turn_route_decision_service.py apps/agent/app/services/data_answer_service.py apps/agent/tests/test_turn_route_decision_service_unittest.py apps/agent/tests/test_turn_route_query_shape_matrix_unittest.py
git commit -m "refactor: route from turn interpretation"
```

### Task 4: Make query-profile generation pure and stop semantic drift

**Files:**
- Modify: `apps/agent/app/services/query_profile_resolver_service.py`
- Modify: `apps/agent/app/services/data_answer_service.py`
- Test: `apps/agent/tests/test_query_profile_governance_unittest.py`
- Test: `apps/agent/tests/test_data_answer_service_unittest.py`

**Step 1: Write the failing test**

Add tests for:

- `warning_only` comes from interpretation, not inherited text guesses
- `requested_measure` and `execution_measure` are distinct
- generic compare after warning compare leaves `requested_measure is None`
- warning disposal inherits only `status_focus` when interpretation says follow-up
- resolver output is identical whether the original text is available or not, as long as interpretation is the same

**Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/mac/Desktop/gago-cloud/code/smart-agriculture/apps/agent
PYTHONPATH=. python -m pytest tests/test_query_profile_governance_unittest.py -v
PYTHONPATH=. python -m pytest tests/test_data_answer_service_unittest.py -k "compare or warning_only or status_focus" -v
```

Expected: failures because the resolver still infers semantics from raw text.

**Step 3: Write minimal implementation**

Change the resolver signature to consume interpretation-derived fields directly. Reduce it to structural mapping:

```python
QueryProfile(
    data_focus=interpretation.data_focus,
    measure=interpretation.measure,
    compare_mode=interpretation.compare_mode,
    warning_type=interpretation.warning_type,
    status_focus=interpretation.status_focus,
)
```

Required guardrail:

- `QueryProfileResolverService` must not use raw `message` text for business-semantic branching after this task
- any fallback default should be structural and interpretation-based, not text-heuristic-based

**Step 4: Run test to verify it passes**

Re-run the governance and focused data-answer tests.

**Step 5: Commit**

```bash
git add apps/agent/app/services/query_profile_resolver_service.py apps/agent/app/services/data_answer_service.py apps/agent/tests/test_query_profile_governance_unittest.py apps/agent/tests/test_data_answer_service_unittest.py
git commit -m "refactor: derive query profile from interpretation"
```

### Task 5: Introduce one canonical metric registry and align rendering

**Files:**
- Modify: `apps/agent/app/services/data_answer_service.py`
- Modify: `apps/agent/app/services/fact_check_service.py`
- Test: `apps/agent/tests/test_data_answer_service_unittest.py`

**Step 1: Write the failing test**

Add focused tests for:

- summary text uses `墒情记录`
- warning answers use `预警记录`
- compare answers expose both `墒情记录` and `预警记录` where appropriate
- no rendered answer uses bare `记录：`

**Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/mac/Desktop/gago-cloud/code/smart-agriculture/apps/agent
PYTHONPATH=. python -m pytest tests/test_data_answer_service_unittest.py -k "record label or compare or warning" -v
```

Expected: one or more failures because labels are still route-local.

**Step 3: Write minimal implementation**

Add a shared registry:

```python
METRIC_LABELS = {
    "soil_record_count": "墒情记录",
    "warning_record_count": "预警记录",
    "soil_device_count": "墒情仪",
    "warning_device_count": "预警墒情仪",
    "region_count": "地区",
}
```

Refactor render helpers to emit labels from this registry and update `FactCheckService` to understand the same metric names.

**Step 4: Run test to verify it passes**

Re-run the focused text tests.

**Step 5: Commit**

```bash
git add apps/agent/app/services/data_answer_service.py apps/agent/app/services/fact_check_service.py apps/agent/tests/test_data_answer_service_unittest.py
git commit -m "refactor: unify soil answer metric labels"
```

### Task 6: Add repository-backed contract verification

**Files:**
- Modify: `apps/agent/tests/test_data_answer_service_unittest.py`
- Modify: `apps/agent/tests/support_repositories.py`
- Modify: `apps/agent/app/services/fact_check_service.py`

**Step 1: Write the failing test**

Add tests that compare service output against repository-backed contract truth, not just rendered text:

- summary answer `soil_record_count` equals repository aggregate
- warning-focused answer `warning_record_count` equals repository aggregate
- compare answer exposes `requested_measure` and `execution_measure` consistently with repository-backed executed rows
- region preview answers mark themselves as `前N个` and do not imply preview sums equal global totals

Example:

```python
reply = await service.reply(...)
executed = reply["blocks"][0]["executed_result"]
assert executed["rows"][0]["warning_record_count"] == 39
assert "前3个" in reply["final_text"]
```

**Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/mac/Desktop/gago-cloud/code/smart-agriculture/apps/agent
PYTHONPATH=. python -m pytest tests/test_data_answer_service_unittest.py -k "truth or preview or warning_record_count" -v
```

Expected: one or more failures because current verification still focuses on rendered text and not repository-backed contract truth.

**Step 3: Write minimal implementation**

Expose or normalize the executed-result contract so tests and fact-check can validate:

- `soil_record_count`
- `warning_record_count`
- `soil_device_count` / `warning_device_count`
- `requested_measure`
- `execution_measure`

Do not scrape numbers back out of rendered text for this verification.

**Step 4: Run test to verify it passes**

Re-run the focused truth-contract tests and confirm green.

**Step 5: Commit**

```bash
git add apps/agent/tests/test_data_answer_service_unittest.py apps/agent/tests/support_repositories.py apps/agent/app/services/fact_check_service.py
git commit -m "test: add repository-backed soil answer truth checks"
```

### Task 7: Add live-data soil-only truth verification

**Files:**
- Create: `apps/agent/tests/test_soil_truth_live_integration_unittest.py`
- Modify: `apps/agent/tests/test_data_answer_service_unittest.py`
- Reference: `apps/agent/.env.example`

**Step 1: Write the failing test**

Add env-backed integration tests that connect to the current local MySQL dataset and verify:

- canonical soil summary / warning summary replies match live repository aggregates
- soil warning answers do not mix in non-soil warning sources
- soil warning answers do not read `warning_disposal_record`
- disposal answers still use the disposal source when the capability is `warning_disposal`

Example:

```python
reply = await service.reply(...)
audit_sql = reply["query_log_entries"][0]["executed_sql_text"]
assert "warning_disposal_record" not in audit_sql
assert reply["blocks"][0]["executed_result"]["warning_record_count"] == live_stats["warning_record_count"]
```

**Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/mac/Desktop/gago-cloud/code/smart-agriculture/apps/agent
set -a
source .env
set +a
PYTHONPATH=. python -m pytest tests/test_soil_truth_live_integration_unittest.py -v
```

Expected: FAIL or expose missing live-truth wiring until the service/result contract can be checked against the real local MySQL dataset.

**Step 3: Write minimal implementation**

Expose enough structured evidence for live-data verification:

- canonical `executed_result` metrics
- executed SQL or equivalent repository audit metadata
- explicit separation between soil-warning and warning-disposal source paths

Important:

- this task is not allowed to silently skip when `MYSQL_*` is missing in the intended dev environment
- if the local DB is unavailable, stop and fix the environment before claiming 100% data correctness

**Step 4: Run test to verify it passes**

Re-run the live integration suite and confirm the local real-data checks are green.

**Step 5: Commit**

```bash
git add apps/agent/tests/test_soil_truth_live_integration_unittest.py apps/agent/tests/test_data_answer_service_unittest.py
git commit -m "test: add live soil truth integration verification"
```

### Task 8: Verify end to end on local chat and core suites

**Files:**
- No new files required unless a small doc note is needed

**Step 1: Run the focused agent suites**

Run:

```bash
cd /Users/mac/Desktop/gago-cloud/code/smart-agriculture/apps/agent
PYTHONPATH=. python -m pytest tests/test_follow_up_intent_resolver_service_unittest.py -v
PYTHONPATH=. python -m pytest tests/test_turn_route_decision_service_unittest.py -v
PYTHONPATH=. python -m pytest tests/test_turn_route_query_shape_matrix_unittest.py -v
PYTHONPATH=. python -m pytest tests/test_query_profile_governance_unittest.py -v
PYTHONPATH=. python -m pytest tests/test_data_answer_service_unittest.py -v
set -a
source .env
set +a
PYTHONPATH=. python -m pytest tests/test_soil_truth_live_integration_unittest.py -v
```

Expected: PASS.

**Step 2: Run local real-chat smoke**

Keep the local agent and web running, then verify in chat:

1. `最近30天全省预警处置情况怎么样`
2. `行，先这样吧`
3. `那设备分布呢`
4. `江苏设备分布呢`
5. `最近30天有没有需要重点关注的地区`
6. `这些地区里只看睢宁县`
7. `徐州和南通最近30天哪个预警点位更多`
8. `徐州和南通最近30天对比一下`
9. `那更差那边有多少条预警记录`

Expected:

- step 3 is blocked with restart guidance
- step 4 is treated as explicit restart
- step 6 stays in subset/filter mode instead of becoming standalone
- compare text distinguishes `墒情记录` and `预警记录`
- winner follow-up stays in the correct metric scope
- warning preview text clearly states `前N个` and does not imply preview sums equal global totals

**Step 3: Commit**

```bash
git add apps/agent/app/services apps/agent/tests docs/plans/2026-05-09-soil-query-contract-unification-design.md docs/plans/2026-05-09-soil-query-contract-unification-implementation-plan.md
git commit -m "refactor: unify soil query interpretation contract"
```
