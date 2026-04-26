---
name: db-sync
description: >
  Use when the Docker MySQL or Redis state is out of sync with local development —
  e.g. after adding columns/tables in 001_init_tables.sql, updating seed data in
  002_insert_data.sql, adding auth users, switching modes, or wanting to save/restore
  key table row data (fact_soil_moisture, auth_user, region_alias).
---

# Smart Agriculture — Docker 数据库同步 Skill

## 架构背景（必读）

**MySQL 和 Redis 始终运行在 Docker 容器中**，两种部署模式共用同一组容器：

```
MySQL  → smart-agriculture-mysql  → 127.0.0.1:3306  (volume: mysql-data/)
Redis  → smart-agriculture-redis  → 127.0.0.1:6379  (volume: redis-data/)
agent  → 进程模式(18010) 或 Docker(8000)
web    → 进程模式(3000)  或 Docker(3000)
```

**核心陷阱：** Docker MySQL 卷中已有数据时，容器重启**不会**重新执行 `docker-entrypoint-initdb.d/` 下的初始化脚本，开发中对 SQL 文件的修改不会自动生效。

---

## 前置：读取连接信息

所有场景开始前先执行一次，建立连接变量：

```bash
cd /Users/mac/Desktop/gago-cloud/code/smart-agriculture
source scripts/dev/load-root-env.sh

MYSQL_HOST_SYNC=127.0.0.1
MYSQL_PORT_SYNC=${MYSQL_PORT:-3306}
MYSQL_DB=${MYSQL_DATABASE:-smart_agriculture}
MYSQL_USER_SYNC=${MYSQL_APPLY_USER:-${MYSQL_USER:-root}}
MYSQL_PWD_SYNC=${MYSQL_APPLY_PASSWORD:-${MYSQL_PASSWORD:-${MYSQL_ROOT_PASSWORD:-}}}
REDIS_HOST=127.0.0.1
REDIS_PORT=6379

# 连通性检查
MYSQL_PWD="$MYSQL_PWD_SYNC" mysql --protocol=TCP \
  -h $MYSQL_HOST_SYNC -P $MYSQL_PORT_SYNC -u $MYSQL_USER_SYNC \
  -e "SELECT 1" 2>/dev/null \
  && echo "MySQL ✓" \
  || echo "MySQL ✗ — 请先启动: docker compose --env-file .env -f infra/docker/docker-compose.yml up -d mysql"
```

---

## 辅助函数：行数快照

每个场景用这个函数在操作前后各抓一次行数，最后打印 summary：

```bash
snapshot_counts() {
  MYSQL_PWD="$MYSQL_PWD_SYNC" mysql --protocol=TCP \
    -h $MYSQL_HOST_SYNC -P $MYSQL_PORT_SYNC -u $MYSQL_USER_SYNC \
    --skip-column-names -s 2>/dev/null \
    -e "USE \`$MYSQL_DB\`;
        SELECT
          COALESCE((SELECT COUNT(*) FROM fact_soil_moisture),0),
          COALESCE((SELECT COUNT(*) FROM auth_user),0),
          COALESCE((SELECT COUNT(*) FROM region_alias),0),
          COALESCE((SELECT COUNT(*) FROM metric_rule),0),
          COALESCE((SELECT COUNT(*) FROM warning_template),0),
          COALESCE((SELECT COUNT(*) FROM auth_session),0);"
}

print_summary() {
  local label="$1"
  local before="$2"   # tab-separated values from snapshot_counts
  local after="$3"

  IFS=$'\t' read -r b_soil b_user b_alias b_rule b_tmpl b_sess <<< "$before"
  IFS=$'\t' read -r a_soil a_user a_alias a_rule a_tmpl a_sess <<< "$after"

  # Format: "1234 → 1236  (+2 行)" or "1234" if no change
  row() {
    local b=$1 a=$2
    local d=$((a - b))
    if   [ $d -gt 0 ]; then printf "%s → %s  (+%s 行)" "$b" "$a" "$d"
    elif [ $d -lt 0 ]; then printf "%s → %s  (%s 行)"  "$b" "$a" "$d"
    else                    printf "%s"                  "$a"
    fi
  }

  echo ""
  echo "════════════════════════════════════════"
  echo "  同步 Summary — ${label}"
  echo "────────────────────────────────────────"
  printf "  %-22s %s\n" "fact_soil_moisture"  "$(row $b_soil  $a_soil)"
  printf "  %-22s %s\n" "auth_user"           "$(row $b_user  $a_user)"
  printf "  %-22s %s\n" "region_alias"        "$(row $b_alias $a_alias)"
  printf "  %-22s %s\n" "metric_rule"         "$(row $b_rule  $a_rule)"
  printf "  %-22s %s\n" "warning_template"    "$(row $b_tmpl  $a_tmpl)"
  printf "  %-22s %s\n" "auth_session"        "$(row $b_sess  $a_sess)"
  echo "════════════════════════════════════════"
}
```

