# UI 全面优化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Smart Agriculture MVP 的整体 UI 从「绿色渐变卡片风」改造为「白底全屏贴边企业级 SaaS 风」，气质接近 ChatGPT 网页端。

**Architecture:** 纯 CSS 改写，不触碰任何 TSX 文件和业务逻辑。所有改动集中在 `apps/web/app/globals.css` 一个文件，按区域分批次修改并提交。

**Tech Stack:** Next.js 19, React 19, 纯手写 CSS（无 Tailwind / 组件库）

---

## 文件映射

| 文件 | 操作 |
|------|------|
| `apps/web/app/globals.css` | 分 9 个任务逐区修改 |

---

## Task 1：CSS 变量 + Body 背景

**Files:**
- Modify: `apps/web/app/globals.css:1-34`

- [ ] **Step 1：替换 `:root` 设计 token**

将文件第 1–16 行替换为：

```css
:root {
  --bg: #ffffff;
  --bg-elevated: #ffffff;
  --panel: #ffffff;
  --panel-soft: #f9fafb;
  --panel-strong: rgba(0, 0, 0, 0.04);
  --panel-hover: rgba(0, 0, 0, 0.02);
  --text: #111827;
  --muted: #6b7280;
  --accent: #10a37f;
  --accent-soft: rgba(16, 163, 127, 0.1);
  --user-bubble: #f3f4f6;
  --assistant-bubble: transparent;
  --border: #e5e7eb;
  --shadow: 0 1px 3px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04);
}
```

- [ ] **Step 2：替换 body 背景**

将文件第 22–34 行（`html, body, #root` 块）替换为：

```css
html,
body,
#root {
  margin: 0;
  height: 100%;
  font-family: 'Avenir Next', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
  background: #ffffff;
  color: var(--text);
  overflow: hidden;
}
```

- [ ] **Step 3：启动开发服务（若未运行）**

```bash
# 确认 web 已在 localhost:3000 运行
curl -fsS http://localhost:3000/api/health | python3 -m json.tool
```

- [ ] **Step 4：打开浏览器确认**

访问 `http://localhost:3000`，确认：页面背景变为白色，不再有绿色径向渐变。

- [ ] **Step 5：提交**

```bash
git add apps/web/app/globals.css
git commit -m "style: clean up CSS tokens and remove body gradient"
```

---

## Task 2：登录页（Auth）

**Files:**
- Modify: `apps/web/app/globals.css`（`.auth-*` 选择器区域，约第 36–133 行）

- [ ] **Step 1：替换登录页 CSS**

将以下 `.auth-*` 所有规则整块替换：

```css
.auth-shell {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background: #f9fafb;
}

.auth-card {
  width: min(100%, 400px);
  padding: 32px;
  border-radius: 12px;
  background: #ffffff;
  border: 1px solid var(--border);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
  display: grid;
  gap: 16px;
}

.auth-loading {
  text-align: center;
  color: var(--muted);
  font-size: 14px;
}

.auth-brand {
  color: var(--accent);
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.auth-title {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  color: var(--text);
}

.auth-subtitle {
  margin: 0;
  color: var(--muted);
  font-size: 14px;
}

.auth-form {
  display: grid;
  gap: 14px;
}

.auth-field {
  display: grid;
  gap: 6px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
}

.auth-field input {
  width: 100%;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: #ffffff;
  font: inherit;
  font-size: 14px;
  color: var(--text);
  outline: none;
  transition: border-color 0.15s;
}

.auth-field input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(16, 163, 127, 0.08);
}

.auth-password-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
}

.auth-password-toggle {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px;
  background: #ffffff;
  font: inherit;
  font-size: 13px;
  line-height: 1;
  color: var(--muted);
  cursor: pointer;
}

.auth-password-toggle:hover {
  border-color: #d1d5db;
  color: var(--text);
}

.auth-error {
  padding: 10px 12px;
  border-radius: 8px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #dc2626;
  font-size: 13px;
}

.auth-submit {
  border: 0;
  border-radius: 8px;
  padding: 11px 16px;
  background: #111827;
  color: #ffffff;
  font: inherit;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}

.auth-submit:hover {
  background: #1f2937;
}

.auth-submit:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
```

- [ ] **Step 2：浏览器验证登录页**

访问 `http://localhost:3000`（未登录时显示登录页），确认：
- 背景浅灰 `#f9fafb`
- 白色卡片，轻阴影，`border-radius: 12px`
- 登录按钮深色实色，无渐变

- [ ] **Step 3：提交**

