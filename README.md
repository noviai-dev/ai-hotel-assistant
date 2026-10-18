# 酒店 AI 助手项目骨架

面向酒店经营团队的模块化 AI 助手，覆盖市场决策、GEO 品牌可见性和 AI 客服。当前为 MVP 项目骨架，外部数据与模型适配器均为接口占位，不能直接用于生产经营决策。

## 模块

- **市场决策助手**：需求与预订节奏分析、竞品监测、定价/渠道建议。所有建议保留来源、置信度和人工审核状态。
- **GEO 助手**：管理品牌问题集，记录模型答案、品牌提及/引用来源和竞品表现，生成巡检报告。自动化查询通过受支持的 API/服务适配器接入。
- **AI 客服助手**：基于酒店知识库回答咨询；识别服务请求并创建工单；低置信度、负面情绪或高风险情况转人工。

## 技术假设

- API：Python 3.12、FastAPI、Pydantic
- 数据：PostgreSQL；后续异步任务可加入 Redis/Celery
- Web：Next.js / TypeScript（前端目录为占位骨架）
- 部署：Docker Compose（本地开发），生产部署方式待定

## 本地启动（API）

Linux / WSL 部署可使用启动与停止脚本（需要 Bash、Docker Compose v2，以及已安装并运行的 cron 服务）：

```bash
chmod +x bin/start.sh bin/stop.sh
# nohup ./bin/start.sh > start.log 2>&1 &
./bin/start.sh
# 停止服务并移除定时任务
./bin/stop.sh
```

运行前先在根目录 `.env` 配置 `POSTGRES_PASSWORD` 和 `APIFY_TOKEN`。
`start.sh` 执行 `docker compose up -d`，并在当前用户的 crontab 注册每天 **05:00**
执行 `docker compose run --build --rm competitors`，按部署机器本地时区计算
（日本时间请将机器时区设为 `Asia/Tokyo`）。重复启动会更新本项目的任务，不会重复添加。
采集日志追加到 `logs/competitors.log`；启动时不会立即采集，机器关闭期间错过的任务不会补跑。
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
uvicorn app.main:app --reload
```

接口文档：`http://127.0.0.1:8000/docs`。当前只提供健康检查与模块占位端点。

## 目录

```text
backend/app/       API、配置、模块服务与外部适配器
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
