-- Run after 002 in postgres/public by default. Safe to rerun on an existing installation.
BEGIN;
CREATE INDEX IF NOT EXISTS hotel_quotes_daily_idx
ON hotel_quotes(check_in, hotel_key, adults, children_ages, collected_at DESC) WHERE nights=1;
-- All valid daily quotes, including competitors whose prices leave the target band.
-- Never interpret an absent quote as sold out or as zero price.
CREATE OR REPLACE VIEW daily_hotel_prices AS
SELECT q.*, q.check_in AS stay_date,
       (q.collected_at AT TIME ZONE 'Asia/Tokyo')::date AS observation_date_jst,
       r.batch_id, r.apify_run_id,
       NOT ('price_outside_range'=ANY(q.reasons)) AS in_target_price_band
FROM hotel_quotes q JOIN collection_queries r ON r.id=q.query_id
WHERE q.nights=1 AND q.check_out=q.check_in+1
  AND q.nightly_jpy IS NOT NULL
  AND NOT (q.reasons && ARRAY['price_unknown_or_non_jpy','type_unknown_or_excluded',
      'location_outside','location_unknown','dates_mismatch','own_hotel']::text[]);
CREATE OR REPLACE VIEW latest_daily_hotel_prices AS
SELECT DISTINCT ON (hotel_key, stay_date, adults, children_ages, rooms_requested)
       * FROM daily_hotel_prices
ORDER BY hotel_key, stay_date, adults, children_ages, rooms_requested,
         collected_at DESC, id DESC;
COMMIT;
