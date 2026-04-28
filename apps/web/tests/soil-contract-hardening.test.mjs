import test from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import path from 'node:path';

const repoRoot = new URL('../../..', import.meta.url);

function read(relativePath) {
  return readFileSync(new URL(relativePath, repoRoot), 'utf8');
}

function walk(relativePath) {
  const normalizedPath = relativePath.replace(/\/$/, '');
  const absolutePath = new URL(`${normalizedPath}/`, repoRoot);
  const entries = readdirSync(absolutePath);
  const files = [];
  for (const entry of entries) {
    const entryRelativePath = path.posix.join(normalizedPath, entry);
    const entryAbsolutePath = new URL(entryRelativePath, repoRoot);
    if (statSync(entryAbsolutePath).isDirectory()) {
      if (
        entry === '__pycache__'
        || entry === '.git'
        || entry === '.next'
        || entry === '.runtime'
        || entry === 'node_modules'
        || entry === 'output'
        || entry === 'outputs'
      ) {
        continue;
      }
      files.push(...walk(entryRelativePath));
      continue;
    }
    files.push(entryRelativePath);
  }
  return files;
}

function markdownFieldNames(relativePath) {
  return read(relativePath)
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.startsWith('| `'))
    .map((line) => line.split('|')[1]?.trim().replaceAll('`', ''))
    .filter(Boolean);
}

function sqlColumns(tableName) {
  const sql = read('infra/mysql/init/001_init_tables.sql');
  const match = sql.match(new RegExp(`CREATE TABLE IF NOT EXISTS ${tableName} \\(([\\s\\S]*?)\\n\\);`, 'i'));
  assert.ok(match, `missing table block for ${tableName}`);
  return match[1]
    .split('\n')
    .map((line) => line.trim().replace(/,$/, ''))
    .filter((line) => /^[a-z]/.test(line))
    .map((line) => line.match(/^`?([a-z0-9_]+)`?\s+/i)?.[1])
    .filter(Boolean);
}

function legacyTokens() {
  return [
    ['record', '_id'],
    ['batch', '_id'],
    ['device', '_sn'],
    ['device', '_name'],
    ['city', '_name'],
    ['county', '_name'],
    ['town', '_name'],
    ['sample', '_time'],
    ['soil', '_anomaly', '_type'],
    ['soil', '_anomaly', '_score'],
    ['long', 'itude'],
    ['lat', 'itude'],
    ['parent', '_county', '_name'],
    ['latest', '_batch'],
  ].map((parts) => parts.join(''));
}

test('database docs stay aligned with current ddl columns', () => {
  assert.deepEqual(markdownFieldNames('infra/mysql/docs/fact_soil_moisture.md'), sqlColumns('fact_soil_moisture'));
  assert.deepEqual(markdownFieldNames('infra/mysql/docs/region_alias.md'), sqlColumns('region_alias'));
  assert.deepEqual(
    markdownFieldNames('infra/mysql/docs/soil_import_job.md'),
    [...sqlColumns('soil_import_job'), ...sqlColumns('soil_import_job_diff')],
  );
  assert.deepEqual(markdownFieldNames('infra/mysql/docs/warning_template.md'), sqlColumns('warning_template'));
});

test('legacy soil field names no longer remain in runtime docs tests or cases', () => {
  const targets = [
    ...walk('apps'),
    ...walk('infra/mysql/docs'),
    ...walk('docs/testing'),
    ...walk('testdata'),
  ].filter((filePath) => {
    if (
      filePath.endsWith('.png')
      || filePath.endsWith('.jpg')
      || filePath.endsWith('.jpeg')
      || filePath.endsWith('.xlsx')
      || filePath.endsWith('.pyc')
    ) {
      return false;
    }
    return !readFileSync(new URL(filePath, repoRoot)).includes(0);
  });

  for (const filePath of targets) {
    const content = read(filePath);
    for (const token of legacyTokens()) {
      assert.doesNotMatch(content, new RegExp(`\\b${token}\\b`), `${filePath} still contains ${token}`);
    }
  }
});

test('template placeholders and required fields stay inside current runtime contract', () => {
  const allowedTemplateFields = new Set(['year', 'month', 'day', 'hour', 'city', 'county', 'sn', 'water20cm', 'warning_level']);
  const seedSql = read('infra/mysql/init/002_insert_data.sql');
  const templateFile = read('apps/agent/app/templates/soil_warning.j2');

  const requiredFields = [...seedSql.matchAll(/JSON_ARRAY\(([^)]+)\)/g)]
    .flatMap((match) => [...match[1].matchAll(/'([^']+)'/g)].map((item) => item[1]));
  for (const field of requiredFields) {
    assert.ok(allowedTemplateFields.has(field), `unexpected required template field ${field}`);
  }

  const placeholders = [...templateFile.matchAll(/\{\{\s*([a-zA-Z0-9_]+)\s*\}\}/g)].map((match) => match[1]);
  for (const field of placeholders) {
    assert.ok(allowedTemplateFields.has(field), `unexpected template placeholder ${field}`);
  }
});

test('soil query chain orders and filters by create_time', () => {
  const repositorySource = read('apps/agent/app/repositories/soil_repository.py');
  const adminRepositorySource = read('apps/web/lib/server/soilAdminRepository.mjs');
  const adminStoreSource = read('apps/web/lib/server/soilAdminStore.mjs');

  assert.match(repositorySource, /\("create_time", ">=", "start_time", start_time\)/);
  assert.match(repositorySource, /\("create_time", "<=", "end_time", end_time\)/);
  assert.match(repositorySource, /ORDER BY create_time DESC/);
  assert.match(adminRepositorySource, /create_time >= \?/);
  assert.match(adminRepositorySource, /create_time <= \?/);
  assert.match(adminRepositorySource, /ORDER BY create_time DESC/);
  assert.match(adminStoreSource, /query\.create_time_from/);
  assert.match(adminStoreSource, /query\.create_time_to/);
});
