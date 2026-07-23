import { Injectable } from '@nestjs/common';

import { loadAuth } from '../data/bridge';

export interface PublicUser {
  id: number;
  username: string;
  role: string;
}

export interface SessionResult {
  token: string;
  expiresAt: string;
  user: PublicUser;
}

/**
 * Thin wrapper around the reused auth.mjs (createAuthService / scrypt / auth_session).
 * Logic is untouched; this only adapts naming to the Phase 0 contract
 * ({ token, expiresAt, user }) and provides authenticate/logout used by guards.
 */
@Injectable()
export class AuthService {
  async login(username: string, password: string): Promise<SessionResult> {
    const auth = await loadAuth();
    // auth.mjs returns { token, expires_at, user }
    const session = await auth.loginWithPassword(
      String(username || '').trim(),
      String(password || '').trim(),
    );
    return {
      token: session.token,
      expiresAt: session.expires_at,
      user: session.user,
    };
  }

  async authenticate(token: string): Promise<PublicUser | null> {
    const auth = await loadAuth();
    return auth.getUserFromToken(String(token || '').trim());
  }

  async logout(token: string): Promise<void> {
    const auth = await loadAuth();
    await auth.logoutWithToken(String(token || '').trim());
  }
}