```bash
git add apps/web/app/globals.css
git commit -m "style: redesign auth/login page to clean enterprise style"
```

---

## Task 3：Layout + Sidebar 结构

**Files:**
- Modify: `apps/web/app/globals.css`（`.layout`、`.sidebar`、`.main` 区域，约第 135–161 行）

- [ ] **Step 1：替换 Layout + Sidebar + Main 结构规则**

将 `.layout`、`.sidebar,.main`、`.sidebar`、`.main` 四个规则块整块替换：

```css
.layout {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  height: 100vh;
  overflow: hidden;
}

.sidebar {
  padding: 16px 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: var(--panel-soft);
  border-right: 1px solid var(--border);
  min-height: 0;
}

.main {
  display: grid;
  grid-template-rows: auto 1fr auto;
  background: #ffffff;
  min-height: 0;
  overflow: hidden;
}
```

注意：删掉原来的 `.sidebar, .main { … }` 联合规则，以及 `.sidebar` 里的渐变背景和圆角。

- [ ] **Step 2：浏览器验证布局**

登录后访问 `/chat`，确认：
- Sidebar 左侧贴边，浅灰背景，右侧细线分隔
- Main 区域铺满右侧，白色背景
- 不再有 18px 外框和圆角

- [ ] **Step 3：提交**

```bash
git add apps/web/app/globals.css
git commit -m "style: switch to full-bleed layout, remove card frame"
```

---

## Task 4：Sidebar 内部组件

**Files:**
- Modify: `apps/web/app/globals.css`（`.sidebar-brand`、`.new-chat`、`.sidebar-search`、`.session-*` 区域，约第 163–500 行）

- [ ] **Step 1：替换 sidebar 品牌区、新建按钮、搜索框**

```css
.sidebar-brand {
  padding: 4px 4px 14px;
}

.sidebar-brand-copy {
  display: grid;
  gap: 4px;
}

.sidebar-brand-copy strong {
  font-size: 14px;
  font-weight: 700;
  line-height: 1.3;
  color: var(--text);
}

.sidebar-brand p {
  margin: 0;
  color: var(--muted);
  font-size: 12px;
}

.sidebar-version {
  margin-left: 6px;
  font-size: 11px;
  font-weight: 400;
  color: #9ca3af;
}

.new-chat {
  width: 100%;
  border: 0;
  border-radius: 8px;
  padding: 10px 14px;
  background: #111827;
  color: #ffffff;
  font: inherit;
  font-size: 14px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  cursor: pointer;
  transition: background 0.15s;
}

.new-chat:hover {
  background: #1f2937;
}

.new-chat-icon {
  width: 20px;
  height: 20px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.15);
  font-size: 14px;
  line-height: 1;
}

.sidebar-search {
  margin-top: 10px;
}

.sidebar-search-input {
  width: 100%;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px 10px;
  background: #ffffff;
  font: inherit;
  font-size: 13px;
  color: var(--text);
  outline: none;
  transition: border-color 0.15s;
}

.sidebar-search-input::placeholder {
  color: #9ca3af;
}

.sidebar-search-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(16, 163, 127, 0.08);
}

.sidebar-search-input::-webkit-search-cancel-button {
  cursor: pointer;
}

.sidebar-section-title {
  margin: 16px 4px 8px;
  color: #9ca3af;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
```

- [ ] **Step 2：替换搜索结果样式**

```css
.search-result-item {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px 10px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition: background 0.12s;
}

.search-result-item:hover {
  background: #f3f4f6;
}

.search-result-item.active {
  background: rgba(16, 163, 127, 0.08);
}

.search-result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.search-result-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1 1 0;
  min-width: 0;
}

.search-result-tag {
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 600;
  color: var(--accent);
  background: var(--accent-soft);
  border-radius: 4px;
  padding: 1px 5px;
}

.search-result-snippet {
  margin: 0;
  font-size: 12px;
  color: var(--muted);
  line-height: 1.5;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.search-highlight {
  background: rgba(250, 204, 21, 0.35);
  color: inherit;
  border-radius: 2px;
  padding: 0 1px;
}
```

- [ ] **Step 3：替换会话列表样式**

