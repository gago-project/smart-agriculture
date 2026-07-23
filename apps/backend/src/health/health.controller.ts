import { Controller, Get } from '@nestjs/common';

import { loadMysql } from '../data/bridge';

@Controller('health')
export class HealthController {
  // GET /health -> simple DB ping via the reused mysql.mjs connection helper.
  @Get()
  async health() {
    try {
      const mysql = await loadMysql();
      const value = await mysql.withMysqlConnection(async (connection: any) => {
        const [rows] = await connection.query('SELECT 1 AS ok');
        return rows?.[0]?.ok;
      });
      return {
        status: 'ok',
        service: 'smart-agriculture-backend',
        db: value === 1 ? 'up' : 'unknown',
      };
    } catch (error) {
      return {
        status: 'degraded',
        service: 'smart-agriculture-backend',
        db: 'down',
        error: error instanceof Error ? error.message : 'db ping failed',
      };
    }
  }
}
