import { Request } from 'express';

/**
 * Extract the raw session token from a request. Mirrors web's requireRequestUser,
 * which reads `Authorization: Bearer <token>`, and additionally accepts `{ token }`
 * in the JSON body (login/validate/logout are documented to take a body token).
 */
export function extractToken(req: Request): string {
  const authHeader = String(req.headers['authorization'] || '');
  if (authHeader.startsWith('Bearer ')) {
    const headerToken = authHeader.slice('Bearer '.length).trim();
    if (headerToken) return headerToken;
  }
  const body = (req.body || {}) as Record<string, unknown>;
  const bodyToken = typeof body.token === 'string' ? body.token.trim() : '';
  return bodyToken;
}
