# `auth_user` 表设计说明

## 表作用

`auth_user` 是 Web 管理端的数据库用户表，负责保存可登录账号的基础信息。

它只保存“用户身份本身”，不保存登录态；登录态在 `auth_session` 中维护。

## 主键与关联关系

- 主键：`id`
- 被 `auth_session.user_id` 外键引用

## 字段说明

| 字段 | 类型 | 为空 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| `id` | `bigint` | 否 | `AUTO_INCREMENT` | 用户主键。 |
| `username` | `varchar(64)` | 否 | 无 | 登录用户名，必须唯一。 |
| `password_hash` | `varchar(255)` | 否 | 无 | 密码哈希值。数据库中不保存明文密码。 |
| `password_salt` | `varchar(255)` | 否 | 无 | 密码盐值，用于配合哈希校验。 |
| `role` | `varchar(32)` | 否 | `'user'` | 用户角色。默认是普通用户，当前本地示例使用 `admin`。 |
| `is_active` | `tinyint` | 否 | `1` | 账号是否启用。 |
| `created_at` | `datetime` | 否 | `CURRENT_TIMESTAMP` | 创建时间。 |
| `updated_at` | `datetime` | 否 | `CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | 更新时间。 |

## 索引与约束

- `PRIMARY KEY (id)`
- `UNIQUE KEY uk_auth_username (username)`

## 实际读写链路

### 写入来源

- `apps/web/scripts/seed-local-auth-users.mjs`：读取 `infra/mysql/local/auth_users.local.json`，在本机生成哈希和盐后写入 `auth_user`。
- `infra/mysql/local/seed_auth_users.local.sql.example`：本地手工 SQL 种子模板。

### 读取来源

- `apps/web/lib/server/authRepository.mjs` 的 `getUserByUsername()`：登录时按用户名读取用户。
- `apps/web/lib/server/authRepository.mjs` 的 `getUserByToken()`：通过 `auth_session` 关联回用户，并校验用户是否启用。

## 本地初始化约定

真实账号不放进 `infra/mysql/init/*.sql`，原因是这些 SQL 会被自动执行，不能带真实凭据。

当前推荐做法：

- 复制 `infra/mysql/local/auth_users.local.json.example`
- 在本机填写用户名、明文密码、角色
- 运行本地初始化脚本，由本地脚本生成哈希和盐后写库

当前示例角色是：

- `admin`

数据库层没有强制枚举，角色语义由应用层约定。

## 注意事项

- `password_hash` / `password_salt` 属于敏感字段，禁止提交到公共初始化脚本。
- `is_active = 0` 的用户即使存在有效会话，也应视为不可继续使用。
- 由于 `username` 唯一，修改用户名属于高风险操作，通常应谨慎执行。
