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

test('admin routes for records upload and rules exist', () => {
  assert.equal(existsSync(new URL('../app/api/admin/soil/records/route.ts', import.meta.url)), true);
  assert.equal(existsSync(new URL('../app/api/admin/soil/upload/route.ts', import.meta.url)), true);
  assert.equal(existsSync(new URL('../app/api/admin/soil/rules/route.ts', import.meta.url)), true);
});

test('workspace routes for auth and chat exist', () => {
  assert.equal(existsSync(new URL('../app/api/auth/login/route.ts', import.meta.url)), true);
  assert.equal(existsSync(new URL('../app/api/auth/me/route.ts', import.meta.url)), true);
  assert.equal(existsSync(new URL('../app/api/auth/logout/route.ts', import.meta.url)), true);
  assert.equal(existsSync(new URL('../app/api/agent/chat/route.ts', import.meta.url)), true);
  assert.equal(existsSync(new URL('../app/api/agent/summary/route.ts', import.meta.url)), true);
  assert.equal(existsSync(new URL('../workspace/App.tsx', import.meta.url)), true);
});

test('agent summary route must surface upstream errors instead of fake fallback data', () => {
  const source = readFileSync(new URL('../app/api/agent/summary/route.ts', import.meta.url), 'utf8');
  assert.doesNotMatch(source, /待连接/);
  assert.doesNotMatch(source, /total_records:\s*0/);
  assert.doesNotMatch(source, /status:\s*200/);
});

test('web start script prepares standalone static assets', () => {
  const pkg = readFileSync(new URL('../package.json', import.meta.url), 'utf8');
  assert.match(pkg, /copy:standalone-assets/);
  assert.match(pkg, /\.next\/standalone\/\.next\/static/);
});

test('web docker image binds standalone server to all interfaces for healthcheck', () => {
  const dockerfile = readFileSync(new URL('../Dockerfile', import.meta.url), 'utf8');
  assert.match(dockerfile, /ENV HOSTNAME=0\.0\.0\.0/);
  assert.match(dockerfile, /ENV PORT=3000/);
});

test('docker compose uses container network addresses for runtime dependencies', () => {
  const compose = readFileSync(new URL('../../../infra/docker/docker-compose.yml', import.meta.url), 'utf8');
  assert.match(compose, /REDIS_URL:\s+redis:\/\/redis:6379\/0/);
  assert.match(compose, /AGENT_BASE_URL:\s+http:\/\/agent:8000/);
  assert.match(compose, /MYSQL_HOST:\s+mysql/);
  assert.match(compose, /MYSQL_DATABASE:\s+\$\{MYSQL_DATABASE\}/);
  assert.match(compose, /MYSQL_USER:\s+\$\{MYSQL_USER\}/);
  assert.match(compose, /MYSQL_PASSWORD:\s+\$\{MYSQL_PASSWORD\}/);
});
