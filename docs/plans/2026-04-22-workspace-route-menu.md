# 工作台路由化下拉菜单 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将工作台顶部的横向入口改成下拉菜单，并把问答、墒情管理、查询日志切换改为真实路由与明确的前端权限守卫。

**Architecture:** 保留现有登录态与业务页面组件不变，把 `apps/web/workspace/App.tsx` 从 `workspaceView` 本地切页改为基于 `pathname` 的路由壳层。新增 `/query-logs` 页面文件与一个独立的用户菜单组件，在壳层中统一处理登录态、根路径跳转、权限不足回退和菜单导航。

**Tech Stack:** Next.js 16 App Router、React 19、TypeScript、Zustand、`node:test`

---

### Task 1: 锁定真实路由与路由壳层契约

**Files:**
- Modify: `apps/web/tests/file-contract.test.mjs`
- Create: `apps/web/app/query-logs/page.tsx`
- Modify: `apps/web/workspace/App.tsx`

**Step 1: Write the failing test**

在 `apps/web/tests/file-contract.test.mjs` 新增 / 调整契约测试，先锁定“必须有独立查询日志路由”和“App 不再依赖 `workspaceView` 本地切页”：

```javascript
test('web has route files for chat admin and query logs', () => {
  assert.equal(existsSync(new URL('../app/chat/page.tsx', import.meta.url)), true);
  assert.equal(existsSync(new URL('../app/admin/page.tsx', import.meta.url)), true);
  assert.equal(existsSync(new URL('../app/query-logs/page.tsx', import.meta.url)), true);
});

test('workspace app uses route state instead of local workspaceView state', () => {
  const appSource = readFileSync(new URL('../workspace/App.tsx', import.meta.url), 'utf8');

  assert.match(appSource, /usePathname/);
  assert.match(appSource, /useRouter/);
  assert.doesNotMatch(appSource, /workspaceView/);
});
```

**Step 2: Run test to verify it fails**

Run: `node --test apps/web/tests/file-contract.test.mjs --test-name-pattern="route files|route state"`

Expected: FAIL because `apps/web/app/query-logs/page.tsx` does not exist and `App.tsx` still contains `workspaceView`.

**Step 3: Write minimal implementation**

1. 新建 `apps/web/app/query-logs/page.tsx`
2. 在 `apps/web/workspace/App.tsx` 中先接入：
   - `usePathname`
   - `useRouter`
   - 一个基于路径的 `currentView`
3. 删除 `workspaceView` 本地状态及对应切换 `useEffect`

最小页面文件可以先保持和现有页面一致：

```typescript
import WorkspaceApp from '../../workspace/App';

export default function QueryLogsPage() {
  return <WorkspaceApp />;
}
```

`App.tsx` 的最小路由判断可先写成：

```typescript
const pathname = usePathname();
const currentView =
  pathname === '/admin' ? 'soil-admin' :
  pathname === '/query-logs' ? 'agent-logs' :
  'chat';
```

**Step 4: Run test to verify it passes**

Run: `node --test apps/web/tests/file-contract.test.mjs --test-name-pattern="route files|route state"`

Expected: PASS

**Step 5: Commit**

```bash
git add apps/web/tests/file-contract.test.mjs apps/web/app/query-logs/page.tsx apps/web/workspace/App.tsx
git commit -m "test: lock workspace route-based navigation contract"
```

### Task 2: 实现根路由跳转与主要路由权限守卫

**Files:**
- Modify: `apps/web/workspace/App.tsx`
- Modify: `apps/web/app/page.tsx`
- Modify: `apps/web/app/chat/page.tsx`
- Modify: `apps/web/app/admin/page.tsx`
- Modify: `apps/web/app/query-logs/page.tsx`
- Test: `apps/web/tests/file-contract.test.mjs`

**Step 1: Write the failing test**

在 `apps/web/tests/file-contract.test.mjs` 增加权限和跳转契约，先描述目标行为：

```javascript
test('workspace app redirects authenticated root users to chat', () => {
  const appSource = readFileSync(new URL('../workspace/App.tsx', import.meta.url), 'utf8');

  assert.match(appSource, /pathname === '\\/'/);
  assert.match(appSource, /router\\.replace\\('\\/chat'\\)/);
});

test('workspace app keeps route permission boundaries in one place', () => {
  const appSource = readFileSync(new URL('../workspace/App.tsx', import.meta.url), 'utf8');

  assert.match(appSource, /canManageSoilAdmin/);
  assert.match(appSource, /canViewAgentLogs/);
  assert.match(appSource, /pathname === '\\/admin'/);
  assert.match(appSource, /pathname === '\\/query-logs'/);
  assert.match(appSource, /router\\.replace\\('\\/chat'\\)/);
});
```

**Step 2: Run test to verify it fails**

