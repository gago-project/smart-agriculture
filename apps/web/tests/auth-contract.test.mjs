import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';

const authSource = readFileSync(new URL('../lib/server/auth.mjs', import.meta.url), 'utf8');
const repositorySource = readFileSync(new URL('../lib/server/soilAdminRepository.mjs', import.meta.url), 'utf8');
const adminStoreSource = readFileSync(new URL('../lib/server/soilAdminStore.mjs', import.meta.url), 'utf8');
const healthScriptSource = readFileSync(new URL('../../../scripts/health/check-local.sh', import.meta.url), 'utf8');

test('auth uses database-backed storage instead of file-based sessions or configured users', () => {
  assert.doesNotMatch(authSource, /configuredUsers/);
  assert.doesNotMatch(authSource, /auth-sessions\.json/);
  assert.doesNotMatch(authSource, /APP_ADMIN_USERNAME/);
  assert.doesNotMatch(authSource, /APP_ADMIN_PASSWORD/);
});

test('admin repository no longer falls back to runtime file state', () => {
  assert.doesNotMatch(repositorySource, /loadAdminState/);
  assert.doesNotMatch(repositorySource, /saveAdminState/);
});

test('soil admin paginated listing avoids prepared execute for LIMIT/OFFSET', () => {
  assert.match(
    repositorySource,
    /const \[rows\] = await connection\.query\([\s\S]*ORDER BY sample_time DESC[\s\S]*LIMIT \? OFFSET \?/,
  );
});

test('soil admin store is pure helpers without runtime file persistence', () => {
  assert.doesNotMatch(adminStoreSource, /soil-admin-state\.json/);
  assert.doesNotMatch(adminStoreSource, /runtimeDir/);
  assert.doesNotMatch(adminStoreSource, /fs\/promises/);
});

test('admin routes require admin role instead of generic authenticated user', () => {
  const adminRoutes = [
    '../app/api/admin/soil/records/route.ts',
    '../app/api/admin/soil/records/[recordId]/route.ts',
    '../app/api/admin/soil/records/bulk-delete/route.ts',
    '../app/api/admin/soil/rules/route.ts',
    '../app/api/admin/soil/upload/route.ts',
  ];

  for (const route of adminRoutes) {
    const source = readFileSync(new URL(route, import.meta.url), 'utf8');
    assert.match(source, /requireAdminRequestUser/);
    assert.doesNotMatch(source, /requireRequestUser/);
  }
});

test('developer log route allows admin and developer roles only', () => {
  const authHelperSource = readFileSync(new URL('../lib/server/auth.mjs', import.meta.url), 'utf8');
  const routeSource = readFileSync(new URL('../app/api/developer/agent/query-logs/route.ts', import.meta.url), 'utf8');

  assert.match(authHelperSource, /export async function requireRoleRequestUser/);
  assert.match(routeSource, /requireRoleRequestUser/);
  assert.match(routeSource, /'admin'/);
  assert.match(routeSource, /'developer'/);
  assert.doesNotMatch(routeSource, /requireAdminRequestUser/);
});

test('local health smoke uses the seeded database admin account', () => {
  assert.match(healthScriptSource, /HEALTH_USERNAME=\$\{HEALTH_USERNAME:-gago-admin\}/);
  assert.doesNotMatch(healthScriptSource, /HEALTH_USERNAME=\$\{HEALTH_USERNAME:-admin\}/);
  assert.doesNotMatch(healthScriptSource, /admin123456/);
});

test('auth credential seeds are kept out of executable docker init sql', () => {
  assert.equal(existsSync(new URL('../../../infra/mysql/init/003_seed_auth_users.sql', import.meta.url)), false);
  assert.equal(existsSync(new URL('../../../infra/mysql/local/seed_auth_users.local.sql.example', import.meta.url)), true);
});
