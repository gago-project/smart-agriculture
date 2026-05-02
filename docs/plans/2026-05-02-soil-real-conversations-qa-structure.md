# Soil Real Conversations QA Structure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a separate real-conversation QA corpus for soil-moisture so natural user questions can be accumulated, reviewed, and regression-tested without overloading the 56-case formal gate.

**Architecture:** Keep the existing 56-case formal acceptance library as the hard contract gate. Add a sibling real-conversations corpus with one file per sample, a shared schema, and a failure-regression bucket for newly discovered bugs. The corpus should be easy to read by humans and simple to automate later.

**Tech Stack:** Markdown docs, repository conventions, existing soil-moisture QA scripts/tests.

---

### Task 1: Define the corpus layout

**Files:**
- Create: `testdata/agent/soil-moisture/real-conversations/README.md`
- Create: `testdata/agent/soil-moisture/real-conversations/cases/README.md`
- Create: `testdata/agent/soil-moisture/real-conversations/regressions/README.md`

**Step 1: Write the structure docs**

Define the purpose, directory layout, and naming rules for real user questions and bug regressions.

**Step 2: Keep the formal gate separate**

State clearly that the 56-case formal library remains the hard gate and the new corpus is a growth dataset.

### Task 2: Define the field schema

**Files:**
- Create: `testdata/agent/soil-moisture/real-conversations/schema.md`
- Create: `testdata/agent/soil-moisture/real-conversations/template.md`

**Step 1: Write the field definitions**

Describe each required field with type, meaning, and whether it is mandatory.

**Step 2: Provide a reusable template**

Add a sample record showing how a real question, context, expected capability, evidence rules, and regression tags should be written.

### Task 3: Wire the corpus into the parent docs

**Files:**
- Modify: `testdata/agent/soil-moisture/README.md`

**Step 1: Add a link to the new corpus**

Document the new real-conversations folder alongside the existing formal library.

**Step 2: Explain the three-layer QA model**

Summarize the separation between `core-gate`, `real-conversations`, and `failure-regressions`.

