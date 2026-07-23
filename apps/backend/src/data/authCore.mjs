import crypto from 'node:crypto';

const PASSWORD_SCRYPT_OPTIONS = {
  N: 2 ** 14,
  r: 8,
  p: 1,
};

function compareHex(left, right) {
  try {
    const leftBuffer = Buffer.from(String(left || ''), 'hex');
    const rightBuffer = Buffer.from(String(right || ''), 'hex');
    if (leftBuffer.length === 0 || leftBuffer.length !== rightBuffer.length) {
      return false;
    }
    return crypto.timingSafeEqual(leftBuffer, rightBuffer);
  } catch {
    return false;
  }
}

function publicUser(user) {
  return {
    id: Number(user.id),
    username: String(user.username),
    role: String(user.role || 'user'),
  };
}

export function hashPassword(password, saltHex = crypto.randomBytes(16).toString('hex')) {
  const passwordHash = crypto
    .scryptSync(String(password), Buffer.from(saltHex, 'hex'), 64, PASSWORD_SCRYPT_OPTIONS)
    .toString('hex');
  return {
    passwordHash,
    passwordSalt: saltHex,
  };
}

export function verifyPassword(password, passwordHash, passwordSalt) {
  const candidate = hashPassword(password, passwordSalt);
  return compareHex(candidate.passwordHash, passwordHash);
}

export function hashToken(token) {
  return crypto.createHash('sha256').update(String(token)).digest('hex');
}

function generateSessionToken() {
  return crypto.randomBytes(32).toString('base64url');
}

export function createAuthService({ repository, sessionTtlDays = 7, now = () => new Date() }) {
  return {
    async login(username, password) {
      const user = await repository.getUserByUsername(String(username || '').trim());
      if (!user || !user.is_active) {
        throw new Error('用户名或密码错误');
      }
      if (!verifyPassword(String(password || ''), user.password_hash, user.password_salt)) {
        throw new Error('用户名或密码错误');
      }

      const token = generateSessionToken();
      const tokenHash = hashToken(token);
      const expiresAt = new Date(now().getTime() + Math.max(1, sessionTtlDays) * 24 * 60 * 60 * 1000).toISOString();

      await repository.createSession({
        userId: Number(user.id),
        tokenHash,
        expiresAt,
      });

      return {
        token,
        expires_at: expiresAt,
        user: publicUser(user),
      };
    },

    async authenticate(token) {
      const normalized = String(token || '').trim();
      if (!normalized) return null;
      const tokenHash = hashToken(normalized);
      const user = await repository.getUserByToken(tokenHash);
      if (!user) return null;
      await repository.touchSession(tokenHash, now().toISOString());
      return publicUser(user);
    },

    async logout(token) {
      const normalized = String(token || '').trim();
      if (!normalized) return;
      await repository.deleteSession(hashToken(normalized));
    },
  };
}
