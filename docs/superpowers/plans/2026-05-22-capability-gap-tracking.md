# Capability Gap Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 当 agent 返回兜底（safe_hint / unsupported_derived / closed_context / clarification）而非真实数据时，将该回合自动记录到 `agent_query_log`，并在 admin 页新增"能力盲区"视图，让管理员看到用户问了哪些当前能力无法回答的问题。

**Architecture:** 在 `DataAnswerService.reply()` 中拦截 guidance 类型响应，补充一条 `query_type="guidance"` 的日志条目。Web BFF 的 `insertQueryLogs` 透传 `fallback_reason` 字段写入 DB。前端新增独立视图 `/capability-gaps`，通过现有 `query_type` 过滤器拉取 guidance 记录。

**Tech Stack:** Python / FastAPI (agent), Next.js / TypeScript (web), MySQL, React

---

## File Map

| 文件 | 变更类型 | 职责 |
|---|---|---|
| `infra/mysql/init/001_init_tables.sql` | Modify | 新增 `fallback_reason` 列 |
| `apps/agent/app/services/data_answer_service.py` | Modify | `reply()` 拦截 guidance 响应，生成日志条目 |
| `apps/agent/tests/test_data_answer_service_unittest.py` | Modify | 验证 guidance 响应带日志条目 |
| `apps/web/lib/server/agentChatRuntime.mjs` | Modify | `insertQueryLogs` 写入 `fallback_reason` |
| `apps/web/lib/server/agentLogRepository.mjs` | Modify | SELECT 加 `fallback_reason`；支持 `query_type=guidance` 过滤 |
| `apps/web/workspace/services/agentLogApi.ts` | Modify | `AgentQueryLog` 类型加 `fallback_reason` |
| `apps/web/workspace/components/CapabilityGapsPage.tsx` | Create | 能力盲区视图组件 |
| `apps/web/app/capability-gaps/page.tsx` | Create | Next.js 页面路由 |
| `apps/web/workspace/App.tsx` | Modify | 路由 `/capability-gaps` → `CapabilityGapsPage` |
| `apps/web/workspace/components/WorkspaceUserMenu.tsx` | Modify | admin 用户导航加"能力盲区"入口 |

---

## Task 1: DB Migration — 新增 `fallback_reason` 列

**Files:**
- Modify: `infra/mysql/init/001_init_tables.sql`

- [ ] **Step 1: 在 `001_init_tables.sql` 末尾的 `ensure_column` 块中追加一行**

找到文件中最后一个 `ensure_column` 调用（约第 270 行），在其后追加：

```sql
CALL ensure_column('agent_query_log', 'fallback_reason', 'ALTER TABLE agent_query_log ADD COLUMN fallback_reason VARCHAR(64) NULL AFTER status');
```

- [ ] **Step 2: 在线上 MySQL 直接执行 DDL（不重建容器）**

```bash
# 进入 MySQL（密码从 .env 读取）
source .env
mysql -h 127.0.0.1 -P 3306 -u "${MYSQL_USER}" -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE}" \
  -e "ALTER TABLE agent_query_log ADD COLUMN IF NOT EXISTS fallback_reason VARCHAR(64) NULL AFTER status;"
```

Expected: `Query OK, 0 rows affected` 或 `Duplicate column name` 均可继续。

- [ ] **Step 3: 验证列存在**

```bash
source .env
mysql -h 127.0.0.1 -P 3306 -u "${MYSQL_USER}" -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE}" \
  -e "SHOW COLUMNS FROM agent_query_log LIKE 'fallback_reason';"
```

Expected output 包含 `fallback_reason` 行。

- [ ] **Step 4: Commit**

```bash
git add infra/mysql/init/001_init_tables.sql
git commit -m "feat(db): add fallback_reason column to agent_query_log"
```

---

## Task 2: Agent — `reply()` 为 guidance 响应补充日志条目

**Files:**
- Modify: `apps/agent/app/services/data_answer_service.py`
- Test: `apps/agent/tests/test_data_answer_service_unittest.py`

### Step 1: 写失败测试

- [ ] 在 `test_data_answer_service_unittest.py` 末尾添加新测试类：