```css
.session-list {
  display: grid;
  align-content: start;
  gap: 2px;
  flex: 1 1 0;
  min-height: 0;
  overflow: auto;
  padding: 2px 0;
}

.session-empty {
  margin: 0;
  padding: 12px 10px;
  color: var(--muted);
  font-size: 13px;
}

.session-item {
  width: 100%;
  position: relative;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--text);
  transition: background 0.12s;
}

.session-item[data-menu-open='true'] {
  z-index: 5;
  background: #f3f4f6;
}

.session-item:hover {
  background: #f3f4f6;
}

.session-item-surface {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 4px;
  align-items: flex-start;
}

.session-item-main {
  border: 0;
  background: transparent;
  text-align: left;
  padding: 8px 10px;
  display: grid;
  gap: 4px;
  min-width: 0;
  cursor: pointer;
}

.session-item-title-row {
  min-width: 0;
}

.session-item-meta-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.session-item-title {
  display: block;
  font-size: 13px;
  line-height: 1.4;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-item-meta {
  color: var(--muted);
  font-size: 11px;
}

.session-item-status {
  flex-shrink: 0;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--accent-soft);
  color: var(--accent);
  font-size: 11px;
  font-weight: 600;
}

.session-item.active {
  background: rgba(16, 163, 127, 0.08);
}

.session-item.active .session-item-title {
  color: var(--accent);
  font-weight: 600;
}

.session-item-actions {
  display: flex;
  align-items: flex-start;
  justify-content: flex-end;
  position: relative;
  padding: 6px 6px 0 0;
}

.session-item-action {
  width: 28px;
  height: 28px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  line-height: 1;
  color: var(--muted);
  font-size: 16px;
  cursor: pointer;
  display: grid;
  place-items: center;
}

.session-item-action:hover {
  background: #e5e7eb;
  color: var(--text);
}

.session-item-menu {
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  min-width: 136px;
  margin: 0;
  padding: 4px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  display: grid;
  gap: 2px;
  z-index: 6;
}

.session-item-menu-action {
  border: 0;
  border-radius: 6px;
  padding: 8px 10px;
  background: transparent;
  text-align: left;
  font: inherit;
  font-size: 13px;
  color: var(--text);
  cursor: pointer;
}

.session-item-menu-action:hover {
  background: #f3f4f6;
}

.session-item-menu-action.danger {
  color: #dc2626;
}

.session-rename-input {
  width: 100%;
  border: 1px solid var(--accent);
  border-radius: 6px;
  padding: 6px 8px;
  font: inherit;
  font-size: 13px;
  background: #ffffff;
  outline: none;
  box-shadow: 0 0 0 3px rgba(16, 163, 127, 0.08);
}
```

- [ ] **Step 4：浏览器验证 Sidebar**

登录后确认：
- 新建按钮：深色实色，无渐变
- 会话列表项：无边框无阴影，hover 浅灰，active 浅绿色
- 搜索框白底细边框

- [ ] **Step 5：提交**

```bash
git add apps/web/app/globals.css
git commit -m "style: redesign sidebar components — clean list, dark new-chat button"
```

---

## Task 5：Main Header + 用户菜单

**Files:**
- Modify: `apps/web/app/globals.css`（`.workspace-*` 区域，约第 516–616 行）

- [ ] **Step 1：替换 workspace header 和用户菜单 CSS**

```css
.workspace-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid var(--border);
  background: #ffffff;
}

.workspace-title-group {
  display: grid;
  gap: 2px;
}

.workspace-title {
  margin: 0;
  font-size: 16px;
  line-height: 1.3;
  font-weight: 700;
  color: var(--text);
}

.workspace-version {
  margin-left: 8px;
  font-size: 12px;
  font-weight: 400;
  color: #9ca3af;
  vertical-align: middle;
}

.workspace-subtitle {
  margin: 0;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.5;
}

.workspace-menu-root {
  position: relative;
}

.workspace-menu-trigger {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px 12px;
  background: #ffffff;
  color: var(--text);
  font: inherit;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}

.workspace-menu-trigger:hover {
  background: #f9fafb;
  border-color: #d1d5db;
}

.workspace-menu-panel {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  min-width: 168px;
  padding: 4px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  display: grid;
  gap: 2px;
  z-index: 10;
}

.workspace-menu-item {
  width: 100%;
  border: 0;
  border-radius: 6px;
  padding: 8px 10px;
  background: transparent;
  color: var(--text);
  text-align: left;
  font: inherit;
  font-size: 13px;
  cursor: pointer;
}

.workspace-menu-item:hover {
  background: #f3f4f6;
}

.workspace-menu-item[aria-current='page'] {
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 600;
}

.workspace-menu-item-meta {
  color: var(--muted);
  font-size: 12px;
  cursor: default;
}

.workspace-menu-item-meta:hover {
  background: transparent;
}

.workspace-menu-item-danger {
  color: #dc2626;
}

.workspace-menu-item-danger:hover {
  background: #fef2f2;
}
```

