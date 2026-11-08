-- 模拟酒店报价；全部价格、评分、房型均为假数据，不代表真实酒店信息。
-- 2026-10-26 至 2026-11-05（日本时间），每天同样的30家酒店。
-- 按明确列出的 x=30..40 生成11条/酒店/天，共11批、121次查询、3630条报价。
-- 名单中的“ホテル春日出，a”保留为一个名称，名单共30家。
-- currency 固定为 JPY（币种是类别，不做数值波动）。
-- nightly_jpy = 基准价 ×（1 + 采集日周期 + 提前天数周期 + 入住周末溢价）。
-- stay_total_jpy = nightly_jpy + 每次入住清洁费；均为一晚、一间房、2成人+5岁儿童。
-- 自包含：补齐 collection_batches / collection_queries 外键，不复用示例 query_id=21。
-- id 使用数据库 identity；稳定批次ID和hotel_key确保重复执行不会增加报价数量。
-- 前置条件：已执行 002_create_tables.sql。只生成/导入模拟记录，不删除数据。
BEGIN;
SET LOCAL TIME ZONE 'Asia/Tokyo';

DO $mock$
DECLARE
    v_date DATE;
    v_collected_at TIMESTAMPTZ;
    v_batch_id UUID;
    v_query_id BIGINT;
    v_check_in DATE;
    v_offset INTEGER;
    v_day INTEGER;
    v_hotel RECORD;
    v_key TEXT;
    v_nightly NUMERIC(14,2);
    v_total NUMERIC(14,2);
    v_count INTEGER;
