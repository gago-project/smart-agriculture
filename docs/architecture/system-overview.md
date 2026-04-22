# Smart Agriculture System Overview

## Runtime Services

- `web`: Next.js main platform. It serves pages, Admin entry, Chat UI, Soniox token API, and BFF routes.
- `agent`: Python FastAPI service. It follows the restricted Flow design in `${GAGO_CLOUD_ROOT}/plans/4~8`.
- `mysql`: Isolated `smart_agriculture` schema. It stores soil measurements, import batch, rules, templates, query logs, and admin logs.
- `redis`: Runtime context/cache service. It must not store full `FlowState`.

## Service Boundaries

- Browser only calls `web`.
- `web` calls `agent` through `AGENT_BASE_URL`.
- `agent` reads MySQL for facts and uses Redis for short-lived context.
- Soniox long-lived key stays in `web` environment variables only.

## First Visible Features

- `/`: system overview and live soil summary cards.
- `/chat`: soil moisture agent chat page.
- `/admin`: soil data management overview table.
- `/api/health`: web health check.
- `agent:/health`: agent health check.
- `/api/agent/chat`: web BFF to agent chat.
- `/api/agent/summary`: web BFF to agent summary.

## Validation Basis

- Answer type coverage follows `apps/agent/plans/1/2.answer-types-business.md`.
- MVP acceptance follows `docs/testing/agent/soil-moisture/acceptance-test-matrix.md`.
- Flow safety follows `apps/agent/plans/1/8.flow-risk-contract.md`.

## Documentation Boundaries

- `apps/agent/plans/`: Agent capability design, implementation plans, flow diagrams, and risk contracts only.
- `infra/mysql/docs/`: MySQL table design and database-side companion designs.
- `docs/testing/agent/soil-moisture/`: Testing rules, acceptance guidance, regression guidance, and review guidance.
- `testdata/agent/soil-moisture/case-library.md`: Single formal soil moisture Agent case library. Future case additions, removals, and edits must be made here.
- `outputs/`: One-off generated artifacts such as retest workbooks, CSV files, screenshots, and temporary review exports; not a long-term source of truth.