- [ ] **Step 2：替换 chat-workspace 和 auto-run-banner**

```css
.chat-workspace {
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 0;
  overflow: hidden;
}

.chat-workspace.with-query-evidence {
  grid-template-columns: minmax(0, 1fr) 400px;
}

.chat-column {
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.chat-column > .chat-panel {
  flex: 1 1 0;
  min-height: 0;
}

.auto-run-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 24px;
  border-bottom: 1px solid var(--border);
  background: #f9fafb;
  font-size: 13px;
  color: var(--muted);
  flex-shrink: 0;
}

.auto-run-banner strong,
.auto-run-banner span,
.auto-run-banner p,
.auto-run-banner small {
  margin: 0;
}

.auto-run-banner--error {
  background: #fef2f2;
  border-bottom-color: #fecaca;
  color: #dc2626;
}

.auto-run-banner--done {
  background: #f0fdf4;
  border-bottom-color: #bbf7d0;
  color: #15803d;
}
```

- [ ] **Step 3：浏览器验证**

确认 Header 区域：标题字号收小、底部细分隔线、用户按钮无装饰

- [ ] **Step 4：提交**

```bash
git add apps/web/app/globals.css
git commit -m "style: clean up workspace header and user menu"
```

---

## Task 6：Chat Panel + 消息气泡 + 空状态

**Files:**
- Modify: `apps/web/app/globals.css`（`.chat-panel`、`.messages`、`.message-*`、`.empty-*`、`.suggestion-*` 区域）

- [ ] **Step 1：替换聊天面板和消息列表 CSS**

```css
.chat-panel {
  min-height: 0;
  overflow: hidden;
  display: grid;
  grid-template-rows: minmax(0, 1fr);
  background: #ffffff;
}

.chat-panel.empty {
  place-items: center;
  padding: 48px 24px 24px;
  text-align: left;
}

.empty-shell {
  width: min(100%, 640px);
  display: grid;
  gap: 20px;
}

.empty-shell h2 {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  line-height: 1.3;
  color: var(--text);
}

.suggestion-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.suggestion-card {
  display: grid;
  gap: 6px;
  padding: 14px 16px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: #ffffff;
  cursor: pointer;
  transition: background 0.12s, border-color 0.12s;
}

.suggestion-card:hover {
  background: #f9fafb;
  border-color: #d1d5db;
}

.suggestion-card strong {
  font-size: 13px;
  font-weight: 600;
  line-height: 1.4;
  color: var(--text);
}

.suggestion-card span {
  color: var(--muted);
  font-size: 12px;
  line-height: 1.5;
}

.messages {
  min-height: 0;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: 24px;
}

.message-row {
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr);
  gap: 12px;
  width: 100%;
  max-width: 768px;
  margin: 0 auto;
  padding: 8px 0;
}

.message-row.user {
  grid-template-columns: minmax(0, 1fr) 28px;
}

.message-row.user .message-avatar {
  order: 2;
}

.message-row.user .message {
  order: 1;
  margin-left: auto;
}

.message-avatar {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
  color: #6b7280;
  background: #f3f4f6;
  flex-shrink: 0;
}

.message-avatar.assistant {
  color: #ffffff;
  background: var(--accent);
}

.message-avatar.user {
  background: #f3f4f6;
  color: #374151;
}

.message {
  border-radius: 14px;
  padding: 12px 16px;
  max-width: min(680px, 100%);
  min-width: 0;
  overflow: hidden;
  background: transparent;
  border: 0;
  box-shadow: none;
}

.message.user {
  background: var(--user-bubble);
  max-width: min(520px, 100%);
  border-radius: 14px;
}

.message.assistant.selectable {
  cursor: pointer;
  transition: background 0.12s;
}

.message.assistant.selectable:hover,
.message.assistant.selectable:focus-visible {
  background: #f9fafb;
  outline: none;
}

.message.assistant.selected {
  background: rgba(16, 163, 127, 0.06);
  outline: none;
}

.message-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}

.message-header-badge-only {
  justify-content: flex-end;
}

.message-content {
  display: grid;
  gap: 8px;
  font-size: 14px;
}

.message-content-paragraph {
  margin: 0;
  line-height: 1.7;
  overflow-wrap: anywhere;
  color: var(--text);
}

.message-content-list {
  margin: 0;
  padding-left: 18px;
  display: grid;
  gap: 4px;
}

.message-content-list li {
  line-height: 1.7;
  overflow-wrap: anywhere;
  color: var(--text);
}
```

