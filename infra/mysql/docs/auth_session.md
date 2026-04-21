# `auth_session` 表设计说明

## 表作用

`auth_session` 用于保存登录会话，是当前 Web 鉴权链路的会话事实表。

它负责回答三个问题：

- 谁登录了；
- 登录态何时过期；
- 最近一次使用是什么时候。

## 主键与关联关系

- 主键：`id`
- 外键：`user_id -> auth_user.id`

## 字段说明

| 字段 | 类型 | 为空 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| `id` | `bigint` | 否 | `AUTO_INCREMENT` | 会话主键。 |
| `user_id` | `bigint` | 否 | 无 | 关联的登录用户 ID。 |
| `token_hash` | `varchar(255)` | 否 | 无 | 登录令牌的哈希值，不直接保存原始 token。 |
| `created_at` | `datetime` | 否 | 无 | 会话创建时间。 |
| `expires_at` | `datetime` | 否 | 无 | 会话过期时间。 |
| `last_used_at` | `datetime` | 否 | 无 | 最近一次使用时间，用于续期或审计。 |

## 索引与约束

- `PRIMARY KEY (id)`
- `UNIQUE KEY uk_auth_token_hash (token_hash)`
- `KEY idx_auth_session_user (user_id)`
- `KEY idx_auth_session_expires_at (expires_at)`
- `FOREIGN KEY fk_auth_session_user (user_id) REFERENCES auth_user(id)`

## 实际读写链路

### 写入来源

- `apps/web/lib/server/authRepository.mjs`：
  - `createSession()`：登录成功后创建会话；
  - `touchSession()`：请求使用时刷新最近访问时间；
  - `deleteSession()`：退出登录时删除会话。

### 读取来源

- `apps/web/lib/server/authRepository.mjs` 的 `getUserByToken()`：
  - 按 `token_hash` 查会话；
  - 要求 `expires_at > NOW()`；
  - 再关联 `auth_user` 且要求 `is_active = 1`。

## 当前会话约束

- 会话唯一性依赖 `token_hash`。
- 数据库层不自动清理过期会话；当前主要靠查询时过滤 `expires_at`。
- `last_used_at` 用于记录活跃度，但当前仓库中未见复杂的滑动续期策略。

## 注意事项

- 表中保存的是 `token_hash`，不是原始 token，本质上是降低泄漏风险。
- 由于没有 `ON DELETE CASCADE`，若手工删除 `auth_user`，需要同步处理其会话数据。
- 如果未来需要设备维度、IP、UA 等登录审计信息，需要额外加字段或另建审计表。