```python
class GuidanceQueryLogTest(unittest.IsolatedAsyncioTestCase):
    """reply() must emit a query_log_entries entry for guidance (fallback) responses."""

    async def asyncSetUp(self) -> None:
        from app.services.data_answer_service import DataAnswerService
        from app.services.input_guard_service import InputGuardResult

        class OOSGuard:
            def classify(self, _text):
                return InputGuardResult(
                    allow_business_flow=False,
                    suggested_answer="超出范围",
                    guidance_reason="safe_hint",
                )

        self.service = DataAnswerService(
            soil_repository=SeedSoilRepository(),
            input_guard=OOSGuard(),
        )

    async def test_guidance_response_has_log_entry(self):
        result = await self.service.reply(
            message="今天天气怎么样",
            session_id="test-session",
            turn_id=1,
            current_context=None,
        )
        self.assertEqual(result["answer_kind"], "guidance")
        entries = result.get("query_log_entries", [])
        self.assertEqual(len(entries), 1, "guidance 响应必须包含一条日志条目")
        entry = entries[0]
        self.assertEqual(entry["query_type"], "guidance")
        self.assertEqual(entry["fallback_reason"], "safe_hint")
        self.assertEqual(entry["request_text"], "今天天气怎么样")
        self.assertIsNotNone(entry.get("query_id"))
        self.assertEqual(entry["session_id"], "test-session")
        self.assertEqual(entry["turn_id"], 1)

    async def test_normal_response_has_no_guidance_query_type(self):
        """正常数据回答不应被标记为 guidance。"""
        result = await self.service.reply(
            message="最近墒情怎么样",
            session_id="test-session",
            turn_id=1,
            current_context=None,
        )
        # 正常回答的 query_log_entries 中 query_type 不应为 guidance
        entries = result.get("query_log_entries", [])
        for entry in entries:
            self.assertNotEqual(entry.get("query_type"), "guidance")
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd apps/agent
python -m pytest tests/test_data_answer_service_unittest.py::GuidanceQueryLogTest -v
```

Expected: `FAILED` with `AssertionError: guidance 响应必须包含一条日志条目`

### Step 3: 实现最小修改

- [ ] 在 `data_answer_service.py` 的 `import` 区（第 3-14 行）加入 `uuid`：

```python
import uuid
```

（与现有 `import re`、`import time` 同组）

- [ ] 修改 `reply()` 方法（第 213-231 行），在 `return response` 前插入 guidance 日志逻辑：

```python
async def reply(
    self,
    *,
    message: str,
    session_id: str,
    turn_id: int,
    current_context: dict[str, Any] | None,
    timezone: str = "Asia/Shanghai",
) -> dict[str, Any]:
    """Handle one deterministic data-answer turn."""
    response = await self._reply_impl(
        message=message,
        session_id=session_id,
        turn_id=turn_id,
        current_context=current_context,
        timezone=timezone,
    )
    self.fact_check_service.verify(response)
    if response.get("answer_kind") == "guidance" and not response.get("query_log_entries"):
        guidance_blocks = response.get("blocks") or []
        fallback_reason = next(
            (b.get("guidance_reason") for b in guidance_blocks if b.get("block_type") == "guidance_card"),
            "unknown",
        )
        response["query_log_entries"] = [
            {
                "query_id": str(uuid.uuid4()),
                "session_id": session_id,
                "turn_id": turn_id,
                "request_text": message,
                "response_text": response.get("final_text", ""),
                "query_type": "guidance",
                "fallback_reason": fallback_reason,
                "status": "succeeded",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "query_plan_json": {},
                "time_range_json": {},
                "filters_json": {},
                "row_count": 0,
            }
        ]
    return response
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
cd apps/agent
python -m pytest tests/test_data_answer_service_unittest.py::GuidanceQueryLogTest -v
```

Expected: `2 passed`

- [ ] **Step 5: 运行全量 agent 单测，确认无回归**

```bash
cd apps/agent
python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: 全部 pass，无新 failure。

- [ ] **Step 6: Commit**

```bash
git add apps/agent/app/services/data_answer_service.py \
        apps/agent/tests/test_data_answer_service_unittest.py
