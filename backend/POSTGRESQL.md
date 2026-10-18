# PostgreSQL 数据库与字段说明

核心采集已改为按天查询：配置 `calendar_days=30`、`nights=[1]`，默认覆盖2026-11-11至2026-12-10的入住日，退房日为次日。每个日期有8个人数组合，共240个Actor运行，默认费用上限合计120美元；先用 `--limit-runs 1` 验证。可缩短天数或限定一个人数组合降低费用。3–5晚套餐仍可通过 `nights=[3,4,5]` 查询，但不进入单晚视图。

已有数据库执行 `sql/003_daily_prices.sql` 升级，或者重新运行 `competitors.py --init-db`（会执行002及003）。新库按001、002、003顺序执行。

新增视图：`daily_hotel_prices` 保留每天报价的所有采集历史；`latest_daily_hotel_prices` 为每个酒店、入住日、成人数、儿童年龄、房间数组合选取最近报价。`stay_date`是入住日；`observation_date_jst`是采集日。两者不能混用。

```sql
-- 比较相同人数条件下，每家酒店各入住日最新价格
SELECT stay_date, name, nightly_jpy, in_target_price_band,
       collected_at AT TIME ZONE 'Asia/Tokyo' AS observed_at_jst
FROM latest_daily_hotel_prices
WHERE adults=2 AND children_ages=ARRAY[5,8]::smallint[]
ORDER BY stay_date, nightly_jpy;

-- 固定酒店在同一入住日的价格变动
SELECT name, stay_date, nightly_jpy, collected_at
FROM daily_hotel_prices
WHERE stay_date=DATE '2026-11-11' AND adults=2
  AND children_ages=ARRAY[5,8]::smallint[]
ORDER BY hotel_key, collected_at;
```

配置 `hotel_urls` 为确定的Booking酒店链接数组，可固定竞品名单；为空时按目的地发现候选，每次最多max_results条，不保证所有酒店或每个日期均有记录。固定链接应去掉日期查询参数。默认 `filter_search_price=false` 不在上游过滤价格，超出价带仍保存并进入每日视图，`in_target_price_band=false`。单晚价格可能不同于3–5晚入住的每晚平均价；最短入住限制也可能让单晚没有报价。空白不能解释为售罄。本程序不会把套餐总价均分后冒充各天价格，也不自动定时执行；每次执行保存新的采集批次。

默认 host=localhost、port=5432、user=postgres、database=postgres，连接固定使用 public schema。密码不写入程序。旧 hotel_competitors 库的数据不会自动迁移。

## 初始化

