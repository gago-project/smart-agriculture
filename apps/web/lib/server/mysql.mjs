async function loadMysql() {
  try {
    return await import('mysql2/promise');
  } catch (error) {
    throw new Error(`mysql2/promise unavailable: ${error instanceof Error ? error.message : 'unknown error'}`);
  }
}

export function mysqlConfig() {
  return {
    host: process.env.MYSQL_HOST,
    port: Number(process.env.MYSQL_PORT || '3306'),
    user: process.env.MYSQL_USER,
    password: process.env.MYSQL_PASSWORD,
    database: process.env.MYSQL_DATABASE,
  };
}

export function assertMysqlConfig() {
  const config = mysqlConfig();
  if (!config.host || !config.user || !config.password || !config.database) {
    throw new Error('MySQL configuration is incomplete');
  }
  return config;
}

export async function withMysqlConnection(task, options = {}) {
  const mysql = await loadMysql();
  const config = assertMysqlConfig();
  const connection = await mysql.createConnection({
    ...config,
    connectTimeout: options.connectTimeout ?? 2000,
  });

  try {
    return await task(connection);
  } finally {
    await connection.end();
  }
}
