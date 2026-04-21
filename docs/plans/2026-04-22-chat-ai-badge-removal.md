# Chat AI Badge Removal Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 移除聊天对话区 AI 回复中的“AI参与度”标签展示，同时保持现有消息元数据与右侧隐藏分析面板相关结构不变。

**Architecture:** 仅调整 `ChatPanel` 的渲染逻辑，不修改接口返回、store、消息结构或 `EvidencePanel`。先用源码合约测试锁定聊天区不再渲染该标签，再做最小 UI 删除，最后运行定向验证。

**Tech Stack:** Next.js、React、TypeScript、Node test、Markdown plans

---

### Task 1: 写失败测试

**Files:**
- Modify: `apps/web/tests/file-contract.test.mjs`

**Step 1: 添加聊天区合约测试**

- 断言 `apps/web/workspace/components/ChatPanel.tsx` 不再包含 `AI参与度`
- 断言 `ChatPanel` 不再直接读取 `ai_involvement`

**Step 2: 运行测试确认失败**

Run: `npm --prefix apps/web test -- --test-name-pattern "chat panel no longer renders AI involvement badge in message list"`
Expected: FAIL，且失败原因是 `ChatPanel.tsx` 仍包含旧展示逻辑

### Task 2: 删除聊天区标签渲染

**Files:**
- Modify: `apps/web/workspace/components/ChatPanel.tsx`

**Step 1: 移除消息列表中的 badge 渲染**

- 删除 `assistant` 消息顶部 `AI参与度` 的 header/badge
- 删除仅为该 badge 服务的局部变量

**Step 2: 保持其他行为不变**

- 不改重试按钮逻辑
- 不改消息内容渲染
- 不改消息 `meta` 数据结构

### Task 3: 验证

**Files:**
- Modify: 无

**Step 1: 重新运行定向测试**

Run: `npm --prefix apps/web test -- --test-name-pattern "chat panel no longer renders AI involvement badge in message list"`
Expected: PASS

**Step 2: 运行 Web 合约测试**

Run: `npm --prefix apps/web test`
Expected: PASS