- [ ] **Step 2：浏览器验证聊天区域**

发一条消息，确认：
- User 消息：浅灰气泡，右侧
- Assistant 消息：无气泡背景，左侧，文字直接显示
- 消息列表最大宽度 768px，居中显示
- Avatar 变小（28px）

- [ ] **Step 3：提交**

```bash
git add apps/web/app/globals.css
git commit -m "style: clean message bubbles — assistant text-only, user light grey"
```

---

## Task 7：Composer 输入框

**Files:**
- Modify: `apps/web/app/globals.css`（`.composer-*`、`.voice-button`、`.retry` 区域）

- [ ] **Step 1：替换 Composer CSS**

```css
.composer-shell {
  display: grid;
  gap: 8px;
  padding: 12px 16px 14px;
  border-top: 1px solid var(--border);
  background: #ffffff;
}

.composer-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--muted);
  font-size: 12px;
  padding: 0 2px;
}

.composer-label {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  min-height: 22px;
  padding: 0 8px;
  border-radius: 4px;
  background: var(--accent-soft);
  color: var(--accent);
  font-size: 11px;
  font-weight: 600;
}

.composer-tip {
  color: #9ca3af;
  font-size: 12px;
}

.composer {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
  align-items: end;
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 4px 4px 4px 0;
  background: #ffffff;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.composer:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(16, 163, 127, 0.08);
}

.composer textarea {
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--text);
  padding: 10px 12px;
  min-height: 44px;
  max-height: 160px;
  resize: none;
  font: inherit;
  font-size: 14px;
  line-height: 1.55;
  outline: none;
}

.composer textarea:focus {
  outline: none;
  box-shadow: none;
  border-color: transparent;
}

.composer-actions {
  display: grid;
  grid-auto-flow: column;
  gap: 6px;
  align-items: end;
  padding-bottom: 4px;
  padding-right: 4px;
}

.composer button {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 0 14px;
  background: #ffffff;
  color: var(--text);
  font: inherit;
  font-size: 13px;
  font-weight: 500;
  min-width: 72px;
  min-height: 44px;
  cursor: pointer;
  transition: background 0.12s, border-color 0.12s;
  white-space: nowrap;
}

.composer button:hover {
  background: #f9fafb;
  border-color: #d1d5db;
}

.composer button:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.voice-button {
  background: #ffffff !important;
  color: var(--text) !important;
  min-width: 84px !important;
}

.voice-button.recording {
  background: #fef2f2 !important;
  border-color: #fecaca !important;
  color: #dc2626 !important;
}

.composer-submit {
  border-color: transparent !important;
  background: #111827 !important;
  color: #ffffff !important;
}

.composer-submit:hover {
  background: #1f2937 !important;
}

.composer-error {
  color: #dc2626;
  font-size: 13px;
  padding: 0 2px;
}

.retry {
  margin-top: 10px;
  border: 1px solid var(--border);
  background: #ffffff;
  color: var(--text);
  border-radius: 6px;
  padding: 6px 10px;
  font: inherit;
  font-size: 13px;
  cursor: pointer;
}

.retry:hover {
  background: #f9fafb;
}
```

- [ ] **Step 2：浏览器验证 Composer**

确认：
- Composer 整体是一个带细边框的容器，textarea 在内部
- focus 时容器边框变绿（而不是 textarea 本身变绿）
- 发送按钮深色实色，语音按钮白色次级样式
- 录音中语音按钮变红（浅红背景）

- [ ] **Step 3：提交**

```bash
git add apps/web/app/globals.css
git commit -m "style: redesign composer — contained textarea, solid send button"
```

---

## Task 8：数据块 + Turn Block + Admin 页面

**Files:**
- Modify: `apps/web/app/globals.css`（`.turn-block-*`、`.template-card-*`、`.ai-badge`、`.soil-admin-*`、`.admin-*` 区域）

- [ ] **Step 1：替换 turn-block 数据块样式**

