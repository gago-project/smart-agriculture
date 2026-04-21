import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { dirname, resolve } from 'node:path';
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
