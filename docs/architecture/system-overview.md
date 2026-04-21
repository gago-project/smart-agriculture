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

- Answer type coverage follows `plans/2.2026-04-20-soil-moisture-agent-answer-types-business.md`.
- MVP acceptance follows `plans/3.2026-04-20-soil-moisture-agent-task16-test-matrix.md`.
- Flow safety follows `plans/8.2026-04-21-soil-moisture-agent-flow-risk-contract.md`.
