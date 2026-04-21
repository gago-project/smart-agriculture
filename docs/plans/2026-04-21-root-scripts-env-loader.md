# Root Scripts Env Loader Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the root `package.json` local development scripts load the repository root `.env` consistently without changing their current runtime semantics.

**Architecture:** Reuse the existing `scripts/dev/load-root-env.sh` helper instead of introducing a second env-loading path. Keep the root npm scripts functionally the same, and exclude `AGENT_PORT` from the agent scripts so `dev:agent` and `start:agent` still default to port `18010` unless the caller explicitly overrides it.

**Tech Stack:** npm scripts, Bash, Node.js built-in test runner

---

### Task 1: Lock the root script contract with a failing test

**Files:**
- Modify: `apps/web/tests/local-dev-env-loader.test.mjs`
- Test: `apps/web/tests/local-dev-env-loader.test.mjs`

**Step 1: Write the failing test**

Add a test that reads the root `package.json` and asserts:
- `dev:web` loads `scripts/dev/load-root-env.sh`
- `dev:agent` loads `scripts/dev/load-root-env.sh`
- `start:web` loads `scripts/dev/load-root-env.sh`
- `start:agent` loads `scripts/dev/load-root-env.sh`
- agent scripts exclude `AGENT_PORT`

**Step 2: Run test to verify it fails**

Run: `npm --prefix apps/web test -- local-dev-env-loader.test.mjs`
Expected: FAIL because the current root scripts do not reference `load-root-env.sh`

**Step 3: Write minimal implementation**

No implementation in this task.

**Step 4: Run test to verify failure is correct**

Run the same command again if needed.
Expected: still FAIL for missing loader references, not for unrelated errors.

### Task 2: Update root npm scripts to use the shared env loader

**Files:**
- Modify: `package.json`
- Reference: `scripts/dev/load-root-env.sh`

**Step 1: Write minimal implementation**

Update these root scripts only:
- `dev:web`
- `dev:agent`
- `start:web`
- `start:agent`

Implementation rules:
- invoke `bash -lc`
- source `scripts/dev/load-root-env.sh`
- preserve the existing command body
- exclude `AGENT_PORT` from agent scripts so the current default port behavior remains stable

**Step 2: Run the focused test**

Run: `npm --prefix apps/web test -- local-dev-env-loader.test.mjs`
Expected: PASS

### Task 3: Run broader regression checks

**Files:**
- No code changes

**Step 1: Run web tests**

Run: `npm --prefix apps/web test`
Expected: PASS

**Step 2: Run agent tests**

Run: `PYTHONPATH=apps/agent .venv/bin/python -m unittest discover -s apps/agent/tests -p '*_unittest.py' -v`
Expected: PASS

**Step 3: Optional smoke confirmation**

Run one root script manually if needed to confirm it still starts with localhost settings.
