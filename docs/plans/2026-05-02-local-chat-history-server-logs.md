# Local Chat History With Server Logs Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 删除后端 `agent_chat_session / agent_chat_turn` 会话持久化，只保留浏览器 `localStorage` 聊天历史，同时继续保留后端 `agent_query_log` 供管理员查证据。

**Architecture:** Web 前端改为本地会话真源：本地生成 `session_id`、递增 `turn_id`、保存 `messages + turn_context + blocks`。BFF 不再维护后端会话表，只负责把本地会话上下文透传到 agent `/chat-v2`，并把本轮返回的 `query_log_entries` 直接写入 `agent_query_log`。列表/分组分页不再依赖 `agent_chat_turn.blocks_json`，统一改为通过 `snapshot_id` 直接从 `agent_result_snapshot_item` 拉页数据。管理员证据接口继续按 `session_id + turn_id` 从 `agent_query_log` 查真实 SQL 与真实结果。

**Tech Stack:** Next.js App Router、Zustand persist、Node server helpers、FastAPI `/chat-v2`、MySQL、Node test、pytest、SQL init docs

---

### Task 1: 先写失败测试，锁定“本地聊天真源 + 后端只保留日志”的新契约

**Files:**
- Modify: `apps/web/tests/chat-session-contract.test.mjs`
- Modify: `apps/web/tests/chat-query-evidence-contract.test.mjs`
- Modify: `apps/web/tests/db-schema-contract.test.mjs`
- Modify: `apps/web/tests/file-contract.test.mjs`

**Step 1: 把旧的服务端会话契约测试改成新契约**

- 删除对以下文件存在性的断言：
  - `apps/web/app/api/agent/sessions/route.ts`
  - `apps/web/app/api/agent/sessions/[sessionId]/route.ts`
  - `apps/web/app/api/agent/sessions/[sessionId]/archive/route.ts`
  - `apps/web/app/api/agent/chat-block/route.ts`
  - `apps/web/lib/server/chatSessionRepository.mjs`
- 新增断言：
  - `apps/web/app/api/agent/chat/route.ts` 仍存在
  - `apps/web/lib/server/agentChatRuntime.mjs`（新文件）存在
  - `chat route` 必须接收 `session_id / turn_id / current_context / client_message_id / message`
  - `chat route` 不得再引用 `executeChatTurn`、`chatSessionRepository`、`createChatSession`

**Step 2: 锁定前端本地会话真源**

- 断言 `apps/web/workspace/store/chatStore.ts` 的 `partialize` 会持久化：
  - `sessions`
  - `activeSessionId`
  - `selectedAssistantMessageIds`
- 断言 store 不再只保留轻量 UI 状态
- 断言 `useChatActions.ts` 不再调用：
  - `fetchChatSessions`
  - `fetchChatSession`
  - `createChatSession`
  - `archiveChatSession`
  - `renameChatSession`
- 断言 `sendChat(...)` 调用时会传 `turn_id` 与 `current_context`

**Step 3: 锁定分页改为 `snapshot_id` 驱动**

- 断言 `TurnRenderer.tsx` 不再调用 `fetchChatBlock(session_id, turn_id, block_id, page)`
- 新契约改为基于 `snapshot_id` 拉页，例如：
  - `fetchChatBlock(snapshotId, blockType, page, pageSize)`
- 断言 `chat block` 接口如果保留，不能再依赖 `agent_chat_turn.blocks_json`

**Step 4: 锁定数据库设计变化**

- 在 `db-schema-contract.test.mjs` 中删除对以下表的要求：
  - `agent_chat_session`
  - `agent_chat_turn`
- 保留并加强对以下表的断言：
  - `agent_query_log`
  - `agent_result_snapshot`
  - `agent_result_snapshot_item`
- 新增断言：`agent_query_log` 仍保留 `session_id / turn_id / query_id / executed_sql_text / executed_result_json`

**Step 5: 运行测试确认失败**

Run:
```bash
node --test apps/web/tests/chat-session-contract.test.mjs apps/web/tests/chat-query-evidence-contract.test.mjs apps/web/tests/db-schema-contract.test.mjs apps/web/tests/file-contract.test.mjs
```

Expected:
- 旧服务端会话路由/仓储相关断言失败
- 本地 store 持久化范围断言失败
- snapshot 分页契约断言失败
- schema 仍要求 chat session 表而失败

