# Smart Agriculture System Overview

## Runtime Services

- `web`: Next.js main platform. It serves pages, Admin entry, Chat UI, Soniox token API, and BFF routes.
- `agent`: Python FastAPI service. Deterministic `/chat-v2` data-answer service. See `apps/agent/plans/1/9.query-profile-governance.md`.
- `mysql`: Isolated `smart_agriculture` schema. It stores soil measurements, import batch, rules, templates, query logs, and admin logs.

## Service Boundaries

- Browser only calls `web`.
- `web` calls `agent` through `AGENT_BASE_URL`.
- `agent` reads MySQL for facts and uses browser-side session context passed in from `web`.
- Chat history itself lives in browser localStorage; MySQL only keeps query evidence and audit logs.
- Soniox long-lived key stays in `web` environment variables only.

## First Visible Features

- `/`: system overview and live soil summary cards.
- `/chat`: soil moisture agent chat page.
- `/admin`: soil data management overview table.
- `/api/health`: web health check.
- `/api/agent/chat`: web BFF to agent chat.
- `agent:/health`: agent health check.

## Validation Basis

- Answer contract follows `apps/agent/plans/1/9.query-profile-governance.md`.
- MVP acceptance follows `testdata/agent/soil-moisture/case-library.md` plus the soil-moisture QA skill/rule assets.
- Region alias resolution follows `infra/mysql/docs/region-alias-resolution.md`.

## Documentation Boundaries

- `apps/agent/plans/`: Agent capability design, implementation plans, flow diagrams, and risk contracts only.
- `infra/mysql/docs/`: MySQL table design and database-side companion designs.
- `testdata/agent/soil-moisture/`: Single formal soil moisture Agent case library entry and long-term test-source directory.
- `.claude/.codex/.agents/.cursor` soil-moisture QA assets: testing rules, acceptance guidance, regression guidance, and review guidance.
- `outputs/`: One-off generated artifacts such as retest workbooks, CSV files, screenshots, and temporary review exports; not a long-term source of truth.
