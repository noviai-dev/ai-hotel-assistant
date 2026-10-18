"""Osaka competitor collection via Apify; preview by default, --execute to run."""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import itertools
import json
import math
import os
from pathlib import Path
import sys
import time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ACTOR = "solidcode~booking-scraper"
HOTSPOTS = {
    "天王寺": ["tennoji", "tennōji", "天王寺"],
    "心斋桥": ["shinsaibashi", "心斎橋", "心斋桥"],
    "中央区": ["chuo-ku", "chūō", "chuo ward", "中央区"],
    "梅田": ["umeda", "梅田"],
    "难波": ["namba", "nanba", "難波", "难波"],
    "道顿堀": ["dotonbori", "dōtonbori", "道頓堀", "道顿堀"],
}


def tokyo_today():
    try:
        return datetime.now(ZoneInfo("Asia/Tokyo")).date()
    except ZoneInfoNotFoundError:
        return datetime.now(timezone(timedelta(hours=9))).date()


def build_plan(config):
    today = tokyo_today()
    check_in = date.fromisoformat(config["check_in"]) if config.get("check_in") else today + timedelta(days=40)
    if check_in < today:
        raise ValueError("入住日期已过期，请修改 check_in 或设为 null 自动使用当前日本日期的40天后")
    ages = config["children_ages"]
    if any(type(age) is not int or not 0 <= age <= 17 for age in ages):
        raise ValueError("儿童年龄必须为0–17的整数")
    if config["rooms"] != 1:
        raise ValueError("当前每间每晚价格比较仅支持 rooms=1")
    if not 0 < config["price_min_jpy"] <= config["price_max_jpy"]:
        raise ValueError("价格区间无效")
    if not 1 <= config["max_results"] <= 1000 or config["max_charge_usd_per_run"] <= 0:
        raise ValueError("结果上限或费用上限无效")
    if not 1 <= config["actor_timeout_seconds"] <= 3600 or config["radius_km"] <= 0:
        raise ValueError("超时时间或半径无效")
    center = config.get("center")
    if center is not None and (len(center) != 2 or not -90 <= center[0] <= 90 or not -180 <= center[1] <= 180):
        raise ValueError("center 必须为 [纬度, 经度]")
    days = config.get("calendar_days", 1)
    if type(days) is not int or not 1 <= days <= 366:
        raise ValueError("calendar_days必须是1–366的整数")
    hotel_urls = config.get("hotel_urls", [])
    from urllib.parse import urlsplit
    for url in hotel_urls:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname not in {"www.booking.com", "booking.com"} or not parsed.path.startswith('/hotel/') or parsed.query or parsed.fragment:
            raise ValueError("hotel_urls需要无日期参数的Booking酒店https链接")
    destinations = [None] if hotel_urls else config["destinations"]
    plan = []
    for day_offset, destination, nights, total, children in itertools.product(
        range(days), destinations, config["nights"], config["total_guests"], config["children_counts"]
    ):
        if nights not in (1, 3, 4, 5) or total not in (3, 4, 5, 6) or children not in (1, 2):
            raise ValueError("支持单晚日历或3–5晚套餐、总人数3–6人、1–2儿童")
        if len(ages) < children:
            raise ValueError("请为每名儿童填写年龄")
        stay_date = check_in + timedelta(days=day_offset)
        query = {
            "search": destination or "tracked_hotels", "checkIn": stay_date.isoformat(),
            "checkOut": (stay_date + timedelta(days=nights)).isoformat(),
            "adults": total - children, "children": children,
            "childrenAges": ages[:children], "rooms": 1,
            "propertyType": ["hotels", "apartments"],
            "currency": "JPY", "language": "en-gb", "maxResults": config["max_results"],
            "includeRoomDetails": True,
        }
        if hotel_urls:
            query["startUrls"] = hotel_urls
        if config.get("filter_search_price", False):
            query.update(priceMin=config["price_min_jpy"], priceMax=config["price_max_jpy"])
        plan.append(query)
    if not plan:
        raise ValueError("搜索组合不能为空")
    return plan


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) and not isinstance(value, bool) else None
    except (TypeError, ValueError):
        return None