**Step 6: Commit**

```bash
git add apps/web/tests/chat-session-contract.test.mjs apps/web/tests/chat-query-evidence-contract.test.mjs apps/web/tests/db-schema-contract.test.mjs apps/web/tests/file-contract.test.mjs
git commit -m "test: lock local chat history contract"
```

### Task 2: 删除后端会话表与旧 BFF 会话链路，只保留实时聊天 + 日志写入

**Files:**
- Delete: `apps/web/app/api/agent/sessions/route.ts`
- Delete: `apps/web/app/api/agent/sessions/[sessionId]/route.ts`
- Delete: `apps/web/app/api/agent/sessions/[sessionId]/archive/route.ts`
- Delete: `apps/web/lib/server/chatSessionRepository.mjs`
- Modify: `apps/web/app/api/agent/chat/route.ts`
- Create: `apps/web/lib/server/agentChatRuntime.mjs`
- Modify: `apps/web/lib/server/agentLogRepository.mjs`
- Modify: `apps/web/lib/server/mysql.mjs` (only if需要复用事务/连接 helper)

**Step 1: 为新的 chat route 写一个最小失败实现测试心智**

- 新的 `POST /api/agent/chat` 只做四件事：
  1. 鉴权
  2. 透传 `session_id / turn_id / current_context / message / timezone` 到 agent `/chat-v2`
  3. 将 agent 返回的 `query_log_entries` 写入 `agent_query_log`
  4. 原样返回当前轮结果
- 不再：
  - 读/写 `agent_chat_session`
  - 读/写 `agent_chat_turn`
  - 保留 `pending` turn 锁逻辑

**Step 2: 新建 `agentChatRuntime.mjs`**

- 迁移并简化 `chatSessionRepository.mjs` 中仍有价值的能力：
  - `parseAgentChatV2Response`
  - 调 agent `/chat-v2`
  - 将 `query_log_entries` 批量插入 `agent_query_log`
- 新文件只暴露一个主入口，例如：
  - `runAgentChatTurn({ message, sessionId, turnId, currentContext, clientMessageId, timezone, agentBaseUrl })`
- `client_message_id` 仍保留在 HTTP 契约中，作为前端幂等标识，但后端不再落会话表；第一版可只透传不持久化

**Step 3: 改造 `/api/agent/chat`**

- 请求体固定读取：
  - `session_id`
  - `turn_id`
  - `client_message_id`
  - `current_context`
  - `message`
  - `timezone`
- 调用 `runAgentChatTurn(...)`
- 返回 agent 当前轮响应，不再拼接服务端 session 元数据

**Step 4: 将日志写入逻辑从“会话收尾”中解耦**

- 把 `insertQueryLogs(...)` 从旧 `chatSessionRepository.mjs` 挪到新运行时 helper
- 保证 `agent_query_log` 写入仍使用：
  - `session_id`
  - `turn_id`
  - `query_id`
  - `executed_sql_text`
  - `executed_result_json`
- `session_id / turn_id` 的真源改为前端本地生成值，而非 DB 会话表

**Step 5: 调整管理员证据接口的说明，但不改其真源**

- `agentLogRepository.mjs` 继续按 `session_id + turn_id` 查证据
- 如果当前实现中有任何对 `agent_chat_turn` 的 fallback 依赖，直接删掉

**Step 6: 跑定向测试**

Run:
```bash
node --test apps/web/tests/chat-session-contract.test.mjs apps/web/tests/chat-query-evidence-contract.test.mjs
```

Expected:
- PASS，确认 web route 与日志链路不再依赖服务端会话仓储

**Step 7: Commit**

```bash
git add apps/web/app/api/agent/chat/route.ts apps/web/lib/server/agentChatRuntime.mjs apps/web/lib/server/agentLogRepository.mjs apps/web/app/api/agent/sessions apps/web/lib/server/chatSessionRepository.mjs
git commit -m "refactor: remove server chat session persistence"
```

### Task 3: 把前端聊天改成完全本地会话模式

**Files:**
- Modify: `apps/web/workspace/store/chatStore.ts`
- Modify: `apps/web/workspace/hooks/useChatActions.ts`
- Modify: `apps/web/workspace/services/chatApi.ts`
- Modify: `apps/web/workspace/types/chat.ts`
- Modify: `apps/web/workspace/components/SessionSidebar.tsx`

