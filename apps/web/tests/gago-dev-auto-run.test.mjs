import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import {
  listRealConversationCases,
  parseRealConversationLibraryMarkdown,
} from '../lib/server/realConversationLibrary.mjs';

test('real conversation library parser keeps markdown as the single source of truth', async () => {
  const cases = await listRealConversationCases();

  assert.equal(cases.length, 126);
  assert.equal(cases[0].id, 1);
  assert.equal(cases[0].turns.length, 1);

  const warningFollowUp = cases.find((item) => item.id === 77);
  assert.ok(warningFollowUp);
  assert.deepEqual(warningFollowUp.turns, ['最近7天哪些区域出现了预警信息？', '那徐州市呢？']);

  const longChain = cases.find((item) => item.id === 112);
  assert.ok(longChain);
  assert.equal(longChain.turns.length, 4);
});

test('real conversation parser ignores table headers and separators', () => {
  const cases = parseRealConversationLibraryMarkdown(`
| ID | 分类 | 测试问题 | 主测能力 | 预期 |
|---:|---|---|---|---|
| 9 | 示例 | 问题一 → 问题二 | multi | 支持 |
`);

  assert.equal(cases.length, 1);
  assert.deepEqual(cases[0].turns, ['问题一', '问题二']);
});

test('gago-dev-only auto run endpoint is protected by username and returns markdown-backed cases', () => {
  const routeSource = readFileSync(
    new URL('../app/api/developer/soil/real-conversation-library/route.ts', import.meta.url),
    'utf8',
  );

  assert.match(routeSource, /requireRequestUser/);
  assert.match(routeSource, /gago-dev/);
  assert.match(routeSource, /listRealConversationCases/);
  assert.match(routeSource, /total_count/);
});

test('frontend app wires gago-dev auto run off login completion and clears local chat state only', () => {
  const appSource = readFileSync(new URL('../workspace/App.tsx', import.meta.url), 'utf8');
  const authStoreSource = readFileSync(new URL('../workspace/store/authStore.ts', import.meta.url), 'utf8');
  const chatStoreSource = readFileSync(new URL('../workspace/store/chatStore.ts', import.meta.url), 'utf8');
  const runnerHookSource = readFileSync(
    new URL('../workspace/hooks/useGagoDevAutoRunner.ts', import.meta.url),
    'utf8',
  );

  assert.match(appSource, /useGagoDevAutoRunner/);
  assert.match(appSource, /gago-dev 自动真实问答回归/);
  assert.match(authStoreSource, /lastLoginAt/);
  assert.match(chatStoreSource, /clearChatLocalState/);
  assert.match(chatStoreSource, /doc-frontend-chat-v1/);
  assert.doesNotMatch(chatStoreSource, /doc-frontend-auth-v1/);
  assert.match(runnerHookSource, /buildSingleTurnSessionTitle/);
  assert.match(runnerHookSource, /turns\.length === 1/);
  assert.match(runnerHookSource, /focusSession: sessionId === singleTurnSessionId/);
});
