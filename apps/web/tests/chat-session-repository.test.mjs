import test from 'node:test';
import assert from 'node:assert/strict';

function loadRepositoryModule() {
  return import(new URL(`../lib/server/agentChatRuntime.mjs?ts=${Date.now()}`, import.meta.url));
}

test('parseAgentChatV2Response keeps upstream plain-text failures readable', async () => {
  const { parseAgentChatV2Response } = await loadRepositoryModule();
  const response = new Response('Internal Server Error', {
    status: 500,
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  });

  await assert.rejects(
    () => parseAgentChatV2Response(response),
    /Internal Server Error/,
  );
});

test('parseAgentChatV2Response returns JSON payloads on success', async () => {
  const { parseAgentChatV2Response } = await loadRepositoryModule();
  const response = new Response(JSON.stringify({ turn_id: 1, final_text: 'ok' }), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });

  assert.deepEqual(await parseAgentChatV2Response(response), { turn_id: 1, final_text: 'ok' });
});
