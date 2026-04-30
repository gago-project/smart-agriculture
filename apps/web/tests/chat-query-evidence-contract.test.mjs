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

test('chat panel starter examples stay within raw-only query capabilities', () => {
  const chatPanelSource = readFileSync(new URL('../workspace/components/ChatPanel.tsx', import.meta.url), 'utf8');

  assert.match(chatPanelSource, /最近30天，按地区汇总墒情数据/);
  assert.doesNotMatch(chatPanelSource, /最近30天，哪些地区墒情异常最多/);
});

test('assistant text replies are not duplicated by plain-text turn blocks', () => {
  const chatPanelSource = readFileSync(new URL('../workspace/components/ChatPanel.tsx', import.meta.url), 'utf8');
  const turnRendererSource = readFileSync(new URL('../workspace/components/TurnRenderer.tsx', import.meta.url), 'utf8');

  assert.match(chatPanelSource, /<p>\{message\.content \|\| \(message\.status === 'streaming' \? '\.\.\.' : ''\)\}<\/p>/);
  assert.match(turnRendererSource, /block\.display_mode === 'evidence_only'/);
  assert.match(turnRendererSource, /block\.block_type === 'guidance_card' \|\| block\.block_type === 'fallback_card'/);
  assert.match(turnRendererSource, /return null;/);
});

test('chat turn tables keep message width constrained and scroll horizontally', () => {
  const globalsSource = readFileSync(new URL('../app/globals.css', import.meta.url), 'utf8');

  assert.match(globalsSource, /\.message\s*\{[\s\S]*min-width:\s*0/);
  assert.match(globalsSource, /\.turn-block-table-wrap\s*\{[\s\S]*overflow-x:\s*auto/);
  assert.match(globalsSource, /\.turn-block-table\s*\{[\s\S]*(width:\s*max-content|min-width:\s*100%)/);
});

test('chat store persists selected assistant message ids by session', () => {
  const chatStoreSource = readFileSync(new URL('../workspace/store/chatStore.ts', import.meta.url), 'utf8');

  assert.match(chatStoreSource, /selectedAssistantMessageIds/);
  assert.match(chatStoreSource, /selectAssistantMessage/);
  assert.match(chatStoreSource, /partialize:[\s\S]*selectedAssistantMessageIds/);
});

test('chat store persists only lightweight query references instead of full evidence payloads', () => {
  const chatStoreSource = readFileSync(new URL('../workspace/store/chatStore.ts', import.meta.url), 'utf8');

  assert.match(chatStoreSource, /function compactMessageData/);
  assert.match(chatStoreSource, /function compactMessageMeta/);
  assert.match(chatStoreSource, /session_id/);
  assert.match(chatStoreSource, /turn_id/);
  assert.match(chatStoreSource, /should_query/);
  assert.match(chatStoreSource, /migrate:/);
  assert.match(chatStoreSource, /selectedAssistantMessageIds/);
  assert.doesNotMatch(chatStoreSource, /sessions:\s*compactPersistedSessions/);
});

test('chat actions stop storing intermediate evidence and processing blobs in message meta', () => {
  const actionsSource = readFileSync(new URL('../workspace/hooks/useChatActions.ts', import.meta.url), 'utf8');

  assert.match(actionsSource, /responseToAssistantMeta/);
  assert.match(actionsSource, /query_ref\?\.has_query/);
  assert.match(actionsSource, /turn:/);
  assert.doesNotMatch(actionsSource, /evidence: result\.evidence/);
  assert.doesNotMatch(actionsSource, /processing: result\.processing/);
});

test('admin query evidence route exists and loads evidence by session and turn', () => {
  assert.equal(existsSync(new URL('../app/api/admin/agent/query-evidence/route.ts', import.meta.url)), true);
  assert.equal(existsSync(new URL('../app/api/admin/agent/query-evidence/result/route.ts', import.meta.url)), true);

  const routeSource = readFileSync(new URL('../app/api/admin/agent/query-evidence/route.ts', import.meta.url), 'utf8');
  const resultRouteSource = readFileSync(new URL('../app/api/admin/agent/query-evidence/result/route.ts', import.meta.url), 'utf8');
  const repositorySource = readFileSync(new URL('../lib/server/agentLogRepository.mjs', import.meta.url), 'utf8');

  assert.match(routeSource, /session_id/);
  assert.match(routeSource, /turn_id/);
  assert.match(routeSource, /getAgentQueryEvidenceByTurn/);
  assert.match(resultRouteSource, /query_id/);
  assert.match(resultRouteSource, /getAgentQueryEvidenceResultByQueryId/);
  assert.match(repositorySource, /export async function getAgentQueryEvidenceByTurn/);
  assert.match(repositorySource, /export async function getAgentQueryEvidenceResultByQueryId/);
  assert.match(repositorySource, /WHERE session_id = \?/);
  assert.match(repositorySource, /AND turn_id = \?/);
  assert.match(repositorySource, /SELECT\s+query_id,\s+DATE_FORMAT\(created_at/);
  assert.match(repositorySource, /WHERE query_id IN \(\$\{detailPlaceholders\}\)/);
});

test('admin query evidence sidebar lazy loads oversized raw JSON only when expanded', () => {
  const sidebarSource = readFileSync(new URL('../workspace/components/AdminQueryEvidenceSidebar.tsx', import.meta.url), 'utf8');
  const apiSource = readFileSync(new URL('../workspace/services/queryEvidenceApi.ts', import.meta.url), 'utf8');
  const repositorySource = readFileSync(new URL('../lib/server/agentLogRepository.mjs', import.meta.url), 'utf8');

  assert.match(sidebarSource, /fetchAdminQueryEvidenceResult/);
  assert.match(sidebarSource, /preview_columns/);
  assert.match(sidebarSource, /仅展示关键字段/);
  assert.match(sidebarSource, /result_truncated/);
  assert.match(sidebarSource, /onToggle/);
  assert.match(sidebarSource, /detailsOpen/);
  assert.match(sidebarSource, /prettyJson\(rawState\.data \?\? value\)/);
  assert.doesNotMatch(sidebarSource, /fallbackQueryResult/);
  assert.match(repositorySource, /preview_columns/);
  assert.match(repositorySource, /RECORD_PREVIEW_COLUMNS/);
  assert.match(apiSource, /export async function fetchAdminQueryEvidenceResult/);
  assert.match(apiSource, /\/api\/admin\/agent\/query-evidence\/result/);
});

test('agent query evidence repository sanitizes legacy derived fields before building previews', () => {
  const repositorySource = readFileSync(new URL('../lib/server/agentLogRepository.mjs', import.meta.url), 'utf8');

  assert.match(repositorySource, /sanitizeExecutedResult/);
});