**Step 1: 先定义本地会话需要保存的数据**

- `Session` 在本地必须持久化：
  - `id`
  - `title`
  - `createdAt`
  - `updatedAt`
  - `messages`
  - `lastTurnId`
  - `currentContext`
- `Message.meta.data` 继续保存轻量引用：
  - `session_id`
  - `turn_id`
  - `should_query`
  - `answer_kind`
  - `capability`
- `Message.meta.turn` 保留当前轮 blocks，供刷新后直接渲染

**Step 2: 改 `chatStore.ts` 为完整持久化**

- 删除“只持久化 activeSessionId 和 selectedAssistantMessageIds”的旧策略
- `partialize` 改为持久化：
  - `sessions`
  - `activeSessionId`
  - `selectedAssistantMessageIds`
- `migrate` 负责兼容现有轻量存储，遇到旧版本时：
  - 默认保留 `activeSessionId`
  - `sessions` 回退为空数组

**Step 3: 重写 `useChatActions.ts`**

- 删除所有远程会话操作：
  - `fetchChatSessions`
  - `fetchChatSession`
  - `createChatSession`
  - `renameChatSession`
  - `archiveChatSession`
- 本地新建会话：
  - 生成 `session_id`（UUID）
  - 插入 store
- 本地重命名/删除：
  - 直接更新 store
- 发送消息时：
  - `turn_id = session.lastTurnId + 1`
  - 从 session 取 `currentContext`
  - 调 `sendChat(sessionId, turnId, clientMessageId, question, currentContext)`
  - 响应成功后更新：
    - assistant message
    - `lastTurnId`
    - `currentContext = result.turn_context`
    - `updatedAt`

**Step 4: 调整 `chatApi.ts`**

- 删除会话类 API 方法：
  - `createChatSession`
  - `fetchChatSessions`
  - `fetchChatSession`
  - `renameChatSession`
  - `archiveChatSession`
- `sendChat(...)` 签名改为：
  - `sendChat(sessionId, turnId, clientMessageId, message, currentContext, timeoutMs?)`
- `fetchChatBlock(...)` 暂不删除，下一任务改成 snapshot 版签名

**Step 5: 调整 `SessionSidebar.tsx` 文案**

- “服务端会话”改成更准确的 MVP 文案，例如：
  - `本地会话`
- “归档”改成真正的本地删除或隐藏操作文案，避免误导

**Step 6: 跑前端契约测试**

Run:
```bash
node --test apps/web/tests/chat-session-contract.test.mjs apps/web/tests/file-contract.test.mjs
```

Expected:
- PASS，确认前端已不依赖服务端会话接口

**Step 7: Commit**

```bash
git add apps/web/workspace/store/chatStore.ts apps/web/workspace/hooks/useChatActions.ts apps/web/workspace/services/chatApi.ts apps/web/workspace/types/chat.ts apps/web/workspace/components/SessionSidebar.tsx
git commit -m "feat: persist chat history in local storage"
```

### Task 4: 重做分页区块接口，改成 `snapshot_id` 直连，不再依赖 `agent_chat_turn`

**Files:**
- Modify: `apps/web/app/api/agent/chat-block/route.ts` or Replace with a simpler snapshot route
- Modify: `apps/web/lib/server/agentLogRepository.mjs` or Create: `apps/web/lib/server/chatBlockRepository.mjs`
- Modify: `apps/web/workspace/services/chatApi.ts`
- Modify: `apps/web/workspace/components/TurnRenderer.tsx`
- Modify: `apps/web/workspace/types/chat.ts`

**Step 1: 先定新接口契约**

- 保留原路径也可以，但请求参数改为：
  - `snapshot_id`
  - `block_type`
  - `page`
  - `page_size`
- 不再需要：
  - `session_id`
  - `turn_id`
  - `block_id`

**Step 2: 提取 snapshot 拉页仓储**

- 用现有 `agent_result_snapshot_item` 做唯一真源
- 新 helper 负责：
  - 按 `snapshot_id` 取分页 rows
  - 返回：
    - `rows`
    - `pagination`
    - `snapshot_id`
- 不再读取任何 `agent_chat_turn.blocks_json`

**Step 3: 改 `TurnRenderer.tsx`**

- 翻页时从当前 `block.pagination.snapshot_id` 直接请求下一页
- `setViewBlock` 时只合并新的：
  - `rows`
  - `pagination`
