# Vue 日期前端

Vue 3 + Vite + Vue Router。需要 Node.js 20.19+ 或 22.12+。

## 本地启动

```bash
cd frontend
npm install
npm run dev
```

打开终端显示的地址（默认 http://localhost:5173）。

- `/`：显示浏览器本地时区的当前日期，格式为 `YYYY/MM/DD`，跨午夜自动更新。
- `/2026/10/10`：显示 `2026/10/10`。
- `/:year/:month/:day`：支持其他有效日期，年份四位、月份和日期两位。
- 无效日期（例如 `/2026/02/30`）或其他路径显示提示。

有效日期页面分为「NOVI Dotonbori」和「住一」两个酒店区块，每个区块包含房型 A、房型 B 的价格模块。每个模块展示 Vue Data UI 多系列折线图和 K 线图，两图共用该房型的数据，各房型独立生成模拟数据。始终以浏览器本地的今天为基准，横轴包含今天后第 30～45 天（含首尾）的 16 个入住日期，格式为 `MM/DD`；每个入住日期有从 6 天前至今天、每天一次的 7 条采集记录，价格为 20000～40000 内的随机整数。小屏可横向滚动查看。

## 验证与构建

折线图中今日采集为蓝色，其余 6 次采集为灰色。悬停提示展示入住日期、7 个采集日期及价格。K 线开盘价和收盘价均等于今日采集价，最高价和最低价取 7 次采集的极值；蓝色横线标识今日价格。点击“重新生成本房型数据”按钮同时刷新该模块内的两张图。实际每天采集 +30～+51 天的入住价格，连续运行 7 天即可为展示区间积累这些历史记录。

```bash
npm test
npm run build
npm run preview
```

## Nginx 部署

构建产物位于 `dist/`。仓库提供 `nginx.conf` 站点配置，默认监听所有 IPv4 网卡的 80 端口，站点目录为 `/var/www/ai-hotel-assistant`。无需启动 Vite，也无需转发到 5173。

在安装了 Nginx 的 Linux 服务器上，从项目的 `frontend` 目录执行（构建产物也可在本地生成后上传）：

```bash
npm ci
npm run build
sudo mkdir -p /var/www/ai-hotel-assistant
sudo cp -R dist/. /var/www/ai-hotel-assistant/
sudo cp nginx.conf /etc/nginx/conf.d/ai-hotel-assistant.conf
sudo nginx -t
# 仅在检查成功后执行：
sudo systemctl reload nginx
```

此文件是 `server` 配置块，应由主配置的 `http` 块加载，不要用它覆盖 `/etc/nginx/nginx.conf`。若主配置没有加载 `/etc/nginx/conf.d/*.conf`，请在 `http` 块中加入对应的 `include`。

此配置使用 `listen 80 default_server;`，通过服务器 IPv4 地址访问时会命中本前端。若其他站点也为同一监听地址声明了 `default_server`，需移除其他站点的该标记，再执行 `nginx -t` 并重新加载，避免默认站点冲突。使用域名时，将 `server_name _;` 改为实际域名；修改站点目录时同步修改 `root`。

配置已包含 Vue Router History 模式回退规则，支持直接访问和刷新 `/2026/10/10` 等路径；HTML 每次重新验证，Vite 带哈希的静态资源长期缓存，缺失资源返回 404。
