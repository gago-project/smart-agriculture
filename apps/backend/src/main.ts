import 'reflect-metadata';
import { config as loadDotenv } from 'dotenv';
import { join } from 'node:path';

// Load apps/backend/.env before anything reads process.env (mysql.mjs reads MYSQL_* lazily).
loadDotenv({ path: join(__dirname, '..', '.env') });

import { NestFactory } from '@nestjs/core';

import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  // No global prefix (Phase 0 contract). No CORS (web proxies this backend server-side).
  const port = Number(process.env.PORT ?? 18033);
  await app.listen(port, '0.0.0.0');
  // eslint-disable-next-line no-console
  console.log(`smart-agriculture-backend listening on :${port}`);
}

bootstrap();
