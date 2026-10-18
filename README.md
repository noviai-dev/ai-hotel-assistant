# 酒店 AI 助手项目骨架

面向酒店经营团队的模块化 AI 助手。竞品采集由 `backend/competitors.py` 负责；营销分析由独立的 Python + OpenAI API worker 负责，支持定时读取数据库和保存建议。GEO、客服和前端仍为规划或占位，营销建议需人工审核。

## 模块

- **市场决策助手**：需求与预订节奏分析、竞品监测、定价/渠道建议。所有建议保留来源、置信度和人工审核状态。
- **GEO 助手**：管理品牌问题集，记录模型答案、品牌提及/引用来源和竞品表现，生成巡检报告。自动化查询通过受支持的 API/服务适配器接入。
- **AI 客服助手**：基于酒店知识库回答咨询；识别服务请求并创建工单；低置信度、负面情绪或高风险情况转人工。

## 技术假设

- API：Python 3.12、FastAPI、Pydantic
- 数据：PostgreSQL；后续异步任务可加入 Redis/Celery
- Web：Next.js / TypeScript（前端目录为占位骨架）
- 部署：Docker Compose（本地开发），生产部署方式待定

## 本地启动

Linux / WSL 部署可使用启动与停止脚本（需要 Bash、Docker Compose v2，以及已安装并运行的 cron 服务）：

```bash
chmod +x bin/start.sh bin/stop.sh
./bin/start.sh
# 停止服务并移除定时任务
./bin/stop.sh
```

运行前先在根目录 `.env` 配置 `POSTGRES_PASSWORD` 和 `APIFY_TOKEN`。
`start.sh` 启动基础服务、初始化营销报告/邮件表，并在当前用户的 crontab 注册每天 **05:00**
执行竞品采集、每天 **09:00** 执行 `docker compose run --build --rm -T marketing run`，生成报告后发送邮件。按部署机器本地时区计算
（日本时间请将机器时区设为 `Asia/Tokyo`）。重复启动会更新本项目的任务，不会重复添加。
采集日志追加到 `logs/competitors.log`，营销和邮件日志追加到 `logs/marketing.log`；启动时不会立即采集或分析，机器关闭期间错过的任务不会补跑。
需在 `.env` 配置营销模型、酒店、SMTP参数及 `MARKETING_EMAIL_ENABLED=true`。
脚本会停止已有常驻营销worker，避免与cron重复调度；cron的09:00不受 `MARKETING_HOUR` 影响。
请使用同一用户执行两个脚本；该用户需有 Docker 权限，cron 执行时 Docker 也必须运行。
`stop.sh` 会停止包含采集任务在内的 Compose 容器，保留数据库和备份文件。

先启动 PostgreSQL：在项目根目录复制 `.env.example` 为 `.env`，填写 `POSTGRES_PASSWORD`，
然后运行 `docker compose up -d`。数据保存在根目录 `data/postgres/`，默认每 24 小时备份到
`backups/postgres/` 并保留 7 天。连接参数、手动备份与恢复步骤见 [基础设施说明](infra/README.md)。

竞品采集也可直接在容器中运行：填写根目录 `.env` 的 `APIFY_TOKEN`，执行
`docker compose build competitors`，然后执行 `docker compose run --rm competitors`。
默认执行 `competitors.py --execute --limit-runs 1`；预览与单独初始化命令见基础设施说明。

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m marketing init-db
python -m marketing run --dry-run
python -m marketing run
python -m marketing latest
```

先配置 `.env` 中的 `MARKETING_HOTEL`、本地 `PG*` 变量，以及正式分析需要的 `OPENAI_API_KEY`、`OPENAI_MODEL`。
目前入口为 CLI/定时 worker，没有启动 HTTP 服务。完整命令、报告结构和限制见 [营销服务说明](backend/MARKETING.md)。
已有数据库先执行 `docker compose run --build --rm marketing init-db` 创建 `a_marketing_reports` 报告表。
Docker 启动定时分析：`docker compose --profile marketing up -d --build marketing`，默认每天日本时间 09:00 执行。

## 目录

```text
backend/app/       API、配置、模块服务与外部适配器
backend/marketing/ 指标查询、OpenAI建议、报告存储与定时worker
frontend/          Next.js 前端结构占位
infra/             本地开发基础设施
 docs/              需求、架构、数据模型、API 与路线图
```

## 关键约束

1. AI 输出是建议或草稿；价格修改、对客发送和退款等操作须经过权限校验及人工确认。
2. 酒店、门店、用户和会话数据必须按 tenant 隔离；日志避免记录不必要的个人信息。
3. 客服知识回答应附来源；缺少依据时明确转人工。
4. 市场建议展示数据时点、来源、假设和置信度，不把估算值呈现成事实。
5. GEO 巡检记录模型、问题模板、语言、时间与采集方式，避免将单次回答当作稳定排名。

## 下一步

先确定首家试点酒店、PMS/OTA 接口权限、客服渠道、GEO 采集方式和数据保留规则，再实现数据库迁移、鉴权、租户隔离及首个端到端流程。
