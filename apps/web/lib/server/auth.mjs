import { createAuthService } from './authCore.mjs';
import { createMysqlAuthRepository } from './authRepository.mjs';

const auth = createAuthService({
  repository: createMysqlAuthRepository(),
  sessionTtlDays: 7,
});

export class AuthRequestError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'AuthRequestError';
    this.status = status;
  }
}

export async function loginWithPassword(username, password) {
  return await auth.login(username, password);
}

export async function logoutWithToken(token) {
  await auth.logout(token);
}

export async function getUserFromToken(token) {
  return await auth.authenticate(token);
}

export async function requireRequestUser(request) {
  const authHeader = request.headers.get('authorization') || '';
  if (!authHeader.startsWith('Bearer ')) {
    return null;
  }
  const token = authHeader.slice('Bearer '.length).trim();
  if (!token) return null;
  const user = await getUserFromToken(token);
  if (!user) return null;
  return { token, user };
}

export async function requireAdminRequestUser(request) {
  const session = await requireRequestUser(request);
  if (!session) {
    throw new AuthRequestError('authentication required', 401);
  }
  if (session.user.role !== 'admin') {
    throw new AuthRequestError('admin required', 403);
  }
  return session;
}

export async function requireRoleRequestUser(request, allowedRoles) {
  const session = await requireRequestUser(request);
  if (!session) {
    throw new AuthRequestError('authentication required', 401);
  }
  const roles = new Set(allowedRoles);
  if (!roles.has(session.user.role)) {
    throw new AuthRequestError('permission denied', 403);
  }
  return session;
}
