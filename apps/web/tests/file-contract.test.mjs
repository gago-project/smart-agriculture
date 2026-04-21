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
  assert.equal(existsSync(new URL('../app/api/developer/agent/query-logs/route.ts', import.meta.url)), true);
  assert.equal(existsSync(new URL('../workspace/App.tsx', import.meta.url)), true);
});

test('developer workspace can view agent query logs without soil admin access', () => {
  assert.equal(existsSync(new URL('../workspace/components/AgentLogPage.tsx', import.meta.url)), true);
  assert.equal(existsSync(new URL('../workspace/services/agentLogApi.ts', import.meta.url)), true);

  const appSource = readFileSync(new URL('../workspace/App.tsx', import.meta.url), 'utf8');
  assert.match(appSource, /canViewAgentLogs/);
  assert.match(appSource, /authUser\?\.role === 'developer'/);
  assert.match(appSource, /AgentLogPage/);
  assert.match(appSource, /查询日志/);
  assert.doesNotMatch(appSource, /开发日志/);
});

test('workspace no longer renders the right-side evidence analysis panel', () => {
  const appSource = readFileSync(new URL('../workspace/App.tsx', import.meta.url), 'utf8');

  assert.doesNotMatch(appSource, /EvidencePanel/);
  assert.doesNotMatch(appSource, /selectedEvidenceMessage/);
});

test('chat panel no longer renders AI involvement badge in message list', () => {
  const chatPanelSource = readFileSync(new URL('../workspace/components/ChatPanel.tsx', import.meta.url), 'utf8');

  assert.doesNotMatch(chatPanelSource, /AI参与度/);
  assert.doesNotMatch(chatPanelSource, /ai_involvement/);
});

test('developer log filters use selects and keep the table focused on rows', () => {
  const pageSource = readFileSync(new URL('../workspace/components/AgentLogPage.tsx', import.meta.url), 'utf8');

  assert.match(pageSource, /queryTypeOptions/);
  assert.match(pageSource, /intentOptions/);
  assert.match(pageSource, /aria-label="查询类型"/);
  assert.match(pageSource, /aria-label="意图"/);
  assert.doesNotMatch(pageSource, /placeholder="recent_summary"/);
  assert.doesNotMatch(pageSource, /placeholder="soil_recent_summary"/);
  assert.doesNotMatch(pageSource, /agent-log-detail/);
});

test('query log repository pages ids before loading wide log fields', () => {
  const source = readFileSync(new URL('../lib/server/agentLogRepository.mjs', import.meta.url), 'utf8');

  assert.match(source, /SELECT\s+query_id\s+FROM agent_query_log[\s\S]*ORDER BY created_at DESC[\s\S]*LIMIT/);
  assert.match(source, /WHERE query_id IN \(\$\{detailPlaceholders\}\)/);
  assert.doesNotMatch(source, /SELECT[\s\S]*executed_result_json[\s\S]*FROM agent_query_log[\s\S]*ORDER BY created_at DESC/);
});

test('authoritative agent plan includes query log request and routing context fields', () => {
  const planSource = readFileSync(
    new URL('../../agent/plans/1/1.2026-04-20-soil-moisture-agent-plan.md', import.meta.url),
    'utf8',
  );

  assert.match(planSource, /request_text\s+text\s+null/i);
  assert.match(planSource, /response_text\s+text\s+null/i);
  assert.match(planSource, /input_type\s+varchar\(32\)\s+null/i);
  assert.match(planSource, /intent\s+varchar\(64\)\s+null/i);
  assert.match(planSource, /answer_type\s+varchar\(64\)\s+null/i);
  assert.match(planSource, /final_status\s+varchar\(64\)\s+null/i);
  assert.match(planSource, /executed_result_json\s+json\s+null/i);
  assert.doesNotMatch(planSource, /result_preview_json/i);
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
