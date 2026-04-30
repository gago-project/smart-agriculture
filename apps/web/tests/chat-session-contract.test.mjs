import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';

test('server-backed chat session routes exist for sessions archive and block pagination', () => {
  assert.equal(existsSync(new URL('../app/api/agent/sessions/route.ts', import.meta.url)), true);
  assert.equal(existsSync(new URL('../app/api/agent/sessions/[sessionId]/route.ts', import.meta.url)), true);
  assert.equal(existsSync(new URL('../app/api/agent/sessions/[sessionId]/archive/route.ts', import.meta.url)), true);
  assert.equal(existsSync(new URL('../app/api/agent/chat-block/route.ts', import.meta.url)), true);
});

test('chat session detail route also supports renaming the session title', () => {
  const routeSource = readFileSync(new URL('../app/api/agent/sessions/[sessionId]/route.ts', import.meta.url), 'utf8');
  const repositorySource = readFileSync(new URL('../lib/server/chatSessionRepository.mjs', import.meta.url), 'utf8');

  assert.match(routeSource, /export async function PATCH/);
  assert.match(routeSource, /payload\?\.title/);
  assert.match(routeSource, /renameChatSession/);
  assert.match(repositorySource, /export async function renameChatSession/);
  assert.match(repositorySource, /UPDATE agent_chat_session/);
  assert.match(repositorySource, /SET title = \?, updated_at = NOW\(\)/);
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

test('chat session repository sanitizes stored legacy turn blocks before returning them', () => {
  const repositorySource = readFileSync(new URL('../lib/server/chatSessionRepository.mjs', import.meta.url), 'utf8');

  assert.match(repositorySource, /sanitizeTurnBlocks/);
});

test('chat session repository clamps list block page size to 10 for snapshot pagination', () => {
  const repositorySource = readFileSync(new URL('../lib/server/chatSessionRepository.mjs', import.meta.url), 'utf8');

  assert.match(repositorySource, /const SNAPSHOT_PAGE_SIZE_DEFAULT = 10;/);
  assert.match(repositorySource, /Math\.min\(SNAPSHOT_PAGE_SIZE_DEFAULT,\s*Math\.max\(1,\s*toPositiveInt\(pageSize,\s*SNAPSHOT_PAGE_SIZE_DEFAULT\)\)\)/);
  assert.match(repositorySource, /Math\.min\(SNAPSHOT_PAGE_SIZE_DEFAULT,\s*Math\.max\(1,\s*toPositiveInt\(pagination\.page_size,\s*SNAPSHOT_PAGE_SIZE_DEFAULT\)\)\)/);
});

test('chat session repository paginates group tables through the same snapshot block endpoint', () => {
  const repositorySource = readFileSync(new URL('../lib/server/chatSessionRepository.mjs', import.meta.url), 'utf8');

  assert.match(repositorySource, /if \(block\.block_type !== 'list_table' && block\.block_type !== 'group_table'\)/);
  assert.match(repositorySource, /if \(block\?\.block_type === 'list_table' \|\| block\?\.block_type === 'group_table'\)/);
  assert.match(repositorySource, /if \(matched\.block_type === 'list_table' \|\| matched\.block_type === 'group_table'\)/);
});

test('chat session snapshot pagination avoids prepared execute for LIMIT/OFFSET', () => {
  const repositorySource = readFileSync(new URL('../lib/server/chatSessionRepository.mjs', import.meta.url), 'utf8');

  assert.match(
    repositorySource,
    /const \[rows\] = await connection\.query\([\s\S]*WHERE snapshot_id = \?[\s\S]*ORDER BY row_index ASC[\s\S]*LIMIT \? OFFSET \?/,
  );
  assert.doesNotMatch(
    repositorySource,
    /const \[rows\] = await connection\.execute\([\s\S]*WHERE snapshot_id = \?[\s\S]*ORDER BY row_index ASC[\s\S]*LIMIT \? OFFSET \?/,
  );
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
