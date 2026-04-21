# Init Scripts Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make project initialization safe to commit and stable to run against Docker or localhost MySQL.

**Architecture:** Keep schema creation, business seed data, and local-only credential/user creation separate. Executable SQL under `infra/mysql/init` must be idempotent, deterministic, and free of real secrets. Local developer imports use scripts that read `.env` or explicit environment variables instead of hardcoded passwords.

**Tech Stack:** MySQL 8 SQL scripts, Docker Compose init directory, Node test runner, Bash helper scripts.

---

### Task 1: Add Initialization Safety Contract Tests

**Files:**
- Create: `apps/web/tests/db-init-hardening.test.mjs`
- Modify: `apps/web/tests/auth-contract.test.mjs`

**Step 1: Write failing tests**

Check that executable SQL files do not seed real password hashes/salts, that only schema/business seed SQL is executed by Docker, and that local import scripts use environment variables.

**Step 2: Run tests to verify failure**

Run: `npm --prefix apps/web test -- tests/db-init-hardening.test.mjs`

Expected: fail while `003_seed_auth_users.sql` exists and real hashes are present.

### Task 2: Split Schema and Business Inserts

**Files:**
- Rename/Replace: `infra/mysql/init/002_seed_data.sql` -> `infra/mysql/init/002_insert_data.sql`
- Modify: `README.md`

**Step 1: Move business rules/templates/facts into `002_insert_data.sql`**

Keep `001_init_tables.sql` as schema-only and `002_insert_data.sql` as idempotent business data only.

**Step 2: Ensure Docker still initializes data**

Docker entrypoint will run `001_init_tables.sql` then `002_insert_data.sql` in filename order.

### Task 3: Remove Real Credential Seeds From Commit Path

**Files:**
- Delete: `infra/mysql/init/003_seed_auth_users.sql`
- Create: `infra/mysql/local/README.md`
- Create: `infra/mysql/local/seed_auth_users.local.sql.example`
- Modify: `.gitignore`

**Step 1: Remove executable auth seed with real hashes**

No real `password_hash` or `password_salt` values should live in executable init SQL.

**Step 2: Provide local-only template**

Document that developers can generate or maintain a local-only auth seed outside Git.

### Task 4: Add Localhost Import Helper

**Files:**
- Create: `scripts/db/apply-local-init.sh`
- Modify: `package.json`
- Modify: `README.md`

**Step 1: Implement local init runner**

The script reads `.env`, accepts `MYSQL_*` overrides, runs `001_init_tables.sql` and `002_insert_data.sql`, and never prints passwords.

**Step 2: Add npm shortcut**

Add `db:init:local` so local MySQL can be initialized by one command.

### Task 5: Verify

**Files:**
- Test: `apps/web/tests/*.test.mjs`
- Runtime: local MySQL via `scripts/db/apply-local-init.sh`

**Step 1: Run focused tests**

Run: `npm --prefix apps/web test -- tests/db-init-hardening.test.mjs tests/auth-contract.test.mjs tests/db-schema-contract.test.mjs`

Expected: pass.

**Step 2: Run web test suite**

Run: `npm --prefix apps/web test`

Expected: pass.

**Step 3: Apply to localhost MySQL**

Run: `bash scripts/db/apply-local-init.sh`

Expected: `smart_agriculture` contains schema plus business rules/templates/fact seed data.
