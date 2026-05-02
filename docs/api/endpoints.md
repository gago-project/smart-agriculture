# API Endpoints

## Web

- `GET /api/health`: web health check.
- `POST /api/agent/chat`: authenticated BFF proxy to agent `/chat-v2`; request must include `session_id`、`turn_id`、`client_message_id`、`current_context`、`message`.
- `GET /api/agent/chat-block`: authenticated snapshot pagination; request must include `snapshot_id`、`block_type`、`page`.
- `POST /api/soniox/token`: creates a temporary Soniox WebSocket token.

## Agent

- `GET /health`: agent health check.
- `POST /chat-v2`: deterministic data-answer endpoint.
