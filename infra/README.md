# PostgreSQL 与定期备份

在项目根目录运行以下命令，需要 Docker Desktop（Linux containers）和 Docker Compose v2。
当前 Compose 默认启动一个 PostgreSQL 17 实例和一个执行备份的辅助容器。
竞品采集通过 `competitors` 任务容器按需执行；FastAPI 仍在本机运行。

## 启动

```powershell
Copy-Item .env.example .env
# 编辑根目录 .env，填写 POSTGRES_PASSWORD（必填）
docker compose up -d
docker compose ps
docker compose logs --tail=50 postgres-backup
```

如果当前 Windows 环境提示 `docker compose` 不存在，可将文中 `docker compose`
替换为 `docker-compose`（本机 Docker Desktop 已提供该独立命令）。

密码含 `$`、`#` 等字符时，在 `.env` 中使用单引号包裹值。
默认用户和数据库均为 `postgres`，端口 `5432`，仅监听本机 `127.0.0.1`。
端口被占用时修改 `.env` 的 `POSTGRES_PORT`，例如 `5433`。

项目根目录会自动生成以下目录，均已加入 `.gitignore`：

| 目录 | 内容 |
| --- | --- |
| `data/postgres/` | PostgreSQL 持久化数据 |
| `backups/postgres/` | 带 UTC 时间戳的压缩 `.dump` 备份 |

首次启动空数据目录时自动执行 `backend/sql/002_create_tables.sql` 和 `003_daily_prices.sql`。
已有数据目录不会重新初始化；修改 `.env` 中的用户、密码或库名也不会修改已有数据库。
`docker compose down` 停止服务后仍保留这些目录；不要手工删除数据目录。

## 容器内运行 competitors.py

在根目录 `.env` 配置 `POSTGRES_PASSWORD` 和 `APIFY_TOKEN`。
例如要使用密码 `123456`，设置 `POSTGRES_PASSWORD=123456`，任务容器会自动使用同一密码；
已有数据库的密码不会因为修改 `.env` 而改变，需填写该数据库的实际密码。
无需再在宿主机安装 Python 依赖或设置 `PGPASSWORD`。

在项目根目录执行（当前 Windows 也可使用 `docker-compose`）：

```powershell
# 构建镜像，自动执行 python -m pip install -r requirements.txt
docker compose build competitors
docker compose up -d

# 预览一个采集组合，不调用 Apify
docker compose run --rm competitors --limit-runs 1

# 可选：仅初始化数据库；正式执行也会自动初始化
docker compose run --rm competitors --init-db

# 实际执行一个组合，使用 .env 中的 APIFY_TOKEN
docker compose run --rm competitors --execute --limit-runs 1
```

`docker compose run --rm competitors` 默认等价于最后一条执行命令。
容器等待 PostgreSQL 健康后运行，完成后退出，不自动重复采集。
该服务属于 `collection` profile，普通 `docker compose up -d` 不会触发采集；
也可用 `docker compose --profile collection up -d --build` 启动包含一次采集的整套服务。
真实执行会调用 Apify 并可能产生费用，token 只通过运行环境传入，不写入镜像。

采集配置直接挂载 `backend/competitors.example.json`，修改配置无需重建镜像。
原始 JSON 输出映射到 `backend/competitor_output/`，结构化结果写入 PostgreSQL，随数据库定期备份。
修改 Python 代码或依赖后重新执行 `docker compose build competitors`。

## backend 本机连接

在启动采集程序的 PowerShell 中设置（值与根目录 `.env` 保持一致）：

```powershell
$env:PGHOST = '127.0.0.1'
$env:PGPORT = '5432'
$env:PGUSER = 'postgres'
$env:PGPASSWORD = '<与 POSTGRES_PASSWORD 一致>'
$env:PGDATABASE = 'postgres'
```

Compose 的 `.env` 不会自动导出到本机 Python 进程。
FastAPI 配置另外读取 `DATABASE_URL`，需在启动 API 的环境中设置为：
`postgresql+psycopg://postgres:<URL编码后的密码>@127.0.0.1:5432/postgres`。
如果修改了用户、端口或库名，同步修改连接地址。API 运行命令见根目录 README。

## 备份策略

数据库健康后立即备份一次，每次成功后等待 `BACKUP_INTERVAL_SECONDS` 秒再执行（默认 86400，即 24 小时）。
备份失败会输出错误、保留已有备份，并在 60 秒后重试。
仅在新备份成功后删除超过 `BACKUP_RETENTION_DAYS` 天的归档（默认 7 天）。
备份先写以 `.postgres-` 开头的隐藏临时文件，检查归档目录可读后原子重命名为 `.dump`，避免误用未完成的备份。
修改备份参数后运行 `docker compose up -d` 应用配置。
服务或 Docker 停止期间不会执行备份，重启后立即补做一次。

手动备份（失败时返回非零退出码）：

```powershell
docker compose run --rm postgres-backup once
```

备份覆盖 `POSTGRES_DB` 指定库的结构和数据，不包含其他数据库及集群角色。
采用 PostgreSQL 官方的 [pg_dump custom 格式](https://www.postgresql.org/docs/17/app-pgdump.html)，
可使用 [pg_restore](https://www.postgresql.org/docs/17/app-pgrestore.html) 恢复。
本地备份与数据位于同一台机器；需要抵御磁盘损坏时，将备份目录另行同步到异地存储。

## 恢复验证

建议先恢复到新库验证，不覆盖当前业务库。将下面文件名替换为 `backups/postgres/` 下实际的 `.dump` 文件名：

```powershell
# 创建空库；下列命令中的 PGUSER 由容器环境读取
docker compose run --rm --entrypoint createdb postgres-backup --maintenance-db=postgres hotel_restore
docker compose run --rm --entrypoint pg_restore postgres-backup --exit-on-error --no-owner --no-acl --dbname=hotel_restore /backups/postgres-20261018T000000Z-XXXXXX.dump
docker compose run --rm --entrypoint psql postgres-backup --dbname=hotel_restore --command='SELECT count(*) FROM public.collection_batches;'
```

恢复成功后可将 backend 的 `PGDATABASE` / `DATABASE_URL` 指向 `hotel_restore`。
`--no-owner --no-acl` 将恢复对象归属当前用户，不恢复原有授权；如有自定义角色和权限，需单独管理。
