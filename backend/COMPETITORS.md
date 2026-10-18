# NOVI Dotonbori 竞品采集

结果写入PostgreSQL。初始化、运行步骤及完整字段字典见 [POSTGRESQL.md](POSTGRESQL.md)。

独立命令行程序，不修改现有API。现在抓取未来入住日期的实时公开报价，不是等待一个月后再运行。

## 使用（PowerShell，在 backend 目录）

```powershell
python -m pip install -r requirements.txt
python competitors.py --limit-runs 1
$env:PGPASSWORD = '123456'
# 可选：单独初始化；--execute 也会自动检查建库并初始化表结构
python competitors.py --init-db
$env:APIFY_TOKEN = '你的Apify API token'
python competitors.py --execute --limit-runs 1
```

token在 https://console.apify.com/settings/integrations 获取，仅通过环境变量传入，不写入输出文件。Codex MCP OAuth登录与Python API认证独立；程序不会读取MCP凭据。

预览默认不访问网络、不收费。`--execute`才启动Actor。示例从2026-11-11开始连续30天、每次1晚、总人数3/4/5/6、1/2儿童共240组；成年人=总人数减儿童。5岁、8岁为待确认假设。一间房/公寓，目标价带每晚15,000–23,000 JPY，但不会过滤掉涨出价带的报价。价格是当前查询时的报价，不能代表未来最终成交价。

修改 `competitors.example.json` 或复制成自己的JSON并使用 `--config 文件路径`：

- `check_in`: 固定入住日期；默认设为null，或省略该字段，每次按当前日本日期计算40天后的日期。
- `children_ages`: 每名儿童实际年龄，影响报价。
- `destinations`: 默认大阪一次城市搜索。可添加 `Tennoji, Osaka, Japan`、`Shinsaibashi, Osaka, Japan`、`Chuo-ku, Osaka, Japan`、`Umeda, Osaka, Japan`、`Namba, Osaka, Japan`、`Dotonbori, Osaka, Japan` 来补充热点搜索，但会按目的地倍增运行次数和费用上限。仅凭搜索关键词不判定酒店位于该区。
- `center`: 填入你认定的市中心 `[纬度, 经度]`。大阪多中心，默认null不猜测；未填写时只能依据地址识别热点，缺少地址/坐标的记录放入待核实表。直线距离不等于步行距离。
- `max_results`: 每组最多50条，有限采样，不是大阪完整酒店名录。
- `calendar_days`: 入住日期覆盖天数，默认30；`nights=[1]`查询真实单晚报价，3–5晚为可选套餐模式。
- `hotel_urls`: 固定竞品Booking酒店链接数组，留空则按目的地搜索。
- `max_charge_usd_per_run`: 每次Actor运行的Apify费用上限，默认0.5美元；240组配置上限合计120美元，实际计费以Apify为准。详情抓取可能额外计费，上限可能导致结果不完整。先跑1组检查结果后，再移除 `--limit-runs`。

## 输出

每次创建独立 `competitor_output/时间戳/` 目录：

- `manifest.json`: 搜索条件和Actor名称。
- `query_*/run.json`: 可追踪的Apify运行状态与费用信息；失败后可在Console检查。程序不自动重试付费启动，避免重复收费。
- `query_*/raw.json`: 成功运行的原始数据。
- PostgreSQL `hotel_quotes`: 全部报价记录，包含未确认及排除原因、房型、设施、价格、评分及原始JSON。
- PostgreSQL `competitor_quotes` 视图: 类型、JPY价格与“半径以内或热点地址”均匹配的竞品报价。
- PostgreSQL `collection_batches` / `collection_queries`: 搜索计划、批次状态、云端run信息。

不再生成CSV。每次运行保存新的报价快照，同查询内酒店去重，不同入住日期、晚数及人数组合独立保存。中断或失败保留此前完成的任务数据，终端非零退出。云端运行达到超时会停止；网络断开时它可能仍运行，凭run ID检查Console。不要直接重跑不确定是否已启动的POST。

## 证据边界

韩/台/中/日是目标客源，酒店列表没有客人国籍字段，`guest_origin_evidence=unknown`。不能用日文/韩文/中文页面语言推断国籍。客源占比需额外的带国家信息的住客评价或自己的经营数据，本版不虚构占比。

Actor查询传入实际成人数和儿童年龄；房型有明确可用且容量足够时标记 `available_room_capacity`，否则标记 `search_party_only_unverified`，须人工检查。酒店搜索报价不一定对应返回房型中同一报价。税费/取消条款没有可靠字段时不推定，`tax_inclusion=unknown`。缺失价格不记为零，空结果不记为售罄。默认排除名称完全相同的自家酒店；不同别名需要人工核对。类型/坐标/地址字段变动会使记录进入待核实或导致适配失败，保留原始数据便于修正。

选择的社区Actor及输入/输出依据：
https://apify.com/solidcode/booking-scraper
https://apify.com/solidcode/booking-scraper/input-schema
API运行及分页依据：
https://docs.apify.com/api/v2/actors-runs-post
https://docs.apify.com/api/v2/dataset-items-get

这是按公布接口实现的适配器，尚需用你的token实测该Actor在大阪的当前结果质量；不保证平台实时可用性。

离线验证：`python -m unittest test_competitors -v`。