git commit -m "feat(agent): emit query_log_entries for guidance (fallback) responses"
```

---

## Task 3: Web BFF — `insertQueryLogs` 写入 `fallback_reason`

**Files:**
- Modify: `apps/web/lib/server/agentChatRuntime.mjs`

- [ ] **Step 1: 在 `insertQueryLogs` 的 INSERT SQL 中加入 `fallback_reason` 列**

找到 `insertQueryLogs` 函数内的 INSERT 语句（列名区块在 `source_files_json` 后，`status` 前），将列名区块改为：

```javascript
const sql = `INSERT INTO agent_query_log (
    query_id,
    session_id,
    turn_id,
    request_text,
    response_text,
    input_type,
    intent,
    answer_type,
    final_status,
    query_type,
    query_plan_json,
    query_spec_json,
    sql_fingerprint,
    executed_sql_text,
    time_range_json,
    filters_json,
    group_by_json,
    metrics_json,
    order_by_json,
    limit_size,
    row_count,
    snapshot_id,
    executed_result_json,
    result_digest_json,
    source_files_json,
    fallback_reason,
    status,
    error_message,
    created_at
  ) VALUES ${rows
    .map(() => '(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)')
    .join(', ')}
  ON DUPLICATE KEY UPDATE
    response_text = VALUES(response_text),
    final_status = VALUES(final_status),
    query_plan_json = VALUES(query_plan_json),
    query_spec_json = VALUES(query_spec_json),
    executed_sql_text = VALUES(executed_sql_text),
    time_range_json = VALUES(time_range_json),
    filters_json = VALUES(filters_json),
    group_by_json = VALUES(group_by_json),
    metrics_json = VALUES(metrics_json),
    order_by_json = VALUES(order_by_json),
    limit_size = VALUES(limit_size),
    row_count = VALUES(row_count),
    snapshot_id = VALUES(snapshot_id),
    executed_result_json = VALUES(executed_result_json),
    result_digest_json = VALUES(result_digest_json),
    source_files_json = VALUES(source_files_json),
    fallback_reason = VALUES(fallback_reason),
    status = VALUES(status),
    error_message = VALUES(error_message)`;
```

- [ ] **Step 2: 在 `params` flatMap 中，在 `source_files_json` 和 `status` 之间插入 `fallback_reason`**

找到 params flatMap，在 `jsonStringify(entry.source_files_json, null),` 后、`String(entry.status || 'succeeded'),` 前插入：

```javascript
entry.fallback_reason ?? null,
```

- [ ] **Step 3: 验证 placeholder 数量匹配**

SQL 中有 29 列，`params` flatMap 每条记录也应有 29 个值。数一下 `?` 的数量和 flatMap 的参数数量是否一致：

```bash
grep -c "??" apps/web/lib/server/agentChatRuntime.mjs || true
node -e "
const sql = \`(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)\`;
console.log('placeholder count:', (sql.match(/\?/g) || []).length);
"
```

Expected: `29`

- [ ] **Step 4: Commit**

```bash
git add apps/web/lib/server/agentChatRuntime.mjs
git commit -m "feat(web-bff): persist fallback_reason in agent_query_log"
```

---

## Task 4: Web Repo + API — 返回 `fallback_reason` 字段

**Files:**
- Modify: `apps/web/lib/server/agentLogRepository.mjs`
- Modify: `apps/web/workspace/services/agentLogApi.ts`

- [ ] **Step 1: 在 `listAgentQueryLogs` 的详情 SELECT 中加入 `fallback_reason`**

找到约第 273 行的 SELECT 块（`query_id, session_id, ... created_at`），在 `status,` 和 `error_message,` 之间插入：

```sql
fallback_reason,
```

完整的相关列区域变为：
```sql
query_type,
sql_fingerprint,
row_count,
status,
fallback_reason,
error_message,
DATE_FORMAT(created_at, '%Y-%m-%d %H:%i:%s') AS created_at,
```

- [ ] **Step 2: 在 `fromDbSummaryLog` 函数中映射 `fallback_reason`**

找到 `fromDbSummaryLog` 函数（约第 140 行），在返回对象中加入：

```javascript
fallback_reason: row.fallback_reason ?? null,
```

