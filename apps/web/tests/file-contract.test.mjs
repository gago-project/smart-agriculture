import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';

const root = new URL('..', import.meta.url);

test('web has route files for chat admin and query logs', () => {
  assert.equal(existsSync(new URL('../app/page.tsx', import.meta.url)), true);
  assert.equal(existsSync(new URL('../app/chat/page.tsx', import.meta.url)), true);
  assert.equal(existsSync(new URL('../app/admin/page.tsx', import.meta.url)), true);
  assert.equal(existsSync(new URL('../app/query-logs/page.tsx', import.meta.url)), true);
});

test('workspace app uses route state instead of local workspaceView state', () => {
  const appSource = readFileSync(new URL('../workspace/App.tsx', import.meta.url), 'utf8');

  assert.match(appSource, /usePathname/);
  assert.match(appSource, /useRouter/);
  assert.doesNotMatch(appSource, /workspaceView/);
});

test('workspace app redirects authenticated root users to chat', () => {
  const appSource = readFileSync(new URL('../workspace/App.tsx', import.meta.url), 'utf8');

  assert.match(appSource, /pathname === '\/'/);
  assert.match(appSource, /router\.replace\('\/chat'\)/);
});

test('workspace app keeps route permission boundaries in one place', () => {
  const appSource = readFileSync(new URL('../workspace/App.tsx', import.meta.url), 'utf8');

  assert.match(appSource, /canManageSoilAdmin/);
  assert.match(appSource, /canViewAgentLogs/);
  assert.match(appSource, /pathname === '\/admin'/);
  assert.match(appSource, /pathname === '\/query-logs'/);
  assert.match(appSource, /router\.replace\('\/chat'\)/);
});

test('workspace app renders neutral loading while redirecting guarded routes', () => {
  const appSource = readFileSync(new URL('../workspace/App.tsx', import.meta.url), 'utf8');

  assert.match(appSource, /isRedirectingWorkspaceRoute/);
  assert.match(appSource, /pathname === '\/'/);
  assert.match(appSource, /pathname === '\/admin' && !canManageSoilAdmin/);
  assert.match(appSource, /pathname === '\/query-logs' && !canViewAgentLogs/);
  assert.match(appSource, /auth-loading/);
});

test('agent chat route proxies to configured AGENT_BASE_URL', () => {
  const source = readFileSync(new URL('../app/api/agent/chat/route.ts', import.meta.url), 'utf8');
  assert.match(source, /AGENT_BASE_URL/);
  assert.match(source, /\/chat/);
  assert.match(source, /closing_answer/);
  assert.match(source, /conversation_closed/);
  assert.match(source, /inheritanceMode/);
  assert.match(source, /buildAnalysisContext/);
  assert.match(source, /mergedSlots/);
  assert.doesNotMatch(source, /region_level:\s*'county'/);
  assert.doesNotMatch(source, /used_context:\s*history\.length > 0/);
  assert.doesNotMatch(source, /memory:\s*history\.length > 0/);
});

test('admin routes for records upload and rules exist', () => {
  assert.equal(existsSync(new URL('../app/api/admin/soil/records/route.ts', import.meta.url)), true);
  assert.equal(existsSync(new URL('../app/api/admin/soil/upload/route.ts', import.meta.url)), true);
  assert.equal(existsSync(new URL('../app/api/admin/soil/import-jobs/route.ts', import.meta.url)), true);
  assert.equal(existsSync(new URL('../app/api/admin/soil/import-jobs/[jobId]/route.ts', import.meta.url)), true);
  assert.equal(existsSync(new URL('../app/api/admin/soil/import-jobs/[jobId]/diff/route.ts', import.meta.url)), true);
  assert.equal(existsSync(new URL('../app/api/admin/soil/import-jobs/[jobId]/apply/route.ts', import.meta.url)), true);
  assert.equal(existsSync(new URL('../app/api/admin/soil/rules/route.ts', import.meta.url)), true);
});

test('workspace routes for auth and chat exist', () => {
  assert.equal(existsSync(new URL('../app/api/auth/login/route.ts', import.meta.url)), true);
  assert.equal(existsSync(new URL('../app/api/auth/me/route.ts', import.meta.url)), true);
  assert.equal(existsSync(new URL('../app/api/auth/logout/route.ts', import.meta.url)), true);
  assert.equal(existsSync(new URL('../app/api/agent/chat/route.ts', import.meta.url)), true);
  assert.equal(existsSync(new URL('../app/api/agent/summary/route.ts', import.meta.url)), true);
  assert.equal(existsSync(new URL('../app/api/developer/agent/query-logs/route.ts', import.meta.url)), true);
  assert.equal(existsSync(new URL('../app/api/developer/agent/query-logs/[queryId]/route.ts', import.meta.url)), true);
  assert.equal(existsSync(new URL('../workspace/App.tsx', import.meta.url)), true);
});

