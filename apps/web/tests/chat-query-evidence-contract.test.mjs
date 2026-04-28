import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';

test('workspace chat renders an admin-only query evidence sidebar', () => {
  const appSource = readFileSync(new URL('../workspace/App.tsx', import.meta.url), 'utf8');

  assert.match(appSource, /AdminQueryEvidenceSidebar/);
  assert.match(appSource, /canViewChatEvidence/);
  assert.match(appSource, /authUser\?\.role === 'admin'/);
});

test('chat panel supports selecting assistant replies for evidence review', () => {
  const chatPanelSource = readFileSync(new URL('../workspace/components/ChatPanel.tsx', import.meta.url), 'utf8');

  assert.match(chatPanelSource, /selectedAssistantMessageId/);
  assert.match(chatPanelSource, /onSelectAssistantMessage/);
  assert.match(chatPanelSource, /message\.role === 'assistant'/);
});

test('chat store persists selected assistant message ids by session', () => {
  const chatStoreSource = readFileSync(new URL('../workspace/store/chatStore.ts', import.meta.url), 'utf8');

  assert.match(chatStoreSource, /selectedAssistantMessageIds/);
  assert.match(chatStoreSource, /selectAssistantMessage/);
  assert.match(chatStoreSource, /partialize:[\s\S]*selectedAssistantMessageIds/);
});

test('admin query evidence route exists and loads evidence by session and turn', () => {
  assert.equal(existsSync(new URL('../app/api/admin/agent/query-evidence/route.ts', import.meta.url)), true);

  const routeSource = readFileSync(new URL('../app/api/admin/agent/query-evidence/route.ts', import.meta.url), 'utf8');
  const repositorySource = readFileSync(new URL('../lib/server/agentLogRepository.mjs', import.meta.url), 'utf8');

  assert.match(routeSource, /session_id/);
  assert.match(routeSource, /turn_id/);
  assert.match(routeSource, /getAgentQueryEvidenceByTurn/);
  assert.match(repositorySource, /export async function getAgentQueryEvidenceByTurn/);
  assert.match(repositorySource, /WHERE session_id = \?/);
  assert.match(repositorySource, /AND turn_id = \?/);
  assert.match(repositorySource, /ORDER BY created_at ASC/);
});