与 `query_type: row.query_type,` 相邻。

- [ ] **Step 3: 在 `AgentQueryLog` 类型中新增字段**

在 `apps/web/workspace/services/agentLogApi.ts` 的 `AgentQueryLog` interface 中加入：

```typescript
fallback_reason?: string | null;
```

紧跟在 `query_type?: string | null;` 之后。

- [ ] **Step 4: Commit**

```bash
git add apps/web/lib/server/agentLogRepository.mjs \
        apps/web/workspace/services/agentLogApi.ts
git commit -m "feat(web): expose fallback_reason in query log list API"
```

---

## Task 5: Admin UI — 能力盲区视图

**Files:**
- Create: `apps/web/workspace/components/CapabilityGapsPage.tsx`
- Create: `apps/web/app/capability-gaps/page.tsx`
- Modify: `apps/web/workspace/App.tsx`
- Modify: `apps/web/workspace/components/WorkspaceUserMenu.tsx`

### Step 1: 创建 CapabilityGapsPage 组件

- [ ] 新建 `apps/web/workspace/components/CapabilityGapsPage.tsx`：

```tsx
import { useCallback, useEffect, useState } from 'react';
import { fetchAgentQueryLogs, type AgentQueryLog, type AgentQueryLogPage } from '../services/agentLogApi';

const PAGE_SIZE = 30;

const FALLBACK_REASON_LABEL: Record<string, string> = {
  safe_hint: '超出范围',
  unsupported_derived: '不支持的推导分析',
  closed_context: '话题已关闭',
  clarification: '需要澄清',
  boundary: '能力边界',
  unknown: '未知原因',
};

function reasonLabel(reason: string | null | undefined): string {
  if (!reason) return '-';
  return FALLBACK_REASON_LABEL[reason] ?? reason;
}

function preview(text: string | null | undefined, max = 80): string {
  const s = String(text || '').trim();
  return s.length > max ? `${s.slice(0, max)}…` : s || '-';
}

const emptyPage: AgentQueryLogPage = { rows: [], total: 0, page: 1, page_size: PAGE_SIZE, total_pages: 0 };

export function CapabilityGapsPage() {
  const [page, setPage] = useState(1);
  const [data, setData] = useState<AgentQueryLogPage>(emptyPage);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (targetPage: number) => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchAgentQueryLogs({
        page: targetPage,
        page_size: PAGE_SIZE,
        query_type: 'guidance',
      });
      setData(result);
      setPage(targetPage);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(1); }, [load]);

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <h2 className="admin-page-title">能力盲区</h2>
        <p className="admin-page-subtitle">
          用户提问但系统无法回答的记录（共 {data.total} 条）
        </p>
      </div>

      {error ? (
        <p className="admin-error">{error}</p>
      ) : loading ? (
        <p className="admin-loading">加载中…</p>
      ) : data.rows.length === 0 ? (
        <p className="admin-empty">暂无记录</p>
      ) : (
        <>
          <table className="admin-table">
            <thead>
              <tr>
                <th>时间</th>
                <th>用户问题</th>
                <th>兜底原因</th>
                <th>Session ID</th>
              </tr>
            </thead>
            <tbody>
              {data.rows.map((row: AgentQueryLog) => (
                <tr key={row.query_id}>
                  <td className="admin-table-cell-nowrap">{row.created_at}</td>
                  <td>{preview(row.request_text, 100)}</td>
                  <td>{reasonLabel(row.fallback_reason)}</td>
                  <td className="admin-table-cell-mono">{preview(row.session_id, 16)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {data.total_pages > 1 ? (
            <div className="admin-pagination">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => void load(page - 1)}
              >
                上一页
              </button>
              <span>{page} / {data.total_pages}</span>
              <button
                type="button"
                disabled={page >= data.total_pages}
                onClick={() => void load(page + 1)}
              >
                下一页
              </button>
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}
```

### Step 2: 创建 Next.js 页面

- [ ] 新建 `apps/web/app/capability-gaps/page.tsx`：

```tsx
import WorkspaceApp from '../../workspace/App';

export default function CapabilityGapsPage() {
  return <WorkspaceApp />;
}
```