---

## 场景一：Schema 同步（修改了 001_init_tables.sql 后）

```bash
BEFORE=$(snapshot_counts)
MYSQL_PWD="$MYSQL_PWD_SYNC" mysql --protocol=TCP \
  -h $MYSQL_HOST_SYNC -P $MYSQL_PORT_SYNC -u $MYSQL_USER_SYNC \
  --default-character-set=utf8mb4 \
  < infra/mysql/init/001_init_tables.sql
AFTER=$(snapshot_counts)
print_summary "Schema 同步 (001_init_tables.sql)" "$BEFORE" "$AFTER"
```

> 001 完全幂等：`CREATE TABLE IF NOT EXISTS` + `ensure_column` + `ensure_index`。  
> 只补缺失结构，不影响现有数据行，行数通常无变化。

---

## 场景二：种子数据同步（修改了 002_insert_data.sql 后）

```bash
BEFORE=$(snapshot_counts)
MYSQL_PWD="$MYSQL_PWD_SYNC" mysql --protocol=TCP \
  -h $MYSQL_HOST_SYNC -P $MYSQL_PORT_SYNC -u $MYSQL_USER_SYNC \
  --default-character-set=utf8mb4 \
  < infra/mysql/init/002_insert_data.sql
AFTER=$(snapshot_counts)
print_summary "种子数据同步 (002_insert_data.sql)" "$BEFORE" "$AFTER"
```

> 002 完全幂等：`INSERT ... ON DUPLICATE KEY UPDATE`。  
> 若规则/模板有更新，metric_rule / warning_template 行数可能变化。

---

## 场景三：Auth 用户同步

```bash
LOCAL_AUTH_JSON="${LOCAL_AUTH_USERS_JSON:-infra/mysql/local/auth_users.local.json}"
BEFORE=$(snapshot_counts)

if [ -f "$LOCAL_AUTH_JSON" ]; then
  MYSQL_HOST=$MYSQL_HOST_SYNC \
  MYSQL_PORT=$MYSQL_PORT_SYNC \
  MYSQL_DATABASE=$MYSQL_DB \
  MYSQL_USER=$MYSQL_USER_SYNC \
  MYSQL_PASSWORD=$MYSQL_PWD_SYNC \
  LOCAL_AUTH_USERS_JSON="$LOCAL_AUTH_JSON" \
  node apps/web/scripts/seed-local-auth-users.mjs
elif [ -f "infra/mysql/local/seed_auth_users.local.sql" ]; then
  MYSQL_PWD="$MYSQL_PWD_SYNC" mysql --protocol=TCP \
    -h $MYSQL_HOST_SYNC -P $MYSQL_PORT_SYNC -u $MYSQL_USER_SYNC \
    --default-character-set=utf8mb4 \
    < infra/mysql/local/seed_auth_users.local.sql
else
  echo "⚠️  未找到 auth users 文件，跳过"
fi

AFTER=$(snapshot_counts)
print_summary "Auth 用户同步" "$BEFORE" "$AFTER"
```

---

## 场景四：导出行数据快照（保存当前墒情/用户数据）

导出表：`fact_soil_moisture`、`auth_user`、`region_alias`。  
不导出：`agent_query_log`、`auth_session`、`soil_import_job`。  
快照文件：`infra/mysql/local/data-snapshot.local.sql`（`*.local.sql` 已在 `.gitignore`）。

