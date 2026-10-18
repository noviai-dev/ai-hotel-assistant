# 营销分析服务

`competitors.py → PostgreSQL → marketing worker → PostgreSQL的a_marketing_reports报告表`。

## 配置与运行

在项目根目录 `.env` 补充 `.env.example` 的营销变量，不要覆盖已有密钥。
`MARKETING_HOTEL` 必须与采集配置中的 `own_hotel` 完全一致。
`OPENAI_MODEL` 由你填写账户可用且支持 Responses API + Structured Outputs 的模型；不默认选择收费模型。

本地运行（项目根目录，Python 3.12+）：

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r backend/requirements.txt
cd backend
../.venv/Scripts/python -m marketing init-db
../.venv/Scripts/python -m marketing run --dry-run
../.venv/Scripts/python -m marketing run
../.venv/Scripts/python -m marketing latest
../.venv/Scripts/python -m marketing schedule
```

Linux 使用 `.venv/bin/python`。本地连接使用 `PGHOST/PGPORT/PGUSER/PGPASSWORD/PGDATABASE`，
不要混淆 Docker 初始化用的 `POSTGRES_*`。本地 `PGPASSWORD` 应与数据库密码一致。
根目录 `.env` 自动加载，进程环境变量优先。首次需按 COMPETITORS.md 初始化数据库并完成采集。

Docker（项目根目录）：

```bash
docker compose build marketing
docker compose run --rm marketing init-db
docker compose run --rm marketing run --dry-run
docker compose run --rm marketing run
docker compose run --rm marketing latest
docker compose --profile marketing up -d marketing
docker compose logs marketing
docker compose stop marketing
```

默认按 Asia/Tokyo 每天09:00运行；当日09:00后启动会尝试补跑当天，不补历史日期。
同酒店、同日、同模式只占用一个运行记录，PostgreSQL唯一约束避免重复进程重复调用模型。
预览与正式运行分开去重；失败、无数据或进程被终止留下的 running 状态不会自动重跑。
修正配置或采集数据后用 `run --force` 手动重试（可能再次收费）。SDK对瞬时API错误最多重试2次。
定时进程每30秒检查，不在Web进程中启动，多个worker可共用同一PostgreSQL数据库。

## 数据口径与报告

- 固定只读SQL，按本店标识隔离成功批次，使用 `daily_hotel_prices` 单晚报价。
- 同竞品、入住日、成人数、儿童年龄和房间数仅保留窗口内最新快照；包含超出目标价带的有效报价。
- 默认分析未来60天、最近7天采集的数据；按相同入住条件计算样本数、最低/中位/最高价格及采集时间。
- SQL事务强制只读并设30秒超时。运行账户需要采集表/视图的SELECT权限，以及a_marketing_reports的SELECT、INSERT、UPDATE和身份序列USAGE权限；建表权限仅初始化时需要。
- 超过500个分组报错，避免静默截断；没有有效数据保存 `no_data`，不调用API。
- 只有单晚报价会参与分析。采集配置若只有3–5晚套餐，需要另外采集单晚数据或扩展指标查询。

报告写入现有 PostgreSQL（复用 `PG*` 配置）的 `public.a_marketing_reports`。
所有新增营销表均以 `a_` 开头，现有竞品采集表保持原名。
表包含运行标识、本店标识、状态、创建/更新时间，以及 JSONB payload：指标快照、模型、提示词版本、
待审核状态、建议与证据ID、数据缺口、API响应ID及token用量。失败保留错误类型，避免写入密钥。
`latest` 读取当前酒店的最新尝试（可能失败或无数据），不是只读取最新成功报告。
报告随现有PostgreSQL备份一起保存，不再创建SQLite文件或报告目录挂载。

SQL脚本为 `sql/004_a_marketing_reports.sql`。全新Docker数据库会自动执行；已有数据库需要运行
`python -m marketing init-db` 或上述Docker初始化命令。初始化可重复执行，不删除现有记录。
常规run/schedule/latest不会自动建表。若之前自行生成过SQLite报告，它们不会自动导入或删除。

模型使用官方 `responses.parse` + Pydantic 结构化输出：
https://developers.openai.com/api/docs/guides/structured-outputs
拒绝、不完整输出和无效证据ID不会标记成功。证据ID校验不等于建议内容已被事实验证。

当前不提供HTTP接口、活动执行、审批工作流或效果回传；`review_status=pending`仅为预留字段。
本店订单、库存、成本与预算尚未接入，不能计算真实入住率、利润或营销ROI。
下一步在 repository 增加这些指标，并接入审核与活动效果记录。

## 测试

```powershell
cd backend
../.venv/Scripts/python -m unittest discover -p "test_*.py"
```

默认测试不调用付费API；PostgreSQL集成测试通过 `TEST_POSTGRES=1` 显式启用。

## 每日邮件

根目录 `.env` 已补充邮件参数空值，不覆盖已有设置。填写：

```dotenv
MARKETING_EMAIL_ENABLED=true
MARKETING_EMAIL_TO=recipient@example.com
MARKETING_EMAIL_FROM=sender@example.com
SMTP_HOST=smtp.example.com
SMTP_PORT=465
SMTP_SECURITY=ssl
SMTP_USERNAME=sender@example.com
SMTP_PASSWORD=邮箱SMTP授权码
```

收件人和发件人均填写单个纯邮箱地址。465端口通常使用ssl，587通常使用starttls；
按邮箱服务商要求配置。用户名/密码可同时为空以使用受信SMTP中继。禁止明文SMTP。
密码仅通过环境变量读取，不写入报告或错误日志。

已有数据库先再次执行 `docker compose run --build --rm marketing init-db`，
新增 `a_report_emails`（初始化可重入）。运行账户需该表SELECT、INSERT、UPDATE权限。
再运行 `docker compose --profile marketing up -d --build marketing`。
每天按 `MARKETING_TIMEZONE` / `MARKETING_HOUR`（默认日本时间09:00）生成并邮件发送。
手动 `run` 同样会发送；`run --dry-run` 不调用模型也不发送邮件。
邮件包含中文纯文本建议与完整JSON报告附件；无数据时发送数据不足通知，分析失败不发送报告。

发送状态保存在 `a_report_emails`：sending / sent / failed。sent仅表示SMTP服务器已接收。
同一运行记录只自动尝试发送一次；再次执行run可补发尚未创建发送记录的已完成报告。
补发失败邮件无需重新调用模型：

```bash
docker compose run --rm marketing send-email --run-key '酒店名:2026-10-18:live' --retry-email
```

请替换为实际run_key。SMTP断线可能发生在服务器已接收邮件之后，补发前请检查收件箱。
进程中断或发送成功但状态写入失败可能留下sending，需核实投递结果后由管理员处理；
不自动重试sending，避免重复发送。`run --force`生成新报告并发送新邮件，不用于邮件补发。
SMTP和数据库之间无法保证严格恰好一次投递。此功能尚不包括退信追踪。