### Step 3: 在 App.tsx 中添加路由

- [ ] 在 `App.tsx` 约第 57-63 行的 `currentView` 计算中，在 `'agent-logs'` 分支后追加：

```typescript
: pathname === '/capability-gaps' && canManageSoilAdmin
  ? 'capability-gaps'
```

完整的 currentView 逻辑变为：
```typescript
const currentView =
  pathname === '/admin' && canManageSoilAdmin
    ? 'soil-admin'
    : pathname === '/query-logs' && canViewAgentLogs
      ? 'agent-logs'
      : pathname === '/capability-gaps' && canManageSoilAdmin
        ? 'capability-gaps'
        : 'chat';
```

- [ ] 在 `App.tsx` 的权限检查部分（约第 54-56 行）加入重定向守卫：

```typescript
(pathname === '/capability-gaps' && !canManageSoilAdmin)
```

（放在 `(pathname === '/query-logs' && !canViewAgentLogs)` 同行 `||` 后）

- [ ] 在 `App.tsx` 顶部 import 区加入：

```typescript
import { CapabilityGapsPage } from './components/CapabilityGapsPage';
```

- [ ] 在 JSX 的视图切换部分（约第 162-166 行），在 `agent-logs` 分支后加入：

```tsx
) : currentView === 'capability-gaps' ? (
  <CapabilityGapsPage />
```

### Step 4: 在导航中加入入口

- [ ] 在 `WorkspaceUserMenu.tsx` 中，在"查询日志"按钮后加入"能力盲区"入口（仅 `canManageSoilAdmin`）：

```tsx
{canManageSoilAdmin ? (
  <button
    type="button"
    className="workspace-menu-item"
    aria-current={currentPath === '/capability-gaps' ? 'page' : undefined}
    onClick={() => navigateTo('/capability-gaps')}
  >
    能力盲区
  </button>
) : null}
```

在 `WorkspaceUserMenuProps` interface 中确认已有 `canManageSoilAdmin` 属性（已存在，无需新增）。

### Step 5: 构建验证

- [ ] 运行 TypeScript 检查：

```bash
npm --prefix apps/web run build 2>&1 | tail -20
```

Expected: `✓ Compiled successfully` 无 type error。

### Step 6: Commit

- [ ] 

```bash
git add apps/web/workspace/components/CapabilityGapsPage.tsx \
        apps/web/app/capability-gaps/page.tsx \
        apps/web/workspace/App.tsx \
        apps/web/workspace/components/WorkspaceUserMenu.tsx
git commit -m "feat(ui): add capability gaps admin view for unanswered queries"
```

---

## Task 6: 端到端验活

- [ ] **重启服务**

```bash
bash scripts/dev/start-local-agent.sh > /tmp/agent.log 2>&1 &
bash scripts/dev/start-local-web.sh > /tmp/web.log 2>&1 &
sleep 8
```

- [ ] **发一条超出范围的问题，触发 guidance 日志**

```bash
source .env
AUTH_TOKEN=$(curl -fsS -X POST "http://localhost:3000/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$HEALTH_USERNAME\",\"password\":\"$HEALTH_PASSWORD\"}" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin).get("token",""))')

curl -fsS -X POST "http://localhost:3000/api/agent/chat" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{"message":"今天天气怎么样","session_id":"gap-test","turn_id":1,"client_message_id":"gt-1"}' \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print("answer_kind:", d.get("answer_kind"))'
```

Expected: `answer_kind: guidance`

- [ ] **查询能力盲区 API，确认刚才的记录出现**

```bash
curl -fsS "http://localhost:3000/api/developer/agent/query-logs?query_type=guidance&page=1" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print("total:", d.get("total")); [print(" -", r.get("request_text"), "|", r.get("fallback_reason")) for r in d.get("rows", [])]'
```

Expected: total >= 1，显示"今天天气怎么样 | safe_hint"

- [ ] **浏览器打开能力盲区页**

访问 `http://localhost:3000/capability-gaps`，用 admin 账号登录后看到上述记录。

- [ ] **最终 deploy**

按照 `/deploy` skill 完整走一遍（bump version、build、restart、smoke test）。