Run: `node --test apps/web/tests/file-contract.test.mjs --test-name-pattern="authenticated root users|permission boundaries"`

Expected: FAIL because `App.tsx` has no route redirects yet.

**Step 3: Write minimal implementation**

在 `apps/web/workspace/App.tsx` 中新增基于 `pathname + role` 的守卫逻辑：

```typescript
useEffect(() => {
  if (authStatus !== 'authenticated' || !authUser) return;
  if (pathname === '/') {
    router.replace('/chat');
    return;
  }
  if (pathname === '/admin' && !canManageSoilAdmin) {
    router.replace('/chat');
    return;
  }
  if (pathname === '/query-logs' && !canViewAgentLogs) {
    router.replace('/chat');
  }
}, [authStatus, authUser, pathname, router, canManageSoilAdmin, canViewAgentLogs]);
```

页面文件继续保持简单壳层入口，避免把权限散落到多个页面里：

```typescript
import WorkspaceApp from '../../workspace/App';

export default function AdminPage() {
  return <WorkspaceApp />;
}
```

**Step 4: Run test to verify it passes**

Run: `node --test apps/web/tests/file-contract.test.mjs --test-name-pattern="authenticated root users|permission boundaries"`

Expected: PASS

**Step 5: Commit**

```bash
git add apps/web/workspace/App.tsx apps/web/app/page.tsx apps/web/app/chat/page.tsx apps/web/app/admin/page.tsx apps/web/app/query-logs/page.tsx apps/web/tests/file-contract.test.mjs
git commit -m "feat: add route guards for workspace pages"
```

### Task 3: 锁定头部下拉菜单契约

**Files:**
- Create: `apps/web/workspace/components/WorkspaceUserMenu.tsx`
- Modify: `apps/web/tests/file-contract.test.mjs`
- Modify: `apps/web/workspace/App.tsx`

**Step 1: Write the failing test**

为菜单结构写契约测试，确保不再回到横向罗列按钮：

```javascript
test('workspace header uses a dedicated user menu instead of nav buttons row', () => {
  const appSource = readFileSync(new URL('../workspace/App.tsx', import.meta.url), 'utf8');

  assert.match(appSource, /WorkspaceUserMenu/);
  assert.doesNotMatch(appSource, /workspace-nav-button/);
});

test('workspace user menu contains route items username and logout entry', () => {
  const menuSource = readFileSync(new URL('../workspace/components/WorkspaceUserMenu.tsx', import.meta.url), 'utf8');

  assert.match(menuSource, /墒情管理/);
  assert.match(menuSource, /查询日志/);
  assert.match(menuSource, /用户名/);
  assert.match(menuSource, /退出登录/);
  assert.match(menuSource, /router\\.push/);
});
```

**Step 2: Run test to verify it fails**

Run: `node --test apps/web/tests/file-contract.test.mjs --test-name-pattern="dedicated user menu|route items username and logout"`

Expected: FAIL because `WorkspaceUserMenu.tsx` does not exist and `App.tsx` still renders old header buttons.

**Step 3: Write minimal implementation**

新建 `apps/web/workspace/components/WorkspaceUserMenu.tsx`，收拢头部入口：

```typescript
interface WorkspaceUserMenuProps {
  username: string;
  currentPath: string;
  canManageSoilAdmin: boolean;
  canViewAgentLogs: boolean;
  onLogout: () => Promise<void>;
}
```

组件内最小结构：

```tsx
<button type="button" className="workspace-menu-trigger">工作台菜单</button>
<div className="workspace-menu" role="menu">
  {canManageSoilAdmin ? <button role="menuitem" onClick={() => router.push('/admin')}>墒情管理</button> : null}
  {canViewAgentLogs ? <button role="menuitem" onClick={() => router.push('/query-logs')}>查询日志</button> : null}
  <div className="workspace-menu-user">用户名：{username}</div>
  <button role="menuitem" onClick={() => void onLogout()}>退出登录</button>
</div>
```

并在 `App.tsx` 中替换旧的右上角按钮区。

**Step 4: Run test to verify it passes**

Run: `node --test apps/web/tests/file-contract.test.mjs --test-name-pattern="dedicated user menu|route items username and logout"`

Expected: PASS

**Step 5: Commit**

```bash
git add apps/web/workspace/components/WorkspaceUserMenu.tsx apps/web/workspace/App.tsx apps/web/tests/file-contract.test.mjs
git commit -m "feat: replace workspace header actions with dropdown menu"
```

### Task 4: 完成菜单交互、当前项保护与样式接入

**Files:**
- Modify: `apps/web/workspace/components/WorkspaceUserMenu.tsx`
- Modify: `apps/web/app/globals.css`
- Modify: `apps/web/workspace/App.tsx`
- Test: `apps/web/tests/file-contract.test.mjs`

**Step 1: Write the failing test**

继续把交互和样式约束住：

