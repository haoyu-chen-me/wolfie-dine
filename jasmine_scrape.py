# jasmine_scrape.py
import json
import datetime
import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (SBU Student Project)"}

API_TEMPLATE = (
    "https://stonybrook.api.nutrislice.com/menu/api/weeks/school/jasmine/menu-type/"
    "{slug}/{year}/{month}/{day}/?format=json"
)

# 固定日（给“不变”的档口用）
FIXED_DATE = datetime.date(2026, 1, 26)

# Jasmine（整体）营业时间
JASMINE_HOURS = {
    "mon_thu": "11am to 8pm",
    "fri": "11am to 8pm",
    "sat": "12pm to 7pm",
    "sun": "12pm to 7pm",
}

# Curry Kitchen：仅周一到周五开放
CURRY_HOURS = {
    "mon_thu": "11am to 8pm",
    "fri": "11am to 8pm",
    "sat": "Closed",
    "sun": "Closed",
}

# 你现在给的 4 个档口（如果有第 5 个，照这个格式再加一行）
STALLS = [
    {"name": "Cafetasia Chinese", "slug": "cafetasia-chinese", "daily": False},
    {"name": "Curry Kitchen", "slug": "curry-kitchen", "daily": True},  # daily
    {"name": "Cafetasia Korean", "slug": "cafetasia-korean", "daily": False},
    {"name": "Sushido", "slug": "sushido", "daily": False},
]


def eastern_now() -> datetime.datetime:
    # 简单按东部时间 UTC-5（和你之前 East/West 保持一致）
    return datetime.datetime.utcnow() - datetime.timedelta(hours=5)


def eastern_today_date() -> datetime.date:
    return eastern_now().date()


def weekday_key(d: datetime.date) -> str:
    wd = d.weekday()  # Mon=0 ... Sun=6
    if wd <= 3:
        return "mon_thu"
    if wd == 4:
        return "fri"
    if wd == 5:
        return "sat"
    return "sun"


def safe_food_name(mi: dict) -> str | None:
    food = mi.get("food") or {}
    name = food.get("name")
    if isinstance(name, str) and name.strip():
        return name.strip()
    return None


def detect_header_text(mi: dict) -> str | None:
    if mi.get("food"):
        return None
    for k in ("name", "text", "label", "description", "menu_item_name"):
        v = mi.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    title = (mi.get("category") or {}).get("name")
    if isinstance(title, str) and title.strip():
        return title.strip()
    return None


def pick_section_name(menu_item: dict, current_section: str | None) -> str:
    mc = menu_item.get("menu_category") or {}
    cat = menu_item.get("category") or {}
    sec = (
        mc.get("name")
        or cat.get("name")
        or menu_item.get("category_name")
        or menu_item.get("station")
        or "Other"
    )
    if sec == "Other" and current_section:
        sec = current_section
    return sec


def dedupe_preserve_order(items: list[str]) -> list[str]:
    seen = set()
    out = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def fetch_flat_items(slug: str, date_obj: datetime.date) -> list[str]:
    url = API_TEMPLATE.format(
        slug=slug,
        year=date_obj.year,
        month=f"{date_obj.month:02d}",
        day=f"{date_obj.day:02d}",
    )

    r = requests.get(url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    data = r.json()

    date_str = date_obj.strftime("%Y-%m-%d")
    day_block = None
    for d in data.get("days", []):
        if d.get("date") == date_str:
            day_block = d
            break

    if not day_block:
        return []

    menu_items = day_block.get("menu_items") or []
    if not menu_items:
        return []

    section_map: dict[str, list[str]] = {}
    current_section = None

    for mi in menu_items:
        header = detect_header_text(mi)
        if header:
            current_section = header
            continue

        name = safe_food_name(mi)
        if not name:
            continue

        sec = pick_section_name(mi, current_section)
        section_map.setdefault(sec, []).append(name)

    flat = []
    for sec in section_map:
        flat.extend(section_map[sec])

    return dedupe_preserve_order(flat)


def stall_hours_today(stall_name: str, today_key: str) -> str:
    if stall_name.strip().lower() == "curry kitchen":
        return CURRY_HOURS[today_key]
    return JASMINE_HOURS[today_key]


def main():
    now_eastern = eastern_now()
    today = now_eastern.date()
    today_key = weekday_key(today)

    out = {
        "date": today.strftime("%Y-%m-%d"),
        "location": "Jasmine",
        "hours_today": JASMINE_HOURS[today_key],
        "updated_at": now_eastern.strftime("%Y-%m-%d %H:%M:%S EST"),
        "timezone": "America/New_York",
        "sections": [],
    }

    for s in STALLS:
        name = s["name"]
        slug = s["slug"]
        is_daily = bool(s.get("daily"))

        # daily 用今天；static 用固定日
        fetch_date = today if is_daily else FIXED_DATE

        # 默认按表给 hours
        h = stall_hours_today(name, today_key)

        # Curry Kitchen 周末直接 Closed，不抓
        if name.strip().lower() == "curry kitchen" and h == "Closed":
            items = []
        else:
            try:
                items = fetch_flat_items(slug, fetch_date)
            except Exception:
                items = []

        # ✅ 新规则：如果什么都没抓到 -> 直接 Closed
        if not items:
            h = "Closed"

        out["sections"].append(
            {
                "section": name,
                "hours_today": h,
                "items": items,
                "menu_url": f"https://stonybrook.nutrislice.com/menu/jasmine/{slug}/{fetch_date.strftime('%Y-%m-%d')}",
            }
        )

    with open("jasmine.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print("Successfully wrote jasmine.json")


if __name__ == "__main__":
    main()
