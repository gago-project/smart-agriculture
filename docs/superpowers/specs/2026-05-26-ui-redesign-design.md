# UI 全面优化设计方案

**日期：** 2026-05-26
**范围：** `apps/web/app/globals.css` 纯视觉改写，不改 TSX 业务逻辑
**目标：** 白底、简洁、企业级 SaaS 风格，气质接近 ChatGPT 网页端

---

## 一、当前问题

| 问题 | 表现 |
|------|------|
| 背景装饰过重 | body/sidebar/main 均有绿色径向渐变，视觉噪音大 |
| 圆角过大 | `.sidebar`、`.main` 使用 `border-radius: 28px`，偏向 iOS App 风格 |
| 阴影偏重 | `box-shadow: 0 18px 42px rgba(15,23,42,0.08)` 在白底上显厚重 |
| 按钮渐变 | 主按钮、提交按钮均用 `linear-gradient`，不够克制 |
| 布局有外框 | `.layout` 有 `padding: 18px` + `gap: 18px`，形成「框中框」观感 |
| 会话卡片过重 | 每个 session-item 有边框 + 渐变背景 + 阴影，堆叠感强 |

---

## 二、设计决策

### 2.1 方案选择

采用 **方案 A：纯 CSS 改写**。保持所有 class 名和 TSX 文件不变，仅重写 `globals.css` 视觉样式。风险最低，改动集中，便于整体 review。

### 2.2 布局结构

从「浮动卡片」改为「全屏贴边」：

- 移除 `.layout` 的 `padding` 和 `gap`，sidebar + main 铺满 `100vh`
- Sidebar 固定宽 `260px`，右侧 `1px solid #e5e7eb` 细线分隔
- Body 背景改为纯白 `#ffffff`，不再使用任何渐变

### 2.3 颜色系统

| Token | 旧值 | 新值 | 用途 |
|-------|------|------|------|
| `--bg` | `#eef4f0` | `#ffffff` | 页面背景 |
| `--panel` | `#ffffff` | `#ffffff` | 面板背景 |
| `--panel-soft` | `#f5f8f6` | `#f9fafb` | 次级背景（sidebar） |
| `--border` | `rgba(15,23,42,0.07)` | `#e5e7eb` | 统一边框色 |
| `--muted` | `#667085` | `#6b7280` | 辅助文字 |
| `--accent` | `#159a74` | `#10a37f` | 品牌强调色（保留绿色） |
| `--shadow` | `0 18px 42px rgba(…)` | `0 1px 3px rgba(0,0,0,0.06)` | 极轻阴影 |

### 2.4 圆角规范

| 元素 | 旧值 | 新值 |
|------|------|------|
| 侧边栏、主面板 | `28px` | `0`（贴边） |
| 卡片、按钮 | `16px` | `8px` |
| 输入框 | `12-18px` | `8px` |
| 消息气泡 | `20px` | `14px` |
| 下拉菜单 | `16px` | `8px` |
| Badge / Pill | `999px` | `6px` |

### 2.5 按钮规范

| 类型 | 样式 |
|------|------|
| 主按钮（发送、新建） | `background: #111827`，白色文字，无渐变 |
| 品牌按钮（录音停止） | `background: #10a37f` |
| 次级按钮 | 白底 `#ffffff`，`border: 1px solid #e5e7eb` |
| 危险按钮 | `color: #dc2626`，白底或透明底 |
| 禁用状态 | `opacity: 0.4` |

### 2.6 各区域详细设计

**Sidebar**
- 背景 `#f9fafb`，无渐变
- 品牌区：字号适当，版本号用 `#9ca3af`
- 新建会话按钮：`#111827` 实色，`border-radius: 8px`，无阴影
- 搜索框：白底、细边框、`border-radius: 8px`
- 会话列表项：无边框无阴影，hover 时 `background: #f3f4f6`，active 时 `background: #eff6ff`（或品牌浅色 `rgba(16,163,127,0.08)`）
- 去掉 session-item 的 `transform: translateY(-1px)` 动效

**主内容区（Main）**
- 背景 `#ffffff`，无渐变
- Header：左标题右菜单，`padding: 16px 24px`，底部 `1px solid #e5e7eb` 分隔线
- 消息列表：最大宽度 `768px` 水平居中，上下 padding 充足
- User 消息：`background: #f3f4f6`，`border-radius: 14px`，无边框
- Assistant 消息：无背景，直接显示文字，去掉边框和阴影
- Avatar：简化，`width: 28px`，字体更小

**Composer**
- 整体 `background: #ffffff`，`border: 1px solid #e5e7eb`，`border-radius: 12px`
- Textarea：无额外边框，focus 时外层容器边框变为 `#10a37f`
- 发送按钮：`#111827` 实色
- 语音按钮：次级样式，录音中变红

**Admin 页面**
- 表格：header 行 `background: #f9fafb`，行 hover `background: #f9fafb`
- 按钮统一为新规范（`border-radius: 8px`，无渐变）
- 状态 badge 保留颜色语义，但用 `border-radius: 6px` 替代胶囊形

---

## 三、不改动的内容

- 所有 TSX 组件（业务逻辑、props、事件处理）
- 响应式断点逻辑（只调整断点内的视觉值）
- 功能性样式（overflow、grid 结构、display 等布局属性）
- 品牌色系（保留绿色 `#10a37f` 作为强调色）

---

## 四、实现范围

单文件改写：`apps/web/app/globals.css`

分区执行顺序：
1. CSS 变量（`:root`）
2. Body / Layout 背景和结构
3. Sidebar（品牌、按钮、搜索、会话列表）
4. Main（Header、消息区、气泡、Composer）
5. Admin 页面（表格、按钮、卡片）
6. 响应式媒体查询调整

---

## 五、验收标准

- 第一眼干净、白底、专业
- 无绿色渐变背景
- 圆角统一不超过 `14px`（气泡除外）
- 按钮无渐变，风格统一
- 移动端不横向溢出
- 所有功能正常（登录、聊天、admin 操作）
