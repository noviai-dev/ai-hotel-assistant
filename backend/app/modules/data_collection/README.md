# 数据抓取模块

支持从已授权的 HTTP JSON 接口抓取数据。API 只接收配置的数据源名称；URL 由管理员通过环境变量配置，不能由请求指定。

## 配置

在 .env 中设置：

```dotenv
DATA_COLLECTION_SOURCES={"booking":"https://example.com/authorized/hotels"}
DATA_COLLECTION_TIMEOUT_SECONDS=15
DATA_COLLECTION_MAX_RESPONSE_BYTES=2097152
```

上面的地址是配置示例，请替换为已获得访问权限的实际接口。默认没有配置数据源。


请求：`POST /api/v1/data-collection/collect`，JSON 请求体为 `{"source":"booking"}`。

响应包含 source、UTC fetched_at、record_count 和 records。上游支持一个 JSON 对象或对象数组。未知数据源返回 404；上游失败、JSON 格式错误或超出大小限制返回 502。不会跟随重定向。

数据直接返回，不持久化，不包含定时任务或后台队列。当前适配器适用于无需认证的 JSON 接口；需要密钥、分页或平台字段转换时，可实现 DataSource 协议并注册到 CollectionService。不要在 URL 中配置密钥。部署对外开放前应接入项目的身份验证。

## 根目录入口

配置数据源后，在 backend 根目录运行：

```sh
python main.py booking
```

入口调用与 API 共用的抓取服务，输出 JSON 结果。数据源未配置或抓取失败时输出错误信息并返回退出码 1。使用 `python main.py --help` 查看参数说明。