BEGIN
    FOR v_date IN
        SELECT d::date
        FROM generate_series(DATE '2026-10-26', DATE '2026-11-05', INTERVAL '1 day') AS dates(d)
    LOOP
        v_day := v_date - DATE '2026-10-26';
        v_collected_at := (v_date + TIME '10:00:00') AT TIME ZONE 'Asia/Tokyo';
        v_batch_id := md5('mock-30-osaka-hotels-v1:' || v_date::text)::uuid;

        INSERT INTO public.collection_batches (
            id, own_hotel, actor, config, queries, status, started_at, finished_at
        ) VALUES (
            v_batch_id, 'NOVI Dotonbori', 'synthetic-30-osaka-hotels-v1',
            jsonb_build_object(
                'synthetic', true, 'dataset', 'mock-30-osaka-hotels-v1',
                'destination', 'Osaka, Japan', 'hotel_count', 30,
                'check_in_offsets', ARRAY[30,31,32,33,34,35,36,37,38,39,40],
                'timezone', 'Asia/Tokyo'
            ),
            (SELECT jsonb_agg(jsonb_build_object(
                'check_in', v_date + x, 'check_out', v_date + x + 1,
                'adults', 2, 'children_ages', ARRAY[5], 'rooms', 1
            ) ORDER BY x) FROM generate_series(30,40) AS offsets(x)),
            'succeeded', v_collected_at - INTERVAL '5 minutes', v_collected_at
        ) ON CONFLICT (id) DO UPDATE SET
            config = EXCLUDED.config, queries = EXCLUDED.queries,
            status = EXCLUDED.status, started_at = EXCLUDED.started_at,
            finished_at = EXCLUDED.finished_at;

        FOR v_offset IN 30..40 LOOP
            v_check_in := v_date + v_offset;
            INSERT INTO public.collection_queries (
                batch_id, query_index, input, run_metadata, status
            ) VALUES (
                v_batch_id, v_offset - 29,
                jsonb_build_object(
                    'synthetic', true, 'destination', 'Osaka, Japan',
                    'check_in', v_check_in, 'check_out', v_check_in + 1,
                    'nights', 1, 'adults', 2, 'children_ages', ARRAY[5], 'rooms', 1
                ),
                jsonb_build_object('synthetic', true, 'status', 'SUCCEEDED'), 'stored'
            ) ON CONFLICT (batch_id, query_index) DO UPDATE SET
                input = EXCLUDED.input, run_metadata = EXCLUDED.run_metadata,
                status = EXCLUDED.status
            RETURNING id INTO v_query_id;

            FOR v_hotel IN
                SELECT * FROM (VALUES
                    (1, 'Tamatsukuri Daifuji Kan', 13000, 7000, 'Apartment'),
                    (2, 'Yume夢 松屋町店', 12000, 5000, 'Apartment'),
                    (3, 'Hotel USY和モダン', 11000, 2000, 'Hotel'),
                    (4, 'katsu house 心斋桥', 14500, 4500, 'Apartment'),
                    (5, 'Sakurajima Parkside House B', 15500, 6000, 'Holiday home'),
                    (6, 'メルシアターリゾート3', 12500, 4000, 'Apartment'),
                    (7, 'Suzuran Tengachaya', 9500, 3500, 'Apartment'),
                    (8, '大阪難波ELLY-one', 14000, 4000, 'Apartment'),
                    (9, 'The Ritz-Carlton Osaka', 65000, 0, 'Hotel'),
                    (10, 'Sakura Garden Hotel', 11500, 0, 'Hotel'),
                    (11, 'Bande Hotel Tenpozan Higashi', 10500, 0, 'Hotel'),
                    (12, '民泊越前ビル501号室', 8500, 3000, 'Apartment'),
                    (13, 'R Residence 天下茶屋 IV', 10000, 3500, 'Apartment'),
                    (14, 'G70 大正buttercream', 9000, 3000, 'Apartment'),
                    (15, 'Osaka Urban Residence Kujo', 11000, 4000, 'Apartment'),
                    (16, 'A.A.O BLDG. NAMBA', 15000, 4500, 'Apartment'),
                    (17, 'RE Hotel Umeda', 12500, 0, 'Hotel'),
                    (18, 'ReA house', 9500, 3500, 'Holiday home'),
                    (19, 'HOTEL AARON通天東', 10500, 0, 'Hotel'),
                    (20, 'Welina Hotel Dotonbori', 13500, 0, 'Hotel'),
                    (21, '虹の宿201', 8000, 3000, 'Apartment'),
                    (22, 'Tennouji Townhouse', 16000, 5500, 'Holiday home'),
                    (23, 'Perfect Life難波西', 11500, 3500, 'Apartment'),
                    (24, 'ホテル春日出，a', 9000, 0, 'Hotel'),
                    (25, '花音Kanon', 12000, 4000, 'Apartment'),
                    (26, 'ST BLD Daikoku', 10500, 3500, 'Apartment'),
                    (27, 'Tino Anastasia', 11000, 3500, 'Apartment'),
                    (28, 'Hotel Keihan Tenmabashi', 13000, 0, 'Hotel'),
                    (29, 'jin osaka bay', 10000, 4000, 'Apartment'),
                    (30, 'Nanba southエルメゾン3rd', 11500, 3500, 'Apartment')
                ) AS hotels(hotel_no, hotel_name, base_price, cleaning_fee, property_type)
            LOOP
                -- 独立模拟命名空间；同一家酒店跨日期、跨批次使用同一key。
                v_key := 'synthetic-osaka-v1-' || lpad(v_hotel.hotel_no::text, 2, '0');
                -- 采集日每7天循环；提前天数每5天循环；周五+8%、周六+15%、周日+5%。
                v_nightly := round(v_hotel.base_price::numeric * (
                    1 + (ARRAY[0.00,0.02,0.04,0.06,0.03,-0.01,-0.03])[(v_day % 7) + 1]
                    + (ARRAY[0.00,0.01,0.02,0.01,-0.01])[((v_offset - 30) % 5) + 1]
                    + CASE EXTRACT(ISODOW FROM v_check_in)::integer
                        WHEN 5 THEN 0.08 WHEN 6 THEN 0.15 WHEN 7 THEN 0.05 ELSE 0 END
                ), 2);
                v_total := v_nightly + v_hotel.cleaning_fee;

                INSERT INTO public.hotel_quotes (
                    query_id, hotel_key, name, url, property_type, address, areas,
                    latitude, longitude, distance_from_center_km, location_status,
                    check_in, check_out, nights, adults, children_ages, total_guests,
                    rooms_requested, currency, nightly_jpy, stay_total_jpy, rating,
                    review_count, amenities, room_offers, capacity_evidence,
                    guest_origin_evidence, tax_inclusion, scraped_at, collected_at,
                    query_destination, status, reasons, raw_data
                ) VALUES (
                    v_query_id, v_key, v_hotel.hotel_name, NULL, v_hotel.property_type,
                    'Osaka, Japan (synthetic)', ARRAY[]::text[],
                    NULL, NULL, NULL, 'unknown',
                    v_check_in, v_check_in + 1, 1, 2, ARRAY[5]::smallint[], 3,
                    1, 'JPY', v_nightly, v_total,
                    round(7.5 + (v_hotel.hotel_no % 19) * 0.1, 2),
                    100 + v_hotel.hotel_no * 23 + v_day,
                    '["Air conditioning", "Private bathroom", "Free WiFi"]'::jsonb,
                    jsonb_build_array(jsonb_build_object(
                        'roomType', 'Synthetic Family Room', 'bedType', '2 double beds',
                        'persons', 4, 'available', true,
                        'features', jsonb_build_array('Air conditioning', 'Private bathroom'),
                        'price', jsonb_build_object(
                            'amount', v_total, 'currency', 'JPY', 'perNight', v_nightly
                        )
                    )),
                    'available_room_capacity', 'unknown', 'included',
                    v_collected_at - INTERVAL '5 minutes', v_collected_at,
                    'Osaka, Japan', 'match', ARRAY[]::text[],
                    jsonb_build_object(
                        'synthetic', true, 'dataset', 'mock-30-osaka-hotels-v1',
                        'hotel_no', v_hotel.hotel_no, 'check_in_offset_days', v_offset,
                        'base_nightly_jpy', v_hotel.base_price,
                        'cleaning_fee_jpy', v_hotel.cleaning_fee,
                        'price_model', 'weekly_collection_cycle+lead_time_cycle+stay_weekend',
                        'note', 'Fabricated test data; not a real hotel offer'
                    )
                ) ON CONFLICT (query_id, hotel_key) DO UPDATE SET
                    name = EXCLUDED.name, property_type = EXCLUDED.property_type,
                    nightly_jpy = EXCLUDED.nightly_jpy, stay_total_jpy = EXCLUDED.stay_total_jpy,
                    rating = EXCLUDED.rating, review_count = EXCLUDED.review_count,
                    room_offers = EXCLUDED.room_offers, scraped_at = EXCLUDED.scraped_at,
                    collected_at = EXCLUDED.collected_at, raw_data = EXCLUDED.raw_data;
            END LOOP;
        END LOOP;
    END LOOP;

    SELECT count(*) INTO v_count
    FROM public.hotel_quotes AS h
    JOIN public.collection_queries AS q ON q.id = h.query_id
    JOIN public.collection_batches AS b ON b.id = q.batch_id
    WHERE b.actor = 'synthetic-30-osaka-hotels-v1';
    IF v_count <> 3630 THEN
        RAISE EXCEPTION 'Expected 3630 synthetic quotes, got %', v_count;
    END IF;
END;
$mock$;

-- 结果应为11行，每天30家酒店、330条报价；日期以日本时区展示。
SELECT (h.collected_at AT TIME ZONE 'Asia/Tokyo')::date AS collected_date,
       count(DISTINCT h.hotel_key) AS hotel_count, count(*) AS quote_count,
       min(h.check_in) AS first_check_in, max(h.check_in) AS last_check_in,
       min(h.nightly_jpy) AS min_nightly_jpy, max(h.nightly_jpy) AS max_nightly_jpy
FROM public.hotel_quotes AS h
JOIN public.collection_queries AS q ON q.id = h.query_id
JOIN public.collection_batches AS b ON b.id = q.batch_id
WHERE b.actor = 'synthetic-30-osaka-hotels-v1'
GROUP BY 1 ORDER BY 1;
COMMIT;