```css
.turn-block-list {
  display: grid;
  gap: 10px;
  margin-top: 12px;
  min-width: 0;
}

.turn-block {
  display: grid;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: #f9fafb;
  min-width: 0;
}

.turn-block-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.turn-block-header strong {
  font-size: 13px;
  font-weight: 600;
}

.turn-block-header span {
  color: var(--muted);
  font-size: 12px;
  text-align: right;
}

.turn-block-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 8px;
}

.turn-block-metrics div {
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: #ffffff;
  font-size: 13px;
}

.turn-block-table-wrap {
  max-width: 100%;
  overflow-x: auto;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: #ffffff;
}

.turn-block-table {
  width: max-content;
  min-width: 100%;
  border-collapse: collapse;
}

.turn-block-table th,
.turn-block-table td {
  padding: 9px 12px;
  border-bottom: 1px solid var(--border);
  text-align: left;
  vertical-align: top;
  font-size: 13px;
  white-space: nowrap;
}

.turn-block-table th {
  background: #f9fafb;
  font-weight: 600;
  color: var(--text);
}

.turn-block-pagination {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.turn-block-pagination button {
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 5px 10px;
  background: #ffffff;
  color: var(--text);
  font: inherit;
  font-size: 13px;
  cursor: pointer;
}

.turn-block-pagination button:disabled {
  opacity: 0.35;
}

.turn-block-empty,
.turn-block-error {
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: #f9fafb;
  color: var(--muted);
  font-size: 13px;
}

.turn-block-error {
  border-color: #fecaca;
  background: #fef2f2;
  color: #dc2626;
}

.turn-block-pre {
  margin: 0;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: #f9fafb;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font-size: 13px;
}

.template-card {
  display: grid;
  gap: 12px;
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.template-card-meta {
  display: grid;
  gap: 4px;
}

.template-card-meta strong {
  font-size: 14px;
  font-weight: 600;
}

.template-card-note {
  color: #15803d;
  font-size: 12px;
  line-height: 1.5;
}

.template-card-preview {
  display: grid;
  gap: 10px;
  padding: 14px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: #ffffff;
}

.template-card-badge {
  width: fit-content;
  display: inline-flex;
  align-items: center;
  padding: 4px 8px;
  border-radius: 4px;
  background: var(--accent-soft);
  color: var(--accent);
  font-size: 12px;
  font-weight: 600;
}

.template-card-body {
  margin: 0;
  padding: 12px 14px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: #f9fafb;
  color: var(--text);
  font-size: 14px;
  line-height: 1.7;
  word-break: break-word;
}

.ai-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  border: 1px solid transparent;
}

.ai-高 {
  background: #eff6ff;
  color: #1d4ed8;
  border-color: #bfdbfe;
}

.ai-中 {
  background: var(--accent-soft);
  color: var(--accent);
}

.ai-低 {
  background: #f3f4f6;
  color: var(--muted);
}
```

- [ ] **Step 2：替换 Admin 页面样式**

