import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readdirSync, readFileSync } from 'node:fs';

const initDir = new URL('../../../infra/mysql/init/', import.meta.url);
const localDir = new URL('../../../infra/mysql/local/', import.meta.url);
const repoRoot = new URL('../../..', import.meta.url);

function read(relativePath) {
  return readFileSync(new URL(relativePath, repoRoot), 'utf8');
}

test('docker mysql init contains only schema and business insert sql files', () => {
  const sqlFiles = readdirSync(initDir).filter((name) => name.endsWith('.sql')).sort();

  assert.deepEqual(sqlFiles, ['001_init_tables.sql', '002_insert_data.sql']);
});

test('executable mysql init sql never contains real authentication seed hashes', () => {
  const sqlFiles = readdirSync(initDir).filter((name) => name.endsWith('.sql')).sort();
  const combined = sqlFiles.map((name) => read(`infra/mysql/init/${name}`)).join('\n');

  assert.doesNotMatch(combined, /INSERT\s+INTO\s+auth_user/i);
  assert.doesNotMatch(combined, /password_hash\s*=\s*VALUES\(password_hash\)/i);
  assert.doesNotMatch(combined, /password_salt\s*=\s*VALUES\(password_salt\)/i);
  assert.doesNotMatch(combined, /admin123456/i);
  assert.doesNotMatch(combined, /gago-admin.+13553bbfe83a68421de15373a6ca4555/is);
});

test('business insert sql seeds rules templates and soil facts idempotently', () => {
  const insertSql = read('infra/mysql/init/002_insert_data.sql');

  assert.match(insertSql, /INSERT INTO etl_import_batch/i);
  assert.match(insertSql, /INSERT INTO metric_rule/i);
  assert.match(insertSql, /INSERT INTO warning_template/i);
  assert.match(insertSql, /INSERT INTO fact_soil_moisture/i);
  assert.match(insertSql, /ON DUPLICATE KEY UPDATE/i);
  assert.match(insertSql, /土壤墒情仪数据\(2\)\.xlsx/);
});

test('local-only auth seed template is outside docker init execution path', () => {
  assert.equal(existsSync(new URL('README.md', localDir)), true);
  assert.equal(existsSync(new URL('seed_auth_users.local.sql.example', localDir)), true);

  const template = read('infra/mysql/local/seed_auth_users.local.sql.example');
  assert.match(template, /password_hash/i);
  assert.match(template, /REPLACE_WITH_/);
  assert.doesNotMatch(template, /13553bbfe83a68421de15373a6ca4555/i);
});

test('local init script exists and reads mysql credentials from environment', () => {
  const script = read('scripts/db/apply-local-init.sh');

  assert.match(script, /MYSQL_HOST/);
  assert.match(script, /MYSQL_USER/);
  assert.match(script, /MYSQL_PASSWORD/);
  assert.match(script, /001_init_tables\.sql/);
  assert.match(script, /002_insert_data\.sql/);
  assert.doesNotMatch(script, /smart_agriculture_pwd/);
  assert.doesNotMatch(script, /root_pwd/);
});

test('local init script can optionally import external soil excel into localhost mysql', () => {
  const script = read('scripts/db/apply-local-init.sh');

  assert.match(script, /SOIL_EXCEL_SOURCE/);
  assert.match(script, /import-local-soil-excel\.mjs/);
  assert.doesNotMatch(script, /\/Users\/mac\/Desktop\/gago-cloud/);
});

test('local auth bootstrap uses gitignored json config instead of committed real hashes', () => {
  assert.equal(existsSync(new URL('../scripts/seed-local-auth-users.mjs', import.meta.url)), true);
  assert.equal(existsSync(new URL('../../../infra/mysql/local/auth_users.local.json.example', import.meta.url)), true);

  const script = read('apps/web/scripts/seed-local-auth-users.mjs');
  const template = read('infra/mysql/local/auth_users.local.json.example');

  assert.match(script, /hashPassword/);
  assert.match(script, /auth_users\.local\.json/);
  assert.match(script, /INSERT INTO auth_user/i);
  assert.match(template, /REPLACE_WITH_USERNAME/);
  assert.match(template, /REPLACE_WITH_PASSWORD/);
  assert.doesNotMatch(template, /gago-admin/);
});

test('full excel import replaces same-source demo rows before loading localhost mysql', () => {
  const script = read('apps/web/scripts/import-local-soil-excel.mjs');

  assert.match(script, /DELETE FROM fact_soil_moisture WHERE source_file = \?/);
});