- 不再依赖 `turn.session_id / turn.turn_id / block.block_id`

**Step 4: 改 `chatApi.ts` 类型**

- `fetchChatBlock(...)` 新签名改为：
  - `fetchChatBlock(snapshotId, blockType, page, pageSize?)`

**Step 5: 跑分页相关契约测试**

Run:
```bash
node --test apps/web/tests/chat-session-contract.test.mjs apps/web/tests/chat-query-evidence-contract.test.mjs
```

Expected:
- PASS，确认分页现在走 snapshot，而不是 server turn storage

**Step 6: Commit**

```bash
git add apps/web/app/api/agent/chat-block/route.ts apps/web/lib/server/chatBlockRepository.mjs apps/web/workspace/services/chatApi.ts apps/web/workspace/components/TurnRenderer.tsx apps/web/workspace/types/chat.ts
git commit -m "refactor: paginate chat blocks by snapshot id"
```

### Task 5: 删除数据库中的会话表设计，并同步文档与契约

**Files:**
- Modify: `infra/mysql/init/001_init_tables.sql`
- Modify: `infra/mysql/docs/agent_query_log.md`
- Modify: `docs/api/endpoints.md`
- Modify: `docs/architecture/system-overview.md`
- Modify: `apps/agent/README.md` (only if it still implies server-backed session storage)
- Modify: `apps/web/tests/db-schema-contract.test.mjs`

**Step 1: 删除 schema 中的两张表**

- 从 `001_init_tables.sql` 删除：
  - `agent_chat_session`
  - `agent_chat_turn`
- 若 init 文件中有与这两张表相关的 index / foreign key / cleanup 语句，一并删除

**Step 2: 加一个显式清理动作，保证“彻底删除”**

- 在 init 或单独清理脚本中增加：
  - `DROP TABLE IF EXISTS agent_chat_turn;`
  - `DROP TABLE IF EXISTS agent_chat_session;`
- 目的：已跑过旧库的环境也能被同步清掉

**Step 3: 更新文档**

- `docs/api/endpoints.md`
  - 删 `/api/agent/sessions*`
  - 说明 `/api/agent/chat` 现在依赖前端传入 `session_id / turn_id / current_context`
- `docs/architecture/system-overview.md`
  - 明确聊天历史存在浏览器本地，后端只保留问答执行与查询日志
- `infra/mysql/docs/agent_query_log.md`
  - 明确 `session_id / turn_id` 是前端本地会话标识，不代表服务端持久化会话表

**Step 4: 跑 schema / docs 契约测试**

Run:
```bash
node --test apps/web/tests/db-schema-contract.test.mjs apps/web/tests/file-contract.test.mjs
```

Expected:
- PASS，确认数据库和文档只保留新真相

**Step 5: Commit**

```bash
git add infra/mysql/init/001_init_tables.sql infra/mysql/docs/agent_query_log.md docs/api/endpoints.md docs/architecture/system-overview.md apps/agent/README.md apps/web/tests/db-schema-contract.test.mjs apps/web/tests/file-contract.test.mjs
git commit -m "docs: align local chat history architecture"
```

### Task 6: 全量回归并做一次本地人工链路验证

**Files:**
- Modify: 无

**Step 1: 跑 agent 单测**

Run:
```bash
PYTHONPATH=apps/agent .venv/bin/pytest apps/agent/tests -q
```

Expected:
- PASS

**Step 2: 跑 web 关键契约测试**

Run:
```bash
node --test apps/web/tests/chat-session-contract.test.mjs apps/web/tests/chat-query-evidence-contract.test.mjs apps/web/tests/db-schema-contract.test.mjs apps/web/tests/file-contract.test.mjs
```

Expected:
- PASS

**Step 3: 本地人工烟雾验证**

验证点：
- 新建本地会话，刷新页面后消息仍在
- 换一个浏览器 profile 后消息不存在（符合本地 MVP 预期）
- 继续追问时，`turn_context` 继承正常
- list/group 分页仍可翻页
- 管理员右侧证据面板仍能按当前 assistant 消息加载 SQL 和结果
- `agent_query_log` 中仍有正确的 `session_id / turn_id`

**Step 4: 最终提交**

```bash
git add -A
git commit -m "refactor: move chat history to local storage"
```
