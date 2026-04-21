import test from 'node:test';
import assert from 'node:assert/strict';

import { createAuthService, hashPassword, verifyPassword, hashToken } from '../lib/server/authCore.mjs';

class MemoryAuthRepository {
  constructor() {
    this.users = new Map();
    this.sessions = new Map();
    this.nextId = 1;
  }

  async getUserByUsername(username) {
    return this.users.get(username) ?? null;
  }

  async createUser({ username, passwordHash, passwordSalt, role = 'user', isActive = true }) {
    const user = {
      id: this.nextId++,
      username,
      password_hash: passwordHash,
      password_salt: passwordSalt,
      role,
      is_active: isActive ? 1 : 0,
    };
    this.users.set(username, user);
    return { ...user };
  }

  async createSession({ userId, tokenHash, expiresAt }) {
    this.sessions.set(tokenHash, { user_id: userId, expires_at: expiresAt, last_used_at: expiresAt });
  }

  async getUserByToken(tokenHash) {
    const session = this.sessions.get(tokenHash);
    if (!session) return null;
    const user = [...this.users.values()].find((item) => item.id === session.user_id);
    if (!user || !user.is_active) return null;
    return {
      id: user.id,
      username: user.username,
      role: user.role,
      is_active: user.is_active,
    };
  }

  async touchSession(tokenHash, lastUsedAt) {
    const session = this.sessions.get(tokenHash);
    if (session) session.last_used_at = lastUsedAt;
  }

  async deleteSession(tokenHash) {
    this.sessions.delete(tokenHash);
  }
}

test('hashPassword and verifyPassword round-trip a password', () => {
  const { passwordHash, passwordSalt } = hashPassword('by4rZw5zZa^NzTrhUwJE=U5c');

  assert.equal(typeof passwordHash, 'string');
  assert.equal(typeof passwordSalt, 'string');
  assert.equal(verifyPassword('by4rZw5zZa^NzTrhUwJE=U5c', passwordHash, passwordSalt), true);
  assert.equal(verifyPassword('wrong-password', passwordHash, passwordSalt), false);
});

test('hashToken is deterministic and does not return the raw token', () => {
  const raw = 'plain-token';
  const hashed = hashToken(raw);

  assert.equal(hashed === hashToken(raw), true);
  assert.notEqual(hashed, raw);
});

test('auth service logs in against repository users and persists hashed sessions', async () => {
  const repository = new MemoryAuthRepository();
  const { passwordHash, passwordSalt } = hashPassword('2aZ8gx-pbXQsxXv4Mf9Q');
  await repository.createUser({
    username: 'gago-1',
    passwordHash,
    passwordSalt,
    role: 'user',
  });

  const auth = createAuthService({ repository, sessionTtlDays: 7 });
  const session = await auth.login('gago-1', '2aZ8gx-pbXQsxXv4Mf9Q');

  assert.equal(session.user.username, 'gago-1');
  assert.equal(session.user.role, 'user');
  assert.ok(session.token);
  assert.equal(repository.sessions.has(hashToken(session.token)), true);
});

test('auth service authenticates and logs out by hashed token', async () => {
  const repository = new MemoryAuthRepository();
  const { passwordHash, passwordSalt } = hashPassword('by4rZw5zZa^NzTrhUwJE=U5c');
  const user = await repository.createUser({
    username: 'gago-admin',
    passwordHash,
    passwordSalt,
    role: 'admin',
  });
  await repository.createSession({
    userId: user.id,
    tokenHash: hashToken('session-token'),
    expiresAt: new Date(Date.now() + 60_000).toISOString(),
  });

  const auth = createAuthService({ repository, sessionTtlDays: 7 });
  const currentUser = await auth.authenticate('session-token');
  assert.deepEqual(currentUser, { id: user.id, username: 'gago-admin', role: 'admin' });

  await auth.logout('session-token');
  assert.equal(repository.sessions.has(hashToken('session-token')), false);
});
