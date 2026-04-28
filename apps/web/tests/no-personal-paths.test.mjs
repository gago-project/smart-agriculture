import test from 'node:test';
import assert from 'node:assert/strict';
import { lstatSync, readdirSync, readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const testDir = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(testDir, '../../..');
const gagoCloudRoot = resolve(repoRoot, '../..');
const blockedPathFragments = [
  ['', 'Users', 'mac', ''].join('/'),
  ['', 'Users', 'mac', 'Desktop', 'gago-cloud'].join('/'),
];
const ignoredDirectories = new Set([
  '.agents',
  '.claude',
  '.codex',
  '.cursor',
  '.git',
  '.next',
  '.runtime',
  '.venv',
  '.npm-cache',
  '.worktrees',
  '__pycache__',
  'mysql-data',
  'node_modules',
  'output',
  'outputs',
]);

function listTextFiles(directory) {
  const files = [];
  for (const entry of readdirSync(directory)) {
    if (entry === '.DS_Store') {
      continue;
    }
    const path = join(directory, entry);
    const stat = lstatSync(path);
    if (stat.isDirectory()) {
      if (!ignoredDirectories.has(entry)) {
        files.push(...listTextFiles(path));
      }
      continue;
    }
    if (!stat.isFile()) {
      continue;
    }
    const buffer = readFileSync(path);
    if (!buffer.includes(0)) {
      files.push(path);
    }
  }
  return files;
}

test('workspace text files do not expose personal macOS paths', () => {
  const violations = [];
  for (const file of listTextFiles(gagoCloudRoot)) {
    const content = readFileSync(file, 'utf8');
    for (const blockedPath of blockedPathFragments) {
      if (content.includes(blockedPath)) {
        violations.push(file);
        break;
      }
    }
  }

  assert.deepEqual(violations.sort(), [], `Personal paths found in:\n${violations.sort().join('\n')}`);
});
