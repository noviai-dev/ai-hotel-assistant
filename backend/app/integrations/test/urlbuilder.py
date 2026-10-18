

from urllib.parse import urlencode


BASE_URL = "https://www.booking.com/searchresults.html"


def build_nflt(filters: dict) -> str:
    """将筛选项拼成 Booking 的 nflt 参数格式。

    示例:
        {
            "price": "JPY-16000-25000-1",
            "ht_id": [204, 201],
            "review_score": 80,
            "family_friendly_property": 1,
        }
        -> "price=JPY-16000-25000-1;ht_id=204;ht_id=201;review_score=80;family_friendly_property=1"
    """
    items = []
    for key, value in filters.items():
        if isinstance(value, (list, tuple, set)):
            for item in value:
                items.append(f"{key}={item}")
        else:
            items.append(f"{key}={value}")
    return ";".join(items)


def build_booking_search_url(
    *,
    ss: str = "",
    lang: str = "zh-cn",
    checkin: str = "",
    checkout: str = "",
    group_adults: int = 2,
    no_rooms: int = 1,
    group_children: int = 0,
    age: int | list[int] | None = None,
    dest_id: str | int | None = None,
    dest_type: str = "hotel",
    src: str = "searchresults",
    aid: int | str | None = None,
    label: str | None = None,
    filters: dict | None = None,
    extra: dict | None = None,
) -> str:
    """按 Booking 的 URL 规则组装搜索链接。"""
    params = {
        "ss": ss,
        "lang": lang,
        "src": src,
        "dest_type": dest_type,
        "checkin": checkin,
        "checkout": checkout,
        "group_adults": group_adults,
        "no_rooms": no_rooms,
        "group_children": group_children,
    }

    if dest_id is not None:
        params["dest_id"] = dest_id

    if aid is not None:
        params["aid"] = aid

    if label is not None:
        params["label"] = label

    if age is not None:
        if isinstance(age, list):
            params["age"] = age
        else:
            params["age"] = age

    if filters:
        params["nflt"] = build_nflt(filters)

    if extra:
        params.update(extra)

    query_string = urlencode(params, doseq=True)
    return f"{BASE_URL}?{query_string}"


if __name__ == "__main__":
    url = build_booking_search_url(
        ss="住一心斎橋店，大阪，大阪府，日本",
        lang="zh-cn",
        checkin="2026-12-18",
        checkout="2026-12-20",
        group_adults=4,
        no_rooms=1,
        group_children=1,
        age=4,
        dest_id=10474892,
        dest_type="hotel",
        aid=2311236,
        label="ja-jp-booking-desktop-RPIhzHD7r*Rvjtq9UC4zEwS655523704762%3Apl%3Ata%3Ap1%3Ap2%3Aac%3Aap%3Aneg%3Afi%3Atikwd-51481728%3Alp9198406%3Ali%3Adec%3Adm",
        filters={
            "price": "JPY-16000-25000-1",
            "ht_id": [204, 201],
            "review_score": 80,
            "family_friendly_property": 1,
            "entire_place_bedroom_count": 1,
            "min_bathrooms": 1,
            "di": [7324, 7322, 7088, 7319, 2076, 2883, 2829],
        },
        extra={
            "ssne": "大阪",
            "ssne_untouched": "大阪",
            "efdco": 1,
            "ac_position": 0,
            "ac_click_type": "b",
            "ac_langcode": "zh",
            "ac_suggestion_list_length": 5,
            "search_selected": "true",
            "search_pageview_id": "89ab1a0307be02e7",
            "flex_window": 1,
        },
    )
    print(url)