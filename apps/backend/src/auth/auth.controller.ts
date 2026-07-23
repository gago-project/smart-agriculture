import {
  Body,
  Controller,
  Headers,
  HttpCode,
  Post,
  UnauthorizedException,
} from '@nestjs/common';

import { AuthService } from '../common/auth.service';

function tokenFrom(authHeader: string | undefined, bodyToken: unknown): string {
  const header = String(authHeader || '');
  if (header.startsWith('Bearer ')) {
    const t = header.slice('Bearer '.length).trim();
    if (t) return t;
  }
  return typeof bodyToken === 'string' ? bodyToken.trim() : '';
}

@Controller('auth')
export class AuthController {
  constructor(private readonly authService: AuthService) {}

  // POST /auth/login {username,password} -> { token, expiresAt, user } | 401
  @Post('login')
  @HttpCode(200)
  async login(@Body() body: { username?: string; password?: string }) {
    try {
      return await this.authService.login(
        String(body?.username || ''),
        String(body?.password || ''),
      );
    } catch (error) {
      throw new UnauthorizedException(
        error instanceof Error ? error.message : '登录失败',
      );
    }
  }

  // POST /auth/validate {token} | Authorization: Bearer <token> -> { user } | 401
  @Post('validate')
  @HttpCode(200)
  async validate(
    @Headers('authorization') authHeader: string | undefined,
    @Body() body: { token?: string },
  ) {
    const token = tokenFrom(authHeader, body?.token);
    if (!token) {
      throw new UnauthorizedException('authentication required');
    }
    const user = await this.authService.authenticate(token);
    if (!user) {
      throw new UnauthorizedException('authentication required');
    }
    return { user };
  }

  // POST /auth/logout {token} | Authorization: Bearer <token> -> { ok: true } | 401
  @Post('logout')
  @HttpCode(200)
  async logout(
    @Headers('authorization') authHeader: string | undefined,
    @Body() body: { token?: string },
  ) {
    const token = tokenFrom(authHeader, body?.token);
    if (!token) {
      throw new UnauthorizedException('authentication required');
    }
    const user = await this.authService.authenticate(token);
    if (!user) {
      throw new UnauthorizedException('authentication required');
    }
    await this.authService.logout(token);
    return { ok: true };
  }
}