def distance_km(lat, lng, center):
    a, b = math.radians(lat), math.radians(center[0])
    h = math.sin((a-b)/2)**2 + math.cos(a)*math.cos(b)*math.sin(math.radians(lng-center[1])/2)**2
    return 6371.0088 * 2 * math.asin(math.sqrt(min(1, h)))


def normalize(item, query, config):
    nights = (date.fromisoformat(query["checkOut"]) - date.fromisoformat(query["checkIn"])).days
    price = item.get("price") or {}
    nightly = number(price.get("perNight"))
    total = number(price.get("amount"))
    if nightly is None and total is not None:
        nightly = total / nights
    address = item.get("address") or {}
    address_text = " ".join(str(v) for v in address.values()) if isinstance(address, dict) else str(address)
    # Names may mention a distant landmark. Use address evidence only for area matching.
    areas = [name for name, aliases in HOTSPOTS.items() if any(a in address_text.casefold() for a in aliases)]
    location = item.get("location") or {}
    lat, lng = number(location.get("lat")), number(location.get("lng"))
    distance = None
    if config.get("center") is not None and lat is not None and lng is not None and -90 <= lat <= 90 and -180 <= lng <= 180:
        distance = distance_km(lat, lng, config["center"])
    geo_ok = bool(areas) or (distance is not None and distance <= config["radius_km"])
    geo_status = "match" if geo_ok else ("outside" if distance is not None else "unknown")
    reasons = []
    if price.get("currency") != "JPY" or nightly is None or nightly <= 0:
        reasons.append("price_unknown_or_non_jpy")
    elif not config["price_min_jpy"] <= nightly <= config["price_max_jpy"]:
        reasons.append("price_outside_range")
    kind = str(item.get("type") or "").casefold()
    if kind not in {"hotel", "apartment", "apartments", "aparthotel", "apartment hotel"}:
        reasons.append("type_unknown_or_excluded")
    if geo_status != "match":
        reasons.append("location_" + geo_status)
    if any(item.get(key) and item[key] != query[key] for key in ("checkIn", "checkOut")):
        reasons.append("dates_mismatch")
    if str(item.get("name", "")).casefold().strip() == config["own_hotel"].casefold().strip():
        reasons.append("own_hotel")
    rooms = item.get("rooms") or []
    capacity = query["adults"] + query["children"]
    eligible_rooms = [r for r in rooms if r.get("available") is True and (number(r.get("persons")) or 0) >= capacity]
    row = {
        "name": item.get("name"), "url": item.get("url"), "type": item.get("type"),
        "address": address_text, "areas": ",".join(areas), "latitude": lat, "longitude": lng,
        "distance_from_center_km": round(distance, 3) if distance is not None else None,
        "location_status": geo_status, "check_in": query["checkIn"], "check_out": query["checkOut"],
        "nights": nights, "adults": query["adults"], "children_ages": query["childrenAges"],
        "total_guests": capacity, "rooms_requested": 1,
        "nightly_jpy": round(nightly, 2) if nightly is not None and price.get("currency") == "JPY" else None,
        "stay_total_jpy": total if price.get("currency") == "JPY" else None,
        "rating": item.get("rating"), "review_count": item.get("reviewsCount"),
        "amenities": item.get("amenities", []), "room_offers": rooms,
        "capacity_evidence": "available_room_capacity" if eligible_rooms else "search_party_only_unverified",
        "guest_origin_evidence": "unknown", "tax_inclusion": "unknown",
        "scraped_at": item.get("scrapedAt"), "query_destination": query["search"],
        "status": "match" if not reasons else "review_or_excluded", "reasons": ",".join(reasons),
    }
    return row


def request(client, method, path, **kwargs):
    # Never retry POST: an ambiguous response could otherwise create duplicate paid runs.
    response = client.request(method, path, **kwargs)
    if response.is_error:
        raise RuntimeError(f"Apify HTTP {response.status_code}: {path}; 请检查额度、token及Actor输入")
    return response.json()