```javascript
test('workspace user menu avoids redundant current-route navigation', () => {
  const menuSource = readFileSync(new URL('../workspace/components/WorkspaceUserMenu.tsx', import.meta.url), 'utf8');

  assert.match(menuSource, /currentPath/);
  assert.match(menuSource, /targetPath !== currentPath/);
});

test('globals include workspace dropdown menu styles', () => {
  const cssSource = readFileSync(new URL('../app/globals.css', import.meta.url), 'utf8');

  assert.match(cssSource, /\\.workspace-menu-trigger/);
  assert.match(cssSource, /\\.workspace-menu-panel/);
  assert.match(cssSource, /\\.workspace-menu-item/);
});
```

**Step 2: Run test to verify it fails**

Run: `node --test apps/web/tests/file-contract.test.mjs --test-name-pattern="redundant current-route navigation|dropdown menu styles"`

Expected: FAIL because the minimal menu implementation has not added current-route guards or final CSS class names yet.

**Step 3: Write minimal implementation**

在 `WorkspaceUserMenu.tsx` 中：

- 用本地状态控制展开 / 收起
- 统一走 `handleNavigate(targetPath)`
- 当前页面点击时只关闭菜单，不重复 `router.push`

最小逻辑示例：

```typescript
function handleNavigate(targetPath: string) {
  setOpen(false);
  if (targetPath !== currentPath) {
    router.push(targetPath);
  }
}
```

在 `apps/web/app/globals.css` 中新增菜单样式：

```css
.workspace-menu-root { position: relative; }
.workspace-menu-trigger { ... }
.workspace-menu-panel { ... }
.workspace-menu-item { ... }
.workspace-menu-item.meta { ... }
.workspace-menu-item.danger { ... }
```

并在 `App.tsx` 中给组件传入 `currentPath={pathname}`。

**Step 4: Run test to verify it passes**

Run: `node --test apps/web/tests/file-contract.test.mjs --test-name-pattern="redundant current-route navigation|dropdown menu styles"`

Expected: PASS

**Step 5: Commit**

```bash
git add apps/web/workspace/components/WorkspaceUserMenu.tsx apps/web/app/globals.css apps/web/workspace/App.tsx apps/web/tests/file-contract.test.mjs
git commit -m "feat: add workspace dropdown interactions and styles"
```

### Task 5: 全量验证并清理契约

**Files:**
- Modify: `apps/web/tests/file-contract.test.mjs`
- Verify: `apps/web/package.json`

**Step 1: Write the failing test**

若前面为快速落地留下了旧断言或旧命名，这一步统一收敛：

```javascript
test('workspace no longer toggles pages with workspaceView buttons', () => {
  const appSource = readFileSync(new URL('../workspace/App.tsx', import.meta.url), 'utf8');

  assert.doesNotMatch(appSource, /workspaceView/);
  assert.doesNotMatch(appSource, /返回问答/);
});
```

**Step 2: Run test to verify it fails**

Run: `node --test apps/web/tests/file-contract.test.mjs --test-name-pattern="workspace no longer toggles pages"`

Expected: FAIL if any旧切页文案或状态残留。

**Step 3: Write minimal implementation**

- 删除剩余 `workspaceView` 相关代码
- 删除旧 header toggle 文案与无用 class
- 保留 `workspace-nav-button` CSS 仅在确认无引用后再删，避免误伤；若已无引用，再一并移除

**Step 4: Run test to verify it passes**

Run: `node --test apps/web/tests/file-contract.test.mjs --test-name-pattern="workspace no longer toggles pages"`

Expected: PASS

**Step 5: Commit**

```bash
git add apps/web/workspace/App.tsx apps/web/tests/file-contract.test.mjs apps/web/app/globals.css
git commit -m "refactor: remove legacy workspace view toggles"
```

### Task 6: 运行完整 Web 测试验证

**Files:**
- Verify: `apps/web/tests/file-contract.test.mjs`
- Verify: `apps/web/tests/auth-contract.test.mjs`
- Verify: `apps/web/tests/*.test.mjs`

**Step 1: Run focused contract tests**

Run: `node --test apps/web/tests/file-contract.test.mjs`

Expected: PASS

**Step 2: Run auth and route-related tests**

Run: `node --test apps/web/tests/auth-contract.test.mjs apps/web/tests/file-contract.test.mjs`

Expected: PASS

**Step 3: Run the full web test suite**

Run: `npm --prefix apps/web test`

Expected: PASS with 0 failures

**Step 4: Review diff manually**

Run: `git diff -- apps/web/app apps/web/workspace apps/web/tests docs/plans`

Expected: Only route/menu-related changes appear

**Step 5: Commit**

```bash
git add apps/web/app apps/web/workspace apps/web/tests
git commit -m "feat: route workspace navigation through dropdown menu"
```
