# API 草案

统一前缀 `/api/v1`。成功响应和错误格式、鉴权与分页策略需在实现阶段定稿。

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/health` | 健康检查 |
| GET | `/market/properties/{property_id}/overview` | 市场与预订节奏概览 |
| POST | `/market/properties/{property_id}/recommendations` | 生成经营建议 |
| POST | `/market/recommendations/{id}/review` | 审核/驳回建议 |
| POST | `/geo/properties/{property_id}/runs` | 创建 GEO 巡检 |
| GET | `/geo/runs/{run_id}` | 查看巡检状态和结果 |
| GET | `/geo/properties/{property_id}/reports` | 获取巡检报告列表 |
| POST | `/concierge/properties/{property_id}/conversations` | 创建客服会话 |
| POST | `/concierge/conversations/{id}/messages` | 对话并检索知识 |
| POST | `/concierge/conversations/{id}/handoff` | 转人工 |
| POST | `/concierge/conversations/{id}/tickets` | 创建服务工单（待确认） |

客服消息响应草案：`answer`, `citations[]`, `confidence`, `handoff_required`, `suggested_ticket`。
市场建议响应草案：`recommendation`, `rationale`, `source_refs[]`, `confidence`, `valid_until`, `requires_approval`。
