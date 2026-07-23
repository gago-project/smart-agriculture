import {
  CanActivate,
  ExecutionContext,
  ForbiddenException,
  Injectable,
  UnauthorizedException,
  mixin,
  Type,
} from '@nestjs/common';
import { Request } from 'express';

import { AuthService, PublicUser } from './auth.service';
import { extractToken } from './token';

export interface AuthedRequest extends Request {
  authToken?: string;
  authUser?: PublicUser;
}

/**
 * Base authentication: token (Bearer header or body.token) -> auth_session -> user.
 * Mirrors web requireRequestUser: no session -> 401.
 */
@Injectable()
export class AuthGuard implements CanActivate {
  constructor(protected readonly authService: AuthService) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const req = context.switchToHttp().getRequest<AuthedRequest>();
    const token = extractToken(req);
    if (!token) {
      throw new UnauthorizedException('authentication required');
    }
    const user = await this.authService.authenticate(token);
    if (!user) {
      throw new UnauthorizedException('authentication required');
    }
    req.authToken = token;
    req.authUser = user;
    return true;
  }
}

/**
 * Admin gate. Mirrors web requireAdminRequestUser: no session -> 401, non-admin -> 403.
 */
@Injectable()
export class AdminGuard extends AuthGuard {
  async canActivate(context: ExecutionContext): Promise<boolean> {
    await super.canActivate(context);
    const req = context.switchToHttp().getRequest<AuthedRequest>();
    if (req.authUser?.role !== 'admin') {
      throw new ForbiddenException('admin required');
    }
    return true;
  }
}

/**
 * Role gate factory. Mirrors web requireRoleRequestUser:
 * no session -> 401, role not in allowed set -> 403 (permission denied).
 */
export function RoleGuard(allowedRoles: string[]): Type<CanActivate> {
  @Injectable()
  class RoleGuardMixin extends AuthGuard {
    async canActivate(context: ExecutionContext): Promise<boolean> {
      await super.canActivate(context);
      const req = context.switchToHttp().getRequest<AuthedRequest>();
      if (!allowedRoles.includes(req.authUser?.role || '')) {
        throw new ForbiddenException('permission denied');
      }
      return true;
    }
  }
  return mixin(RoleGuardMixin);
}