```css
.soil-admin-page {
  min-height: 0;
  overflow: auto;
  padding: 24px;
  display: grid;
  gap: 16px;
  align-content: start;
}

.soil-admin-header,
.admin-table-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.soil-admin-header h2 {
  margin: 0 0 2px;
  font-size: 18px;
  font-weight: 700;
}

.soil-admin-header p {
  margin: 0;
  color: var(--muted);
  font-size: 13px;
}

.admin-card {
  border: 1px solid var(--border);
  border-radius: 10px;
  background: #ffffff;
  padding: 16px;
}

.upload-card,
.filter-card {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
  align-items: end;
}

.admin-card label {
  display: grid;
  gap: 5px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text);
}

.admin-card input,
.admin-card select,
.edit-inline input,
.edit-inline select {
  width: 100%;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px 10px;
  background: #ffffff;
  font: inherit;
  font-size: 13px;
  color: var(--text);
  outline: none;
  transition: border-color 0.15s;
}

.admin-card input:focus,
.admin-card select:focus,
.edit-inline input:focus,
.edit-inline select:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(16, 163, 127, 0.08);
}

.admin-card button,
.admin-table-toolbar button,
.edit-inline button,
.danger-outline {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px 12px;
  background: #ffffff;
  font: inherit;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.12s;
}

.admin-card button:hover,
.admin-table-toolbar button:hover,
.edit-inline button:hover {
  background: #f9fafb;
}

.danger-outline {
  color: #dc2626;
  border-color: #fecaca;
}

.danger-outline:hover {
  background: #fef2f2;
}

.admin-message {
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 13px;
}

.admin-message.success {
  color: #15803d;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
}

.admin-message.error {
  color: #dc2626;
  background: #fef2f2;
  border: 1px solid #fecaca;
}

.admin-table-wrap {
  overflow: auto;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: #ffffff;
}

.admin-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 1080px;
  font-size: 13px;
}

.admin-table th,
.admin-table td {
  border-bottom: 1px solid var(--border);
  padding: 10px 12px;
  text-align: left;
  vertical-align: top;
}

.admin-table th {
  position: sticky;
  top: 0;
  background: #f9fafb;
  z-index: 1;
  font-weight: 600;
  color: var(--text);
}

.admin-table tbody tr:hover {
  background: #f9fafb;
}

.admin-table tbody tr.selected {
  background: #eff6ff;
}

.soil-admin-layout {
  display: grid;
  gap: 16px;
}

.admin-card-title,
.admin-toolbar-actions,
.admin-progress-header,
.admin-selection-bar,
.admin-pagination-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.admin-card-title h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
}

.upload-panel {
  display: grid;
  gap: 14px;
}

.admin-progress-card {
  display: grid;
  gap: 8px;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: #f9fafb;
}

.admin-progress-card progress {
  width: 100%;
}

.admin-summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
  gap: 10px;
}

.admin-summary-item {
  border: 1px solid var(--border);
  border-radius: 8px;
  background: #ffffff;
  padding: 10px 12px;
  display: grid;
  gap: 4px;
}

.admin-summary-item span {
  font-size: 12px;
  color: var(--muted);
}

.admin-summary-item strong {
  font-size: 18px;
  font-weight: 700;
}

.admin-import-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.admin-diff-panel {
  display: grid;
  gap: 10px;
}

.admin-diff-toolbar {
  display: flex;
  gap: 8px;
}

.admin-diff-tag,
.admin-status-badge {
  display: inline-flex;
  align-items: center;
  border-radius: 4px;
  padding: 2px 8px;
  font-size: 12px;
  font-weight: 600;
  background: #eff6ff;
  color: #1d4ed8;
}

.admin-status-badge.is-previewing,
.admin-status-badge.is-applying {
  background: #fffbeb;
  color: #b45309;
}

.admin-status-badge.is-succeeded {
  background: #f0fdf4;
  color: #15803d;
}

.admin-status-badge.is-failed,
.admin-diff-tag.is-delete,
.admin-diff-tag.is-invalid {
  background: #fef2f2;
  color: #dc2626;
}

.admin-diff-tag.is-create {
  background: #f0fdf4;
  color: #15803d;
}

.admin-diff-tag.is-update {
  background: #fffbeb;
  color: #b45309;
}

.admin-diff-tag.is-unchanged {
  background: #f3f4f6;
  color: #6b7280;
}

.admin-inline-field {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 500;
}

.admin-inline-field input,
.admin-inline-field select {
  min-width: 84px;
}

.admin-selection-bar {
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: #f9fafb;
  font-size: 13px;
}

.admin-editable-cell {
  cursor: pointer;
}

.admin-editable-cell:hover {
  background: #eff6ff;
}

.admin-empty {
  text-align: center;
  color: var(--muted);
  padding: 24px;
  font-size: 13px;
}

.admin-modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.3);
  display: grid;
  place-items: center;
  padding: 24px;
  z-index: 40;
}

.admin-modal {
  width: min(520px, 100%);
  border-radius: 12px;
  background: #ffffff;
  border: 1px solid var(--border);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  padding: 20px;
  display: grid;
  gap: 16px;
}

.admin-modal-body {
  display: grid;
  gap: 10px;
}

.admin-modal-body p {
  margin: 0;
  font-size: 14px;
  color: var(--text);
}

.admin-modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.agent-log-detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}

.agent-log-detail-grid p {
  margin: 4px 0 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13px;
}

.agent-log-json-grid {
  margin-top: 12px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 12px;
}

.agent-log-json-grid pre {
  margin: 4px 0 0;
  padding: 10px;
  border-radius: 8px;
  background: #f9fafb;
  border: 1px solid var(--border);
  min-height: 140px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
}

.edit-inline {
  display: grid;
  grid-template-columns: 140px 160px auto;
  gap: 6px;
}

.error-tip {
  margin: 8px 24px;
  color: #dc2626;
  font-size: 13px;
}
```

- [ ] **Step 3：浏览器验证 Admin 和数据块**

访问 `/admin` 页面（需 admin 账号），确认：
- 表格白底，header 行浅灰
- 按钮无渐变，统一圆角
- Badge 用 `border-radius: 4px`，颜色语义正确

- [ ] **Step 4：提交**

```bash
git add apps/web/app/globals.css
git commit -m "style: redesign admin page, turn-blocks, and data display"
```

---

## Task 9：响应式调整 + Query Evidence Panel

**Files:**
- Modify: `apps/web/app/globals.css`（`@media` 区域 + `.query-evidence-*` 区域）