test('developer workspace can view agent query logs without soil admin access', () => {
  assert.equal(existsSync(new URL('../workspace/components/AgentLogPage.tsx', import.meta.url)), true);
  assert.equal(existsSync(new URL('../workspace/services/agentLogApi.ts', import.meta.url)), true);

  const appSource = readFileSync(new URL('../workspace/App.tsx', import.meta.url), 'utf8');
  const menuSource = readFileSync(new URL('../workspace/components/WorkspaceUserMenu.tsx', import.meta.url), 'utf8');
  assert.match(appSource, /canViewAgentLogs/);
  assert.match(appSource, /authUser\?\.role === 'developer'/);
  assert.match(appSource, /AgentLogPage/);
  assert.match(menuSource, /查询日志/);
  assert.doesNotMatch(appSource, /开发日志/);
});

test('workspace no longer renders the right-side evidence analysis panel', () => {
  const appSource = readFileSync(new URL('../workspace/App.tsx', import.meta.url), 'utf8');

  assert.doesNotMatch(appSource, /EvidencePanel/);
  assert.doesNotMatch(appSource, /selectedEvidenceMessage/);
});

test('workspace header uses a dedicated user menu instead of nav buttons row', () => {
  const appSource = readFileSync(new URL('../workspace/App.tsx', import.meta.url), 'utf8');

  assert.match(appSource, /WorkspaceUserMenu/);
  assert.doesNotMatch(appSource, /workspace-nav-button/);
});

test('workspace user menu contains route items username and logout entry', () => {
  const menuSource = readFileSync(new URL('../workspace/components/WorkspaceUserMenu.tsx', import.meta.url), 'utf8');

  assert.match(menuSource, /问答工作台/);
  assert.match(menuSource, /墒情管理/);
  assert.match(menuSource, /查询日志/);
  assert.match(menuSource, /用户名/);
  assert.match(menuSource, /退出登录/);
  assert.match(menuSource, /router\.push/);
});

test('workspace user menu avoids misleading menu roles and guards current route push', () => {
  const menuSource = readFileSync(new URL('../workspace/components/WorkspaceUserMenu.tsx', import.meta.url), 'utf8');

  assert.match(menuSource, /targetPath !== currentPath/);
  assert.doesNotMatch(menuSource, /role="menu"/);
  assert.doesNotMatch(menuSource, /role="menuitem"/);
});

test('globals include workspace dropdown menu styles', () => {
  const globalsSource = readFileSync(new URL('../app/globals.css', import.meta.url), 'utf8');

  assert.match(globalsSource, /\.workspace-menu-trigger/);
  assert.match(globalsSource, /\.workspace-menu-panel/);
  assert.match(globalsSource, /\.workspace-menu-item/);
});

test('workspace user menu uses final dropdown class names', () => {
  const menuSource = readFileSync(new URL('../workspace/components/WorkspaceUserMenu.tsx', import.meta.url), 'utf8');

  assert.match(menuSource, /workspace-menu-root/);
  assert.match(menuSource, /workspace-menu-trigger/);
  assert.match(menuSource, /workspace-menu-panel/);
  assert.match(menuSource, /workspace-menu-item/);
  assert.match(menuSource, /currentPath === '\/chat'/);
  assert.match(menuSource, /navigateTo\('\/chat'\)/);
  assert.match(menuSource, /targetPath !== currentPath/);
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
  assert.match(source, /IF\(executed_result_json IS NULL, 0, 1\) AS has_executed_result_json/);
  assert.match(source, /export async function getAgentQueryLogDetail/);
  assert.match(source, /SELECT[\s\S]*executed_result_json[\s\S]*FROM agent_query_log[\s\S]*WHERE query_id = \?/);
});

test('query log page loads wide SQL and result payloads on demand', () => {
  const apiSource = readFileSync(new URL('../workspace/services/agentLogApi.ts', import.meta.url), 'utf8');
  const pageSource = readFileSync(new URL('../workspace/components/AgentLogPage.tsx', import.meta.url), 'utf8');

  assert.match(apiSource, /export async function fetchAgentQueryLogDetail/);
  assert.match(apiSource, /\/api\/developer\/agent\/query-logs\/\$\{encodeURIComponent\(queryId\)\}/);
  assert.match(pageSource, /fetchAgentQueryLogDetail/);
  assert.match(pageSource, /detailCache/);
  assert.match(pageSource, /onToggle/);
});