def collect(client, query, config, folder, on_run=None):
    run = request(client, "POST", f"/v2/acts/{ACTOR}/runs", json=query, params={
        "maxTotalChargeUsd": config["max_charge_usd_per_run"],
        "timeout": config["actor_timeout_seconds"],
    })["data"]
    run_id = run["id"]
    (folder / "run.json").write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")
    if on_run:
        on_run(run)
    print(f"Apify run: {run_id}", flush=True)
    deadline = time.monotonic() + config["actor_timeout_seconds"] + 120
    while run["status"] not in {"SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"}:
        if time.monotonic() > deadline:
            raise RuntimeError(f"本地等待超时，云端run可能仍在运行：{run_id}，请到Console检查")
        time.sleep(5)
        run = request(client, "GET", f"/v2/actor-runs/{run_id}")["data"]
    (folder / "run.json").write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")
    if on_run:
        on_run(run)
    if run["status"] != "SUCCEEDED":
        raise RuntimeError(f"Actor {run_id} 状态 {run['status']}，原始运行信息已保存")
    items = []
    while True:
        page = request(client, "GET", f"/v2/datasets/{run['defaultDatasetId']}/items", params={
            "format": "json", "clean": "true", "offset": len(items), "limit": 1000,
        })
        items.extend(page)
        if len(page) < 1000:
            break
    (folder / "raw.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    return items


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("competitors.example.json"))
    parser.add_argument("--execute", action="store_true", help="启动可能收费的真实Apify运行")
    parser.add_argument("--init-db", action="store_true", help="自动创建缺失数据库并初始化表结构，不调用Apify")
    parser.add_argument("--limit-runs", type=int, help="仅执行前N个组合，建议首次设为1")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "competitor_output")
    args = parser.parse_args()
    if args.init_db:
        from competitor_db import connect
        with connect(initialize=True):
            pass
        print("数据库及表结构已就绪")
        return 0
    config = json.loads(args.config.read_text(encoding="utf-8-sig"))
    plan = build_plan(config)
    if args.limit_runs is not None:
        if args.limit_runs < 1:
            raise ValueError("limit-runs必须大于0")
        plan = plan[:args.limit_runs]
    budget = len(plan) * config["max_charge_usd_per_run"]
    print(f"{len(plan)}个搜索组合；每个最多{config['max_results']}条；费用上限合计 US${budget:.2f}")
    if not args.execute:
        print(json.dumps({"actor": ACTOR, "queries": plan}, ensure_ascii=False, indent=2))
        return 0
    token = os.environ.get("APIFY_TOKEN")
    if not token:
        raise ValueError("请设置环境变量 APIFY_TOKEN；MCP登录不会自动给Python提供API token")
    import httpx
    output = args.output / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output.mkdir(parents=True)
    (output / "manifest.json").write_text(json.dumps({"config": config, "queries": plan, "actor": ACTOR}, ensure_ascii=False, indent=2), encoding="utf-8")
    from competitor_db import Database, connect
    with connect(initialize=True) as conn:
        db = Database(conn)
        # Initialize storage and persist the batch before starting any paid Actor.
        batch = db.start_batch(config, plan, ACTOR)
        print(f"数据库批次：{batch}")
        try:
            with httpx.Client(base_url="https://api.apify.com", headers={"Authorization": f"Bearer {token}"}, timeout=60) as client:
                for i, query in enumerate(plan):
                    query_id = db.start_query(batch, i+1, query)
                    folder = output / f"query_{i+1:03d}"
                    folder.mkdir()
                    items = collect(client, query, config, folder, on_run=lambda run: db.update_run(query_id, run))
                    db.save_quotes(query_id, [(normalize(item, query, config), item) for item in items])
            db.finish_batch(batch, "succeeded")
        except BaseException as exc:
            db.finish_batch(batch, "failed", type(exc).__name__)
            raise
    print(f"已写入PostgreSQL；原始JSON备份：{output}；空结果不代表售罄")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        raise SystemExit(1)