在 backend 目录运行 PowerShell：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PGHOST = 'localhost'
$env:PGPORT = '5432'
$env:PGUSER = 'postgres'
$env:PGPASSWORD = '123456'
$env:PGDATABASE = 'postgres'
```

程序会连接维护库 `postgres`（可通过 `PGMAINTENANCE_DB` 修改），检查 `PGDATABASE` 指定的数据库。不存在时通过 `sql/001_create_database.sql` 创建，随后连接目标库执行002、003初始化表和视图。数据库归当前 `PGUSER` 所有；首次建库需要该用户具有 `CREATEDB` 权限。运行：

```powershell
.\.venv\Scripts\python.exe competitors.py --init-db
```

`--init-db`检查建库并初始化表结构，不调用Apify。`--execute`自动执行同样的初始化，无需先手动运行此命令。表SQL可重复执行，不删除历史；它不是旧表结构迁移工具。001是Python使用的SQL模板，不应直接传给psql。默认使用已有 postgres 库；手工初始化 public schema 可用：

```powershell
psql -h localhost -p 5432 -U postgres -d postgres -v ON_ERROR_STOP=1 -c "SET search_path TO public" -f sql/002_create_tables.sql
psql -h localhost -p 5432 -U postgres -d postgres -v ON_ERROR_STOP=1 -c "SET search_path TO public" -f sql/003_daily_prices.sql
```

抓取：

```powershell
$env:APIFY_TOKEN = '你的Apify token'
.\.venv\Scripts\python.exe competitors.py --execute --limit-runs 1
```

默认预览仍不连接数据库。执行前验证数据库可写，之后才启动付费Actor。不再生成CSV；JSON仅作本地恢复备份。数据库保存全部候选和原始记录，视图提供匹配竞品。新批次保留新报价，不覆盖历史；同一个查询内酒店以规范URL（移除查询参数）生成SHA256键去重。不同搜索区域的结果保留各自来源，汇总时需去重。

## 数据关系

`collection_batches` 1→N `collection_queries` 1→N `hotel_quotes`。

### collection_batches：一次命令执行

| 字段 | 类型 | 含义 |
|---|---|---|
| id | UUID PK | 采集批次 |
| own_hotel / actor | TEXT | 自家酒店、Actor标识 |
| config / queries | JSONB | 配置快照、完整搜索计划，不含连接密码或token |
| status | TEXT | running / succeeded / failed |
| started_at / finished_at | TIMESTAMPTZ | 数据库记录的开始、结束时间 |
| error_message | TEXT nullable | 失败异常类型，不记录可能包含凭据的异常全文 |

### collection_queries：单个日期和人数组合

| 字段 | 类型 | 含义 |
|---|---|---|
| id | BIGINT identity PK | 搜索任务ID |
| batch_id | UUID FK | 所属批次 |
| query_index | INTEGER | 批次内序号，与batch_id共同唯一 |
| input | JSONB | 目的地、日期、人数、儿童年龄等输入 |
| apify_run_id | TEXT nullable | 云端run ID |
| run_metadata | JSONB nullable | 云端运行状态、费用和dataset信息 |
| status | TEXT | 初始running、Apify状态或stored（报价已完整写入） |

云端成功但数据库写入失败时任务可停留SUCCEEDED，批次为failed；可利用本地raw.json恢复。进程强制结束可能留下running，需要依据run ID检查。

### hotel_quotes：酒店报价快照

| 字段 | 类型 | 含义 |
|---|---|---|
| id / query_id | BIGINT PK / FK | 报价ID、搜索任务ID |
| hotel_key | TEXT | 酒店身份哈希，与query_id共同唯一 |
| name / url / property_type / address | TEXT nullable | 名称、链接、住宿类型、地址 |
| areas | TEXT[] | 地址证据识别的热点区域 |
| latitude / longitude | DOUBLE PRECISION nullable | 经纬度 |
| distance_from_center_km | NUMERIC(12,3) nullable | 距配置中心的直线公里数 |
| location_status | TEXT | match / outside / unknown |
| check_in / check_out | DATE | 查询入住/退房日 |
| nights / adults | SMALLINT | 晚数、成人数 |
| children_ages | SMALLINT[] | 儿童年龄，数组长度即儿童数 |
| total_guests / rooms_requested | SMALLINT | 总人数、房间数 |
| currency | CHAR(3) | 标准化价格币种JPY；其他币种不转换 |
| nightly_jpy / stay_total_jpy | NUMERIC(14,2) nullable | 平均每晚及全程报价，未知不写0 |
| rating / review_count | NUMERIC(6,2) / INTEGER nullable | 评分、评论数量 |
| amenities / room_offers | JSONB | 设施、完整房型报价及容量证据 |
| capacity_evidence | TEXT | 明确可用容量证据或仅搜索人数、待验证 |
| guest_origin_evidence / tax_inclusion | TEXT | 客源国籍、含税证据；目前unknown |
| scraped_at | TIMESTAMPTZ nullable | 上游抓取时间，缺失/不合法/无时区则NULL，原文仍在raw_data |
| collected_at | TIMESTAMPTZ | 入库时间 |
| query_destination | TEXT | 搜索目的地 |
| status | TEXT | match / review_or_excluded |
| reasons | TEXT[] | 排除或待核实原因 |
| raw_data | JSONB | 完整上游酒店原始记录 |

时间使用TIMESTAMPTZ；展示时转换日本时区。价格使用NUMERIC防止浮点累加误差。日期、酒店历史及匹配价格有索引。

## 查询示例

```sql
SELECT name, check_in, nights, adults, children_ages,
       nightly_jpy, stay_total_jpy, rating, areas
FROM competitor_quotes
ORDER BY collected_at DESC, nightly_jpy;

-- 某批次的匹配报价：同酒店、日期、人数跨区域去重
SELECT DISTINCT ON (hotel_key, check_in, check_out, adults, children_ages)
       name, check_in, check_out, adults, children_ages, nightly_jpy
FROM competitor_quotes
WHERE batch_id = '替换为终端输出的批次UUID'::uuid
ORDER BY hotel_key, check_in, check_out, adults, children_ages, collected_at DESC;

SELECT name, nightly_jpy, collected_at AT TIME ZONE 'Asia/Tokyo' AS collected_at_jst
FROM hotel_quotes
WHERE name ILIKE '%酒店名%'
ORDER BY collected_at;
```

驱动与事务参考：https://www.psycopg.org/psycopg3/docs/basic/usage.html
建库参考：https://www.postgresql.org/docs/current/sql-createdatabase.html
