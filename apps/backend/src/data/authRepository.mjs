import { withMysqlConnection } from './mysql.mjs';

export function createMysqlAuthRepository() {
  return {
    async getUserByUsername(username) {
      return await withMysqlConnection(async (connection) => {
        const [rows] = await connection.execute(
          `SELECT id, username, password_hash, password_salt, role, is_active
           FROM auth_user
           WHERE username = ?
           LIMIT 1`,
          [username],
        );
        return rows[0] ?? null;
      });
    },

    async createSession({ userId, tokenHash, expiresAt }) {
      await withMysqlConnection(async (connection) => {
        await connection.execute(
          `INSERT INTO auth_session (user_id, token_hash, created_at, expires_at, last_used_at)
           VALUES (?, ?, NOW(), ?, NOW())`,
          [userId, tokenHash, expiresAt.replace('T', ' ').slice(0, 19)],
        );
      });
    },

    async getUserByToken(tokenHash) {
      return await withMysqlConnection(async (connection) => {
        const [rows] = await connection.execute(
          `SELECT u.id, u.username, u.role, u.is_active
           FROM auth_session s
           JOIN auth_user u ON u.id = s.user_id
           WHERE s.token_hash = ?
             AND s.expires_at > NOW()
             AND u.is_active = 1
           LIMIT 1`,
          [tokenHash],
        );
        return rows[0] ?? null;
      });
    },

    async touchSession(tokenHash, lastUsedAt) {
      await withMysqlConnection(async (connection) => {
        await connection.execute(
          'UPDATE auth_session SET last_used_at = ? WHERE token_hash = ?',
          [lastUsedAt.replace('T', ' ').slice(0, 19), tokenHash],
        );
      });
    },

    async deleteSession(tokenHash) {
      await withMysqlConnection(async (connection) => {
        await connection.execute('DELETE FROM auth_session WHERE token_hash = ?', [tokenHash]);
      });
    },
  };
}
