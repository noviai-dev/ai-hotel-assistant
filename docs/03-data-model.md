# 核心数据模型草案

所有业务实体至少带 `tenant_id`、`created_at`、`updated_at`。生产实现需用外键、迁移和数据库级租户隔离策略补全。

| 实体 | 主要字段 | 用途 |
|---|---|---|
| Tenant | id, name, locale, timezone | 酒店集团/客户隔离 |
| Property | id, tenant_id, name, address, website | 单体酒店/门店 |
| MarketSnapshot | property_id, stay_date, room_type, own_price, availability, source, captured_at | 市场与自有经营快照 |
| CompetitorSnapshot | property_id, competitor, room_type, price, source, captured_at | 竞品价格观测 |
| Recommendation | property_id, type, payload, rationale, confidence, source_refs, status, expires_at | 可审计的经营建议 |
| GeoPrompt | property_id, locale, prompt_text, version, enabled | GEO 巡检问题集 |
| GeoRun | property_id, provider, model, prompt_version, started_at, status | 一次巡检任务 |
| GeoObservation | run_id, answer, brand_mentions, citations, competitor_mentions | GEO 结果与引用 |
| KnowledgeDocument | property_id, title, source, version, status | 客服知识来源 |
| Conversation | property_id, channel, guest_ref, status, assigned_to | 客服会话 |
| Message | conversation_id, role, content, citations, confidence, created_at | 对话记录 |
| ServiceTicket | conversation_id, category, room_ref, description, priority, status, confirmed_by | 服务工单 |
| AuditEvent | actor, tenant_id, action, target, metadata, created_at | 关键操作审计 |