```bash
SNAPSHOT_FILE="infra/mysql/local/data-snapshot.local.sql"
BEFORE=$(snapshot_counts)

cat > "$SNAPSHOT_FILE" <<SQL
-- Smart Agriculture data snapshot
-- Exported: $(date '+%Y-%m-%d %H:%M:%S')
-- Source:   $MYSQL_HOST_SYNC:$MYSQL_PORT_SYNC / $MYSQL_DB
-- Tables:   fact_soil_moisture  auth_user  region_alias

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;
USE \`${MYSQL_DB}\`;

SQL

for TABLE in fact_soil_moisture auth_user region_alias; do
  MYSQL_PWD="$MYSQL_PWD_SYNC" mysqldump \
    --protocol=TCP \
    -h $MYSQL_HOST_SYNC -P $MYSQL_PORT_SYNC -u $MYSQL_USER_SYNC \
    --no-tablespaces --single-transaction --quick \
    --replace --skip-add-drop-table --no-create-info --compact \
    "$MYSQL_DB" "$TABLE" >> "$SNAPSHOT_FILE"
  echo "" >> "$SNAPSHOT_FILE"
done

echo "SET FOREIGN_KEY_CHECKS = 1;" >> "$SNAPSHOT_FILE"

AFTER=$(snapshot_counts)
print_summary "导出数据快照" "$BEFORE" "$AFTER"

FILE_SIZE=$(du -sh "$SNAPSHOT_FILE" | cut -f1)
echo "  快照文件: $SNAPSHOT_FILE ($FILE_SIZE)"
```

---

## 场景五：导入行数据快照（Docker 重建后恢复数据）

```bash
SNAPSHOT_FILE="infra/mysql/local/data-snapshot.local.sql"

if [ ! -f "$SNAPSHOT_FILE" ]; then
  echo "❌ 快照文件不存在: $SNAPSHOT_FILE"
  echo "   请先执行场景四导出快照"
  exit 1
fi

FILE_SIZE=$(du -sh "$SNAPSHOT_FILE" | cut -f1)
echo "导入快照: $SNAPSHOT_FILE ($FILE_SIZE)"

BEFORE=$(snapshot_counts)

MYSQL_PWD="$MYSQL_PWD_SYNC" mysql --protocol=TCP \
  -h $MYSQL_HOST_SYNC -P $MYSQL_PORT_SYNC -u $MYSQL_USER_SYNC \
  --default-character-set=utf8mb4 \
  < "$SNAPSHOT_FILE"

AFTER=$(snapshot_counts)
print_summary "导入数据快照" "$BEFORE" "$AFTER"
```

---

## 场景六：土壤数据基线同步（003，较慢）

```bash
BEFORE=$(snapshot_counts)
echo "⚠️  003_insert_soil_data.sql 约 42MB，请耐心等待..."
MYSQL_PWD="$MYSQL_PWD_SYNC" mysql --protocol=TCP \
  -h $MYSQL_HOST_SYNC -P $MYSQL_PORT_SYNC -u $MYSQL_USER_SYNC \
  --default-character-set=utf8mb4 \
  < infra/mysql/init/003_insert_soil_data.sql
AFTER=$(snapshot_counts)
print_summary "土壤数据基线 (003_insert_soil_data.sql)" "$BEFORE" "$AFTER"
```

---

## 场景七：清除 Redis 对话缓存

Redis 只存 `session_ctx:{session_id}`（对话上下文，TTL 1h）：

```bash
KEY_COUNT=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT \
  --scan --pattern "session_ctx:*" 2>/dev/null | wc -l | tr -d ' ')

if [ "$KEY_COUNT" -gt 0 ]; then
  redis-cli -h $REDIS_HOST -p $REDIS_PORT \
    --scan --pattern "session_ctx:*" \
    | xargs -r redis-cli -h $REDIS_HOST -p $REDIS_PORT DEL
  echo ""
  echo "════════════════════════════════════════"
  echo "  同步 Summary — 清除 Redis 对话缓存"
  echo "────────────────────────────────────────"
  echo "  session_ctx:* 键删除数: $KEY_COUNT"
  echo "════════════════════════════════════════"
else
  echo "Redis 中无 session_ctx:* 键，无需清除"
fi
```

---

## 场景八：清除登录会话（强制重新登录）

```bash
BEFORE=$(snapshot_counts)
MYSQL_PWD="$MYSQL_PWD_SYNC" mysql --protocol=TCP \
  -h $MYSQL_HOST_SYNC -P $MYSQL_PORT_SYNC -u $MYSQL_USER_SYNC \
  -e "USE \`$MYSQL_DB\`; DELETE FROM auth_session;"
AFTER=$(snapshot_counts)
print_summary "清除登录会话" "$BEFORE" "$AFTER"
```

---

## 常用组合

| 场景 | 执行 |
|------|------|
| 改了 `001` 或 `002` | 场景一 + 场景二 |
| 新增了数据，想备份 | 场景四 |
| Docker 重建后恢复 | 场景一 + 二 + 三 + 五 |
| 切换部署模式后对话上下文混乱 | 场景七 |
| 完整重置（不含土壤基线） | 场景一~三 + 七 + 八 |
