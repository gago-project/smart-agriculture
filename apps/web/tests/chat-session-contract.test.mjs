import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';

test('server-backed chat session routes exist for sessions archive and block pagination', () => {
  assert.equal(existsSync(new URL('../app/api/agent/sessions/route.ts', import.meta.url)), true);
  assert.equal(existsSync(new URL('../app/api/agent/sessions/[sessionId]/route.ts', import.meta.url)), true);
  assert.equal(existsSync(new URL('../app/api/agent/sessions/[sessionId]/archive/route.ts', import.meta.url)), true);
  assert.equal(existsSync(new URL('../app/api/agent/chat-block/route.ts', import.meta.url)), true);
});

test('agent chat route uses client_message_id and no longer derives turn_id from local history', () => {
  const routeSource = readFileSync(new URL('../app/api/agent/chat/route.ts', import.meta.url), 'utf8');

  assert.match(routeSource, /client_message_id/);
  assert.match(routeSource, /session_id/);
  assert.doesNotMatch(routeSource, /history\.length \+ 1/);
  assert.doesNotMatch(routeSource, /thread_id/);
  assert.doesNotMatch(routeSource, /history:/);
});

test('chat session repository uses transaction locking and idempotent turn lookup', () => {
  assert.equal(existsSync(new URL('../lib/server/chatSessionRepository.mjs', import.meta.url)), true);
  const repositorySource = readFileSync(new URL('../lib/server/chatSessionRepository.mjs', import.meta.url), 'utf8');
  const mysqlSource = readFileSync(new URL('../lib/server/mysql.mjs', import.meta.url), 'utf8');

  assert.match(repositorySource, /FOR UPDATE/);
  assert.match(repositorySource, /client_message_id/);
  assert.match(repositorySource, /last_turn_id/);
  assert.match(mysqlSource, /export async function withMysqlTransaction/);
});

test('chat session repository reserves turn ids before agent execution and finalizes afterwards', () => {
  const repositorySource = readFileSync(new URL('../lib/server/chatSessionRepository.mjs', import.meta.url), 'utf8');

  assert.match(repositorySource, /async function reserveChatTurn/);
  assert.match(repositorySource, /async function finalizeReservedChatTurn/);
  assert.match(repositorySource, /const reservedTurn = await retryMysqlOperation\(\(\) =>\s*reserveChatTurn/);
  assert.match(repositorySource, /agentResult = await callAgentChatV2/);
  assert.match(repositorySource, /return await retryMysqlOperation\(\(\) =>\s*finalizeReservedChatTurn/);
});

test('chat session repository prevents overlapping in-flight turns in the same session', () => {
  const repositorySource = readFileSync(new URL('../lib/server/chatSessionRepository.mjs', import.meta.url), 'utf8');

  assert.match(repositorySource, /answer_kind = 'pending'/);
  assert.match(repositorySource, /当前会话处理中，请稍后重试/);
});

test('chat store persists active selection only and no longer persists full session transcripts', () => {
  const storeSource = readFileSync(new URL('../workspace/store/chatStore.ts', import.meta.url), 'utf8');

  assert.match(storeSource, /activeSessionId/);
  assert.match(storeSource, /selectedAssistantMessageIds/);
  assert.match(storeSource, /partialize:/);
  assert.doesNotMatch(storeSource, /sessions:\s*compactPersistedSessions/);
});
