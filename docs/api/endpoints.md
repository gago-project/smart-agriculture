# API Endpoints

## Web

- `GET /api/health`: web health check.
- `GET /api/soil/summary`: BFF summary from agent `/summary`.
- `POST /api/agent/chat`: BFF proxy to agent `/chat`.
- `POST /api/soniox/token`: creates a temporary Soniox WebSocket token.

## Agent

- `GET /health`: agent health check.
- `GET /summary`: soil summary payload for dashboard/admin.
- `POST /chat`: restricted Flow chat endpoint.
- `POST /analyze`: alias for chat-style analysis.
