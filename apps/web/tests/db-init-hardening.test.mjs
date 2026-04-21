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

  assert.deepEqual(sqlFiles, ['001_init_tables.sql', '002_insert_data.sql', '003_insert_soil_data.sql']);
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

test('business insert sql seeds rules and templates idempotently', () => {
  const insertSql = read('infra/mysql/init/002_insert_data.sql');

  assert.match(insertSql, /SET NAMES utf8mb4/i);
  assert.match(insertSql, /SET character_set_client = utf8mb4/i);
  assert.match(insertSql, /INSERT INTO metric_rule/i);
  assert.match(insertSql, /INSERT INTO warning_template/i);
  assert.match(insertSql, /ON DUPLICATE KEY UPDATE/i);
  assert.doesNotMatch(insertSql, /INSERT INTO etl_import_batch/i);
  assert.doesNotMatch(insertSql, /INSERT INTO fact_soil_moisture/i);
});

test('business insert sql keeps Chinese seed text in utf8 and avoids mojibake', () => {
  const insertSql = read('infra/mysql/init/002_insert_data.sql');

  assert.match(insertSql, /墒情异常分析规则V1/);
  assert.match(insertSql, /墒情预警模板V1/);
  assert.doesNotMatch(insertSql, /å|æ|ä|Ž|é|è|ç/);
});

test('full soil data sql seeds import batch and fact rows idempotently', () => {
  const insertSql = read('infra/mysql/init/003_insert_soil_data.sql');

  assert.match(insertSql, /SET NAMES utf8mb4/i);
  assert.match(insertSql, /DELETE FROM fact_soil_moisture WHERE source_file = '土壤墒情仪数据\(2\)\.xlsx'/i);
  assert.match(insertSql, /DELETE FROM etl_import_batch WHERE source_file = '土壤墒情仪数据\(2\)\.xlsx'/i);
  assert.match(insertSql, /INSERT INTO etl_import_batch/i);
  assert.match(insertSql, /INSERT INTO fact_soil_moisture/i);
  assert.match(insertSql, /145066/);
});

test('full soil data sql includes static region alias seed generated from facts', () => {
  const insertSql = read('infra/mysql/init/003_insert_soil_data.sql');

  assert.match(insertSql, /BEGIN GENERATED REGION_ALIAS SEED/i);
  assert.match(insertSql, /INSERT INTO region_alias/i);
  assert.match(insertSql, /'南京'\s*,\s*'南京市'\s*,\s*'city'/);
  assert.match(insertSql, /'如东'\s*,\s*'如东县'\s*,\s*'county'/);
  assert.match(insertSql, /ON DUPLICATE KEY UPDATE/i);
});

test('region alias seed generator exists for refreshing static init sql', () => {
  const script = read('apps/web/scripts/generate-region-alias-seed.mjs');

  assert.match(script, /fact_soil_moisture/i);
  assert.match(script, /region_alias/i);
  assert.match(script, /alias_source/i);
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
  assert.match(script, /MYSQL_APPLY_USER:-\$\{MYSQL_USER:-\$\{MYSQL_ROOT_USER:-root\}\}/);
  assert.match(script, /MYSQL_APPLY_PASSWORD:-\$\{MYSQL_PASSWORD:-\$\{MYSQL_ROOT_PASSWORD:-/);
  assert.match(script, /001_init_tables\.sql/);
  assert.match(script, /002_insert_data\.sql/);
  assert.match(script, /003_insert_soil_data\.sql/);
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
