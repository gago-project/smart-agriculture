import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { dirname, join, resolve } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';

const testDir = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(testDir, '../../..');
const helperPath = resolve(repoRoot, 'scripts/dev/load-root-env.sh');
const startLocalAgentPath = resolve(repoRoot, 'scripts/dev/start-local-agent.sh');
const startLocalWebPath = resolve(repoRoot, 'scripts/dev/start-local-web.sh');
const rootPackagePath = resolve(repoRoot, 'package.json');

test('local env loader exports root .env values for local scripts', () => {
  const command = `source "${helperPath}" && printf '%s\\n%s\\n' "$MYSQL_HOST" "$NEXT_PUBLIC_APP_NAME"`;
  const env = {
    ...process.env,
    MYSQL_HOST: '',
    NEXT_PUBLIC_APP_NAME: '',
  };

  delete env.npm_config_prefix;
  delete env.NPM_CONFIG_PREFIX;

  const result = spawnSync('bash', ['-c', command], {
    cwd: repoRoot,
    encoding: 'utf8',
    env,
  });

  assert.equal(result.status, 0, result.stderr);

  const [mysqlHost, appName] = result.stdout.trim().split('\n');
  assert.equal(mysqlHost, '127.0.0.1');
  assert.equal(appName, 'Smart Agriculture');
});

test('local env loader prefers macOS Keychain for secret api keys over root .env', () => {
  const fakeBin = mkdtempSync(join(tmpdir(), 'smart-agriculture-security-'));
  const fakeSecurity = join(fakeBin, 'security');
  writeFileSync(
    fakeSecurity,
    `#!/usr/bin/env bash
if [ "$1" != "find-generic-password" ]; then exit 1; fi
service=""
account=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    -s) service="$2"; shift 2 ;;
    -a) account="$2"; shift 2 ;;
    *) shift ;;
  esac
done
if [ "$service" = "smart-agriculture-local" ] && [ "$account" = "QWEN_API_KEY" ]; then
  printf 'mock-qwen-from-keychain'
  exit 0
fi
if [ "$service" = "smart-agriculture-local" ] && [ "$account" = "SONIOX_API_KEY" ]; then
  printf 'mock-soniox-from-keychain'
  exit 0
fi
exit 44
`,
    { mode: 0o700 }
  );

  const command = `source "${helperPath}" && printf '%s\\n%s\\n' "$QWEN_API_KEY" "$SONIOX_API_KEY"`;
  const env = {
    ...process.env,
    PATH: `${fakeBin}:${process.env.PATH}`,
    QWEN_API_KEY: '',
    SONIOX_API_KEY: '',
  };

  delete env.npm_config_prefix;
  delete env.NPM_CONFIG_PREFIX;

  const result = spawnSync('bash', ['-c', command], {
    cwd: repoRoot,
    encoding: 'utf8',
    env,
  });

  assert.equal(result.status, 0, result.stderr);
  const [qwenKey, sonioxKey] = result.stdout.trim().split('\n');
  if (qwenKey !== 'mock-qwen-from-keychain') {
    throw new Error('QWEN_API_KEY was not loaded from the mocked Keychain value');
  }
  if (sonioxKey !== 'mock-soniox-from-keychain') {
    throw new Error('SONIOX_API_KEY was not loaded from the mocked Keychain value');
  }
});

test('local start scripts source the shared root env loader', () => {
  const agentSource = readFileSync(startLocalAgentPath, 'utf8');
  const webSource = readFileSync(startLocalWebPath, 'utf8');

  assert.match(agentSource, /load-root-env\.sh/);
  assert.match(webSource, /load-root-env\.sh/);
});

test('root package local scripts source the shared root env loader', () => {
  const packageJson = JSON.parse(readFileSync(rootPackagePath, 'utf8'));
  const scripts = packageJson.scripts ?? {};

  assert.match(scripts['dev:web'] ?? '', /load-root-env\.sh/);
  assert.match(scripts['dev:agent'] ?? '', /load-root-env\.sh/);
  assert.match(scripts['start:web'] ?? '', /load-root-env\.sh/);
  assert.match(scripts['start:agent'] ?? '', /load-root-env\.sh/);
  assert.match(scripts['dev:agent'] ?? '', /AGENT_PORT/);
  assert.match(scripts['start:agent'] ?? '', /AGENT_PORT/);
});
