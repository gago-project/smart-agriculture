# Chat Visual Refresh Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refresh the chat workspace visual hierarchy without changing the existing chat behavior or APIs.

**Architecture:** Keep all data flow and chat actions intact. Limit changes to `App.tsx`, chat workspace components, and `globals.css`, with lightweight contract tests guarding the new layout structure.

**Tech Stack:** Next.js app router workspace UI, React components, global CSS, Node contract tests.

---

### Task 1: Lock the new visual hierarchy contract

**Files:**
- Modify: `apps/web/tests/file-contract.test.mjs`

**Step 1:** Add a failing contract test for the refined title hierarchy and composer guidance classes.

**Step 2:** Run `node --test apps/web/tests/file-contract.test.mjs` and confirm the new test fails for missing class names.

### Task 2: Refresh workspace structure

**Files:**
- Modify: `apps/web/workspace/App.tsx`
- Modify: `apps/web/workspace/components/Composer.tsx`

**Step 1:** Add explicit header hierarchy wrappers and subtitle copy in the chat workspace.

**Step 2:** Add named composer guidance elements while keeping the compact textarea behavior unchanged.

### Task 3: Refresh chat workspace styling

**Files:**
- Modify: `apps/web/app/globals.css`

**Step 1:** Rebalance the workspace shell, sidebar weight, and main panel atmosphere.

**Step 2:** Tighten message bubble proportions and spacing.

**Step 3:** Refine the composer, buttons, and helper copy styling while keeping the mobile fallback intact.

### Task 4: Verify

**Files:**
- No code changes expected

**Step 1:** Re-run `node --test apps/web/tests/file-contract.test.mjs`.

**Step 2:** Run at least one broader frontend contract check if the targeted test passes.

**Step 3:** Inspect the local chat page visually if a local browser session is available.