test('database query log docs include request and routing context fields', () => {
  const docsSource = readFileSync(
    new URL('../../../infra/mysql/docs/agent_query_log.md', import.meta.url),
    'utf8',
  );
  const ddlSource = readFileSync(
    new URL('../../../infra/mysql/init/001_init_tables.sql', import.meta.url),
    'utf8',
  );

  assert.match(docsSource, /`request_text`/);
  assert.match(docsSource, /`response_text`/);
  assert.match(docsSource, /`input_type`/);
  assert.match(docsSource, /`intent`/);
  assert.match(docsSource, /`answer_type`/);
  assert.match(docsSource, /`final_status`/);
  assert.match(docsSource, /`executed_result_json`/);
  assert.match(ddlSource, /request_text\s+TEXT\s+NULL/i);
  assert.match(ddlSource, /response_text\s+TEXT\s+NULL/i);
  assert.match(ddlSource, /input_type\s+VARCHAR\(32\)\s+NULL/i);
  assert.match(ddlSource, /intent\s+VARCHAR\(64\)\s+NULL/i);
  assert.match(ddlSource, /answer_type\s+VARCHAR\(64\)\s+NULL/i);
  assert.match(ddlSource, /final_status\s+VARCHAR\(64\)\s+NULL/i);
  assert.match(ddlSource, /executed_result_json\s+JSON\s+NULL/i);
  assert.doesNotMatch(docsSource, /result_preview_json\s+JSON\s+NULL/i);
});

test('region alias and acceptance docs live in dedicated non-plan directories', () => {
  const readmeSource = readFileSync(new URL('../../agent/plans/1/README.md', import.meta.url), 'utf8');
  const mainPlanSource = readFileSync(
    new URL('../../agent/plans/1/1.plan.md', import.meta.url),
    'utf8',
  );
  const matrixSource = readFileSync(
    new URL('../../../docs/testing/agent/soil-moisture/acceptance-test-matrix.md', import.meta.url),
    'utf8',
  );
  const planSource = readFileSync(
    new URL('../../../infra/mysql/docs/region-alias-resolution.md', import.meta.url),
    'utf8',
  );

  assert.match(readmeSource, /infra\/mysql\/docs\/README\.md/);
  assert.match(readmeSource, /docs\/testing\/agent\/soil-moisture\/README\.md/);
  assert.match(mainPlanSource, /region_alias/);
  assert.match(mainPlanSource, /infra\/mysql\/docs\/region-alias-resolution\.md/);
  assert.match(mainPlanSource, /docs\/testing\/agent\/soil-moisture\/acceptance-test-matrix\.md/);
  assert.match(matrixSource, /testdata\/agent\/soil-moisture\/case-library\.md/);
  assert.match(planSource, /地区别名解析与 `region_alias` 使用设计/);
  assert.match(planSource, /南京[\s\S]*南京市/);
  assert.match(planSource, /静态种子/);
  assert.match(planSource, /多候选/);
  assert.match(planSource, /一编辑距离/);
});

test('system design doc reflects current region alias implementation', () => {
  const planSource = readFileSync(
    new URL('../../agent/plans/1/7.system-design-diagram.md', import.meta.url),
    'utf8',
  );

  assert.match(planSource, /RegionAliasResolver \+ region_alias\(city\/county\) \+ fact_soil_moisture 存在性校验/);
  assert.doesNotMatch(planSource, /结构化维表映射/);
});

test('soil moisture testing docs use testdata case library as the single formal case source', () => {
  const testingReadmeSource = readFileSync(
    new URL('../../../docs/testing/agent/soil-moisture/README.md', import.meta.url),
    'utf8',
  );
  const acceptanceSource = readFileSync(
    new URL('../../../docs/testing/agent/soil-moisture/acceptance-test-matrix.md', import.meta.url),
    'utf8',
  );
  const regressionSource = readFileSync(
    new URL('../../../docs/testing/agent/soil-moisture/regression-case-guide.md', import.meta.url),
    'utf8',
  );
  const testdataReadmeSource = readFileSync(
    new URL('../../../testdata/agent/soil-moisture/README.md', import.meta.url),
    'utf8',
  );
  const caseLibrarySource = readFileSync(
    new URL('../../../testdata/agent/soil-moisture/case-library.md', import.meta.url),
    'utf8',
  );

  assert.match(testingReadmeSource, /testdata\/agent\/soil-moisture\/case-library\.md/);
  assert.match(acceptanceSource, /testdata\/agent\/soil-moisture\/case-library\.md/);
  assert.match(regressionSource, /testdata\/agent\/soil-moisture\/case-library\.md/);
  assert.match(testdataReadmeSource, /case-library\.md/);
  assert.match(caseLibrarySource, /130 个正式 Case/);
  assert.match(caseLibrarySource, /按业务价值和真实使用频率加权/);
  assert.match(caseLibrarySource, /### SH-01/);
  assert.match(caseLibrarySource, /### DT-18/);
  assert.match(caseLibrarySource, /### WA-16/);
  assert.match(caseLibrarySource, /### BO-05/);
  assert.equal([...caseLibrarySource.matchAll(/^### /gm)].length, 130);
  assert.equal([...caseLibrarySource.matchAll(/^### SH-/gm)].length, 6);
  assert.equal([...caseLibrarySource.matchAll(/^### DT-/gm)].length, 18);
  assert.equal([...caseLibrarySource.matchAll(/^### BO-/gm)].length, 5);
  assert.doesNotMatch(acceptanceSource, /44 个典型 Case/);
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
