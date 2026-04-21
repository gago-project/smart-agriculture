# Local MySQL Seeds

这个目录只放**本地开发**需要的 MySQL 辅助文件。

## 为什么不把账号种子放进 `infra/mysql/init`

`infra/mysql/init/*.sql` 会被 Docker MySQL 自动执行，适合提交的是：

- 建库建表脚本
- 业务规则
- 预警模板
- 可公开的演示/样例业务数据

不适合提交的是：

- 真实登录账号
- `password_hash`
- `password_salt`
- 线上或个人环境的初始化凭据

## 本地账号怎么处理

如确实需要初始化本地账号，可以复制：

```bash
cp infra/mysql/local/auth_users.local.json.example infra/mysql/local/auth_users.local.json
```

然后在 JSON 中填写用户名、明文密码、角色。`db:init:local` 会在本机调用脚本生成
`password_hash` / `password_salt` 后再写入数据库。这个方式更适合日常开发，因为不需要
手工先算哈希。

如果你更希望手工控制 SQL，也可以复制：

```bash
cp infra/mysql/local/seed_auth_users.local.sql.example infra/mysql/local/seed_auth_users.local.sql
```

然后在 `.local.sql` 文件中填入你本机生成的哈希和盐。`.local.sql` 已被 `.gitignore`
忽略，不应提交到仓库。

## 本地土壤 Excel 怎么处理

如果需要把完整土壤墒情原始 Excel 导入本机 MySQL，可以：

1. 将文件放到 `infra/mysql/local/soil_data.local.xlsx`，或
2. 在执行 `db:init:local` 前设置 `SOIL_EXCEL_SOURCE=/your/path/to/file.xlsx`

脚本只会把文件名写入数据库，不会把你的本机绝对路径写进表里。