- [ ] **Step 1：替换 query evidence panel 样式**

```css
.query-evidence-panel {
  min-height: 0;
  overflow: auto;
  padding: 16px;
  border-left: 1px solid var(--border);
  background: #ffffff;
  display: grid;
  align-content: start;
  gap: 12px;
}

.query-evidence-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.query-evidence-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
}

.query-evidence-header p {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 12px;
}

.query-evidence-section {
  padding: 12px 14px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: #f9fafb;
  display: grid;
  gap: 10px;
}

.query-evidence-section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
}

.query-evidence-summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.query-evidence-summary-grid div {
  display: grid;
  gap: 4px;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: #ffffff;
}

.query-evidence-summary-grid dt {
  color: var(--muted);
  font-size: 11px;
}

.query-evidence-summary-grid dd {
  margin: 0;
  font-size: 13px;
  font-weight: 500;
}

.query-evidence-tab-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.query-evidence-tab {
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 5px 10px;
  background: #ffffff;
  color: var(--text);
  font: inherit;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.12s, border-color 0.12s;
}

.query-evidence-tab:hover {
  background: #f9fafb;
}

.query-evidence-tab.is-active {
  border-color: var(--accent);
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 600;
}

.query-evidence-warning {
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid #fde68a;
  background: #fffbeb;
  color: #b45309;
  font-size: 13px;
}

.query-evidence-empty {
  padding: 14px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: #f9fafb;
  color: var(--muted);
  font-size: 13px;
}

.query-evidence-empty.small {
  padding: 10px 12px;
}

.query-evidence-panel pre {
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
  background: #f9fafb;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 12px;
}

.query-evidence-table-wrap {
  overflow: auto;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: #ffffff;
}

.query-evidence-table {
  width: 100%;
  border-collapse: collapse;
}

.query-evidence-table th,
.query-evidence-table td {
  padding: 9px 12px;
  border-bottom: 1px solid var(--border);
  text-align: left;
  vertical-align: top;
  font-size: 13px;
}

.query-evidence-table th {
  background: #f9fafb;
  font-weight: 600;
}

.query-evidence-json summary {
  cursor: pointer;
  color: var(--muted);
  font-size: 13px;
}
```

- [ ] **Step 2：替换响应式媒体查询**

将 `@media (max-width: 1024px)` 块整块替换：

```css
@media (max-width: 1024px) {
  .layout {
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr;
    height: 100vh;
  }

  .sidebar {
    order: 2;
    border-right: 0;
    border-top: 1px solid var(--border);
    max-height: 40vh;
    overflow: auto;
  }

  .main {
    order: 1;
    min-height: 0;
  }

  .suggestion-grid {
    grid-template-columns: 1fr;
  }

  .workspace-title {
    font-size: 15px;
  }

  .workspace-subtitle {
    display: none;
  }

  .chat-workspace.with-query-evidence,
  .query-evidence-summary-grid {
    grid-template-columns: 1fr;
  }

  .message-row {
    grid-template-columns: 24px minmax(0, 1fr);
  }

  .message-row.user {
    grid-template-columns: minmax(0, 1fr) 24px;
  }

  .message-avatar {
    width: 24px;
    height: 24px;
  }

  .composer {
    grid-template-columns: 1fr;
    border-radius: 8px;
  }

  .composer-actions {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    grid-auto-flow: row;
    padding: 0 4px 4px;
  }

  .messages {
    padding: 16px;
  }
}
```

- [ ] **Step 3：全页面验证**

依次确认：
1. `/chat`：聊天界面整体干净，白底无渐变，消息居中，Composer 底部
2. `/admin`：表格、按钮、状态 badge 风格统一
3. 浏览器缩小到 900px 宽，移动端布局不横向溢出

- [ ] **Step 4：提交**

```bash
git add apps/web/app/globals.css
git commit -m "style: update responsive layout and query evidence panel"
```

---

## Task 10：构建验证 + 部署

**Files:**
- Run: `npm run build:web`

- [ ] **Step 1：生产构建**

```bash
npm run build:web 2>&1 | tail -20
```

预期：build 成功，无 CSS 报错

- [ ] **Step 2：按 deploy skill 重启服务并验活**

```bash
# 按 /deploy skill 流程操作：kill 旧进程 → restart → smoke test
```

- [ ] **Step 3：最终提交**

若 build 期间发现遗漏的样式问题，修复后追加提交：

```bash
git add apps/web/app/globals.css
git commit -m "style: fix post-build CSS issues"
```
