# API Endpoints

## Web

- `GET /api/health`: web health check.
- `POST /api/agent/chat`: authenticated session-based BFF proxy to agent `/chat-v2`.
- `GET /api/agent/chat-block`: authenticated block pagination and drill-down.
- `GET /api/agent/sessions`: authenticated session list.
- `POST /api/agent/sessions`: authenticated session create.
- `POST /api/soniox/token`: creates a temporary Soniox WebSocket token.

## Agent

- `GET /health`: agent health check.
- `POST /chat-v2`: deterministic data-answer endpoint.
