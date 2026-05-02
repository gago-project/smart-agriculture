import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';

test('server chat session routes are removed in favor of a thin chat runtime', () => {
  assert.equal(existsSync(new URL('../app/api/agent/sessions/route.ts', import.meta.url)), false);
  assert.equal(existsSync(new URL('../app/api/agent/sessions/[sessionId]/route.ts', import.meta.url)), false);
  assert.equal(existsSync(new URL('../app/api/agent/sessions/[sessionId]/archive/route.ts', import.meta.url)), false);
  assert.equal(existsSync(new URL('../lib/server/chatSessionRepository.mjs', import.meta.url)), false);
  assert.equal(existsSync(new URL('../app/api/agent/chat/route.ts', import.meta.url)), true);
  assert.equal(existsSync(new URL('../lib/server/agentChatRuntime.mjs', import.meta.url)), true);

  const routeSource = readFileSync(new URL('../app/api/agent/chat/route.ts', import.meta.url), 'utf8');

  assert.match(routeSource, /runAgentChatTurn/);
  assert.match(routeSource, /session_id/);
  assert.match(routeSource, /turn_id/);
  assert.match(routeSource, /current_context/);
  assert.match(routeSource, /client_message_id/);
  assert.match(routeSource, /message is required/);
  assert.doesNotMatch(routeSource, /executeChatTurn/);
  assert.doesNotMatch(routeSource, /chatSessionRepository/);
  assert.doesNotMatch(routeSource, /createChatSession/);
});

test('agent chat runtime keeps the upstream /chat-v2 bridge and query-log write path', () => {
  const runtimeSource = readFileSync(new URL('../lib/server/agentChatRuntime.mjs', import.meta.url), 'utf8');

  assert.match(runtimeSource, /export async function runAgentChatTurn/);
  assert.match(runtimeSource, /chat-v2/);
  assert.match(runtimeSource, /turn_id/);
  assert.match(runtimeSource, /current_context/);
  assert.match(runtimeSource, /query_log_entries/);
  assert.match(runtimeSource, /INSERT INTO agent_query_log/);
});

test('chat store persists local sessions current context and selected assistant message ids', () => {
  const storeSource = readFileSync(new URL('../workspace/store/chatStore.ts', import.meta.url), 'utf8');

  assert.match(storeSource, /sessions/);
  assert.match(storeSource, /activeSessionId/);
  assert.match(storeSource, /selectedAssistantMessageIds/);
  assert.match(storeSource, /currentContext/);
  assert.match(storeSource, /partialize:/);
  assert.match(storeSource, /sessions:\s*compactPersistedSessions\(state\.sessions\)/);
  assert.match(storeSource, /selectedAssistantMessageIds:\s*compactSelectedAssistantMessageIds/);
});

test('chat actions are fully local and send turn id plus current context to the backend', () => {
  const actionsSource = readFileSync(new URL('../workspace/hooks/useChatActions.ts', import.meta.url), 'utf8');

  assert.doesNotMatch(actionsSource, /fetchChatSessions/);
  assert.doesNotMatch(actionsSource, /fetchChatSession/);
  assert.doesNotMatch(actionsSource, /createChatSession/);
  assert.doesNotMatch(actionsSource, /archiveChatSession/);
  assert.doesNotMatch(actionsSource, /renameChatSession/);
  assert.match(actionsSource, /const turnId = session \? session\.lastTurnId \+ 1 : 1;/);
  assert.match(actionsSource, /currentContext/);
  assert.match(actionsSource, /sendChat\(sessionId,\s*turnId,\s*clientMessageId,\s*question,\s*currentContext/);
  assert.match(actionsSource, /turn_context/);
});

test('chat block pagination is driven by snapshot ids instead of server-side turn storage', () => {
  assert.equal(existsSync(new URL('../app/api/agent/chat-block/route.ts', import.meta.url)), true);
  assert.equal(existsSync(new URL('../lib/server/chatBlockRepository.mjs', import.meta.url)), true);

  const routeSource = readFileSync(new URL('../app/api/agent/chat-block/route.ts', import.meta.url), 'utf8');
  const repositorySource = readFileSync(new URL('../lib/server/chatBlockRepository.mjs', import.meta.url), 'utf8');
  const apiSource = readFileSync(new URL('../workspace/services/chatApi.ts', import.meta.url), 'utf8');
  const rendererSource = readFileSync(new URL('../workspace/components/TurnRenderer.tsx', import.meta.url), 'utf8');

  assert.match(routeSource, /snapshot_id/);
  assert.match(routeSource, /block_type/);
  assert.match(routeSource, /page_size/);
  assert.doesNotMatch(routeSource, /session_id/);
  assert.doesNotMatch(routeSource, /turn_id/);
  assert.doesNotMatch(routeSource, /block_id/);
  assert.match(repositorySource, /agent_result_snapshot_item/);
  assert.match(repositorySource, /WHERE snapshot_id = \?/);
  assert.match(apiSource, /export async function fetchChatBlock/);
  assert.match(apiSource, /snapshot_id: snapshotId/);
  assert.match(apiSource, /block_type: blockType/);
  assert.match(apiSource, /snapshot_id/);
  assert.doesNotMatch(rendererSource, /turn\.session_id/);
  assert.doesNotMatch(rendererSource, /turn\.turn_id/);
  assert.match(rendererSource, /pagination\?\.snapshot_id/);
  assert.match(rendererSource, /fetchChatBlock\(snapshotId,\s*viewBlock\.block_type,\s*nextPage/);
});
