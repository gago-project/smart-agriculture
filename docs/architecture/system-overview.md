# Smart Agriculture System Overview

## Runtime Services

- `web`: Next.js main platform. It serves pages, Admin entry, Chat UI, Soniox token API, and BFF routes.
- `agent`: Python FastAPI service. LLM + Function Calling single-agent. See `apps/agent/plans/1/` for design docs.
- `mysql`: Isolated `smart_agriculture` schema. It stores soil measurements, import batch, rules, templates, query logs, and admin logs.
- `redis`: Runtime context/cache service. Stores conversation message history (max 20 messages per session). Must not store full `FlowState`.

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

- Answer contract and migration direction follow `apps/agent/plans/1/2.answer-types-business.md` and `apps/agent/plans/1/9.llm-fc-design-audit.md`.
- Agent tool calling follows `apps/agent/app/llm/tools/soil_tools.py`.
- MVP acceptance follows `testdata/agent/soil-moisture/case-library.md` plus the soil-moisture QA skill/rule assets.
- Flow safety follows `apps/agent/plans/1/8.flow-risk-contract.md`.

## Documentation Boundaries

- `apps/agent/plans/`: Agent capability design, implementation plans, flow diagrams, and risk contracts only.
- `infra/mysql/docs/`: MySQL table design and database-side companion designs.
- `testdata/agent/soil-moisture/`: Single formal soil moisture Agent case library entry and long-term test-source directory.
- `.claude/.codex/.agents/.cursor` soil-moisture QA assets: testing rules, acceptance guidance, regression guidance, and review guidance.
- `outputs/`: One-off generated artifacts such as retest workbooks, CSV files, screenshots, and temporary review exports; not a long-term source of truth.
