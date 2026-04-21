#!/usr/bin/env bash
set -euo pipefail

# Apply the committed MySQL initialization scripts to a local MySQL instance.
#
# The script reads `.env` through the shared loader, but every value can be
# overridden by the shell environment.  Passwords are passed through MYSQL_PWD
# for the child `mysql` process and are never echoed.

ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT_DIR"

source "${ROOT_DIR}/scripts/dev/load-root-env.sh"

MYSQL_HOST_FOR_LOCAL=${LOCAL_MYSQL_HOST:-${MYSQL_HOST:-127.0.0.1}}
if [ "$MYSQL_HOST_FOR_LOCAL" = "mysql" ]; then
  MYSQL_HOST_FOR_LOCAL="127.0.0.1"
fi

MYSQL_PORT_FOR_LOCAL=${LOCAL_MYSQL_PORT:-${MYSQL_PORT:-3306}}
MYSQL_DATABASE_FOR_LOCAL=${MYSQL_DATABASE:-smart_agriculture}
MYSQL_USER_FOR_LOCAL=${MYSQL_APPLY_USER:-${MYSQL_USER:-${MYSQL_ROOT_USER:-root}}}
MYSQL_PASSWORD_FOR_LOCAL=${MYSQL_APPLY_PASSWORD:-${MYSQL_PASSWORD:-${MYSQL_ROOT_PASSWORD:-}}}

if [ -z "$MYSQL_USER_FOR_LOCAL" ]; then
  echo "缺少 MYSQL_APPLY_USER 或可用的 root 用户配置，无法初始化本地 MySQL。"
  exit 1
fi

if [ -z "$MYSQL_PASSWORD_FOR_LOCAL" ]; then
  echo "缺少 MYSQL_APPLY_PASSWORD、MYSQL_ROOT_PASSWORD 或 MYSQL_PASSWORD，无法初始化本地 MySQL。"
  exit 1
fi

MYSQL_ARGS=(
  --protocol=TCP
  -h "$MYSQL_HOST_FOR_LOCAL"
  -P "$MYSQL_PORT_FOR_LOCAL"
  -u "$MYSQL_USER_FOR_LOCAL"
  --default-character-set=utf8mb4
)

run_sql() {
  local sql_file=$1
  echo "执行 ${sql_file}"
  MYSQL_PWD="$MYSQL_PASSWORD_FOR_LOCAL" mysql "${MYSQL_ARGS[@]}" < "$sql_file"
}

run_node_local() {
  MYSQL_HOST="$MYSQL_HOST_FOR_LOCAL" \
  MYSQL_PORT="$MYSQL_PORT_FOR_LOCAL" \
  MYSQL_DATABASE="$MYSQL_DATABASE_FOR_LOCAL" \
  MYSQL_USER="$MYSQL_USER_FOR_LOCAL" \
  MYSQL_PASSWORD="$MYSQL_PASSWORD_FOR_LOCAL" \
  node "$@"
}

echo "初始化本地 MySQL：host=${MYSQL_HOST_FOR_LOCAL} port=${MYSQL_PORT_FOR_LOCAL} database=${MYSQL_DATABASE_FOR_LOCAL} user=${MYSQL_USER_FOR_LOCAL}"
run_sql "infra/mysql/init/001_init_tables.sql"
run_sql "infra/mysql/init/002_insert_data.sql"
run_sql "infra/mysql/init/003_insert_soil_data.sql"

LOCAL_AUTH_USERS_JSON_PATH=${LOCAL_AUTH_USERS_JSON:-infra/mysql/local/auth_users.local.json}
if [ -n "${LOCAL_AUTH_USERS_JSON:-}" ] || [ -f "$LOCAL_AUTH_USERS_JSON_PATH" ]; then
  echo "检测到本地账号 JSON，执行 apps/web/scripts/seed-local-auth-users.mjs"
  LOCAL_AUTH_USERS_JSON="$LOCAL_AUTH_USERS_JSON_PATH" run_node_local "apps/web/scripts/seed-local-auth-users.mjs"
elif [ -f "infra/mysql/local/seed_auth_users.local.sql" ]; then
  echo "检测到本地账号种子，执行 infra/mysql/local/seed_auth_users.local.sql"
  run_sql "infra/mysql/local/seed_auth_users.local.sql"
fi

LOCAL_SOIL_EXCEL_PATH=${SOIL_EXCEL_SOURCE:-infra/mysql/local/soil_data.local.xlsx}
if [ -n "${SOIL_EXCEL_SOURCE:-}" ] || [ -f "$LOCAL_SOIL_EXCEL_PATH" ]; then
  echo "检测到本地土壤 Excel，执行 apps/web/scripts/import-local-soil-excel.mjs"
  SOIL_EXCEL_SOURCE="$LOCAL_SOIL_EXCEL_PATH" run_node_local "apps/web/scripts/import-local-soil-excel.mjs"
else
  echo "未检测到本地土壤 Excel，保留 003_insert_soil_data.sql 的全量初始化数据。"
fi

MYSQL_PWD="$MYSQL_PASSWORD_FOR_LOCAL" mysql "${MYSQL_ARGS[@]}" -e "USE \`${MYSQL_DATABASE_FOR_LOCAL}\`; SELECT COUNT(*) AS fact_soil_moisture_count FROM fact_soil_moisture;"
