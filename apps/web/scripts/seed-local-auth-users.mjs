import { existsSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { hashPassword } from '../lib/server/authCore.mjs';
import { withMysqlConnection } from '../lib/server/mysql.mjs';

const scriptDir = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(scriptDir, '../../..');
const defaultConfigPath = resolve(repoRoot, 'infra/mysql/local/auth_users.local.json');

function normalizePath(pathValue) {
  if (!pathValue) {
    return '';
  }
  if (pathValue.startsWith('/')) {
    return pathValue;
  }
  return resolve(repoRoot, pathValue);
}

function resolveConfigPath() {
  const configured = String(process.env.LOCAL_AUTH_USERS_JSON || '').trim();
  if (configured) {
    return normalizePath(configured);
  }
  if (existsSync(defaultConfigPath)) {
    return defaultConfigPath;
  }
  throw new Error('未找到 LOCAL_AUTH_USERS_JSON，也未检测到 infra/mysql/local/auth_users.local.json');
}

function loadUserSeeds(configPath) {
  const parsed = JSON.parse(readFileSync(configPath, 'utf8'));
  if (!Array.isArray(parsed) || parsed.length === 0) {
    throw new Error('本地账号配置必须是非空 JSON 数组');
  }
  return parsed.map((item, index) => {
    const username = String(item.username || '').trim();
    const password = String(item.password || '');
    if (!username || username.includes('REPLACE_WITH_')) {
      throw new Error(`第 ${index + 1} 个本地账号缺少有效 username`);
    }
    if (!password || password.includes('REPLACE_WITH_')) {
      throw new Error(`第 ${index + 1} 个本地账号缺少有效 password`);
    }
    return {
      username,
      password,
      role: String(item.role || 'user').trim() || 'user',
      isActive: item.is_active === false ? 0 : 1,
    };
  });
}

async function main() {
  const configPath = resolveConfigPath();
  if (!existsSync(configPath)) {
    throw new Error(`本地账号 JSON 不存在：${configPath}`);
  }
  const users = loadUserSeeds(configPath);
  const rows = users.map((user) => {
    const hashed = hashPassword(user.password);
    return {
      username: user.username,
      passwordHash: hashed.passwordHash,
      passwordSalt: hashed.passwordSalt,
      role: user.role,
      isActive: user.isActive,
    };
  });

  const placeholders = rows.map(() => '(?, ?, ?, ?, ?, NOW(), NOW())').join(', ');
  const values = rows.flatMap((row) => [
    row.username,
    row.passwordHash,
    row.passwordSalt,
    row.role,
    row.isActive,
  ]);

  await withMysqlConnection(async (connection) => {
    await connection.execute(
      `INSERT INTO auth_user (
         username,
         password_hash,
         password_salt,
         role,
         is_active,
         created_at,
         updated_at
       ) VALUES ${placeholders}
       ON DUPLICATE KEY UPDATE
         password_hash = VALUES(password_hash),
         password_salt = VALUES(password_salt),
         role = VALUES(role),
         is_active = VALUES(is_active),
         updated_at = NOW()`,
      values,
    );
  });

  console.log(JSON.stringify({ seeded_users: rows.length, source: 'infra/mysql/local/auth_users.local.json' }));
}

await main();
