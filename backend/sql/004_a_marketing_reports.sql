-- Marketing tables use the a_ prefix. Existing collection tables are unchanged.
CREATE TABLE IF NOT EXISTS a_marketing_reports (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    own_hotel TEXT NOT NULL,
    run_key TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN
        ('running', 'preview', 'no_data', 'succeeded', 'failed')),
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (own_hotel, run_key)
);
CREATE INDEX IF NOT EXISTS a_marketing_reports_hotel_latest_idx
    ON a_marketing_reports (own_hotel, id DESC);
COMMENT ON TABLE a_marketing_reports IS '营销分析运行记录、指标快照及待审核建议';
