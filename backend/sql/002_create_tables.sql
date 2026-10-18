-- Run against postgres with search_path=public by default. Safe to rerun; does not delete existing data.
BEGIN;
CREATE TABLE IF NOT EXISTS collection_batches (
    id UUID PRIMARY KEY,
    own_hotel TEXT NOT NULL,
    actor TEXT NOT NULL,
    config JSONB NOT NULL,
    queries JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running','succeeded','failed')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    error_message TEXT
);
CREATE TABLE IF NOT EXISTS collection_queries (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    batch_id UUID NOT NULL REFERENCES collection_batches(id),
    query_index INTEGER NOT NULL,
    input JSONB NOT NULL,
    apify_run_id TEXT,
    run_metadata JSONB,
    status TEXT NOT NULL DEFAULT 'running',
    UNIQUE (batch_id, query_index)
);
CREATE TABLE IF NOT EXISTS hotel_quotes (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    query_id BIGINT NOT NULL REFERENCES collection_queries(id),
    hotel_key TEXT NOT NULL,
    name TEXT,
    url TEXT,
    property_type TEXT,
    address TEXT,
    areas TEXT[] NOT NULL DEFAULT '{}',
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    distance_from_center_km NUMERIC(12,3),
    location_status TEXT NOT NULL,
    check_in DATE NOT NULL,
    check_out DATE NOT NULL CHECK (check_out > check_in),
    nights SMALLINT NOT NULL CHECK (nights > 0),
    adults SMALLINT NOT NULL CHECK (adults > 0),
    children_ages SMALLINT[] NOT NULL,
    total_guests SMALLINT NOT NULL,
    rooms_requested SMALLINT NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'JPY',
    nightly_jpy NUMERIC(14,2),
    stay_total_jpy NUMERIC(14,2),
    rating NUMERIC(6,2),
    review_count INTEGER,
    amenities JSONB NOT NULL,
    room_offers JSONB NOT NULL,
    capacity_evidence TEXT NOT NULL,
    guest_origin_evidence TEXT NOT NULL,
    tax_inclusion TEXT NOT NULL,
    scraped_at TIMESTAMPTZ,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    query_destination TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('match','review_or_excluded')),
    reasons TEXT[] NOT NULL DEFAULT '{}',
    raw_data JSONB NOT NULL,
    UNIQUE (query_id, hotel_key)
);
CREATE INDEX IF NOT EXISTS hotel_quotes_dates_idx ON hotel_quotes(check_in, check_out);
CREATE INDEX IF NOT EXISTS hotel_quotes_hotel_history_idx ON hotel_quotes(hotel_key, collected_at DESC);
CREATE INDEX IF NOT EXISTS hotel_quotes_match_price_idx ON hotel_quotes(nightly_jpy) WHERE status='match';
CREATE INDEX IF NOT EXISTS collection_queries_batch_idx ON collection_queries(batch_id);
CREATE OR REPLACE VIEW competitor_quotes AS
SELECT q.*, r.batch_id, r.apify_run_id FROM hotel_quotes q
JOIN collection_queries r ON r.id=q.query_id WHERE q.status='match';
COMMENT ON TABLE hotel_quotes IS '每次查询的酒店报价快照；跨批次保留历史，不覆盖旧报价';
COMMENT ON COLUMN hotel_quotes.raw_data IS 'Apify原始酒店记录，用于审计及重新解析';
COMMENT ON COLUMN hotel_quotes.nightly_jpy IS '一间房/公寓平均每晚JPY报价；未知为NULL';
COMMENT ON COLUMN hotel_quotes.scraped_at IS '数据源抓取时间；缺失或无法解析为NULL';
COMMENT ON COLUMN hotel_quotes.collected_at IS '本地写入数据库时间';
COMMIT;
