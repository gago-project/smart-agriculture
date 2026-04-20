import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';

const root = new URL('..', import.meta.url);

test('web has required visible pages', () => {
  assert.equal(existsSync(new URL('../app/page.tsx', import.meta.url)), true);
  assert.equal(existsSync(new URL('../app/chat/page.tsx', import.meta.url)), true);
  assert.equal(existsSync(new URL('../app/admin/page.tsx', import.meta.url)), true);
});

test('agent chat route proxies to configured AGENT_BASE_URL', () => {
  const source = readFileSync(new URL('../app/api/agent/chat/route.ts', import.meta.url), 'utf8');
  assert.match(source, /AGENT_BASE_URL/);
  assert.match(source, /\/chat/);
});
