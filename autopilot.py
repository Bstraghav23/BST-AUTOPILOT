"""BST Autopilot: watches your GameBoost listings and sends price-change
suggestions and sale alerts to Telegram. It only READS from GameBoost;
you make every price change yourself.

Secrets (GitHub > Settings > Secrets and variables > Actions):
  GAMEBOOST_API_KEY   from GameBoost dashboard > Settings > Developers
  TELEGRAM_BOT_TOKEN  from @BotFather
  TELEGRAM_CHAT_ID    your chat id (see README)
Without GAMEBOOST_API_KEY it runs on data/sample_offers.json (test mode).
"""
import csv
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://api.gameboost.com/v2"
IST = timezone(timedelta(hours=5, minutes=30))
NOW = datetime.now(timezone.utc)
CFG = json.load(open("config.json", encoding="utf-8"))
STATE_PATH = "data/state.json"


# ---------- GameBoost ----------
def api_get(path, params):
    url = f"{API}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {os.environ['GAMEBOOST_API_KEY']}",
        "Accept": "application/json", "User-Agent": "bst-autopilot/1.0"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:  # rate limited: wait and retry
                time.sleep(10 * (attempt + 1))
                continue
            raise SystemExit(f"GameBoost API error {e.code} on {path}: {e.read()[:300]!r}")
    raise SystemExit(f"GameBoost API kept rate-limiting {path}")


def fetch_offers(path, kind):
    offers, page = [], 1
    while True:
        body = api_get(path, {"per_page": 50, "page": page})
        batch = body.get("data", body if isinstance(body, list) else [])
        for o in batch:
            o["_kind"] = kind
        offers += batch
        meta = body.get("meta", {}) if isinstance(body, dict) else {}
        last = meta.get("last_page") or (meta.get("pagination") or {}).get("last_page")
        has_next = (body.get("links") or {}).get("next") if isinstance(body, dict) else None
        if not batch or (last and page >= last) or (not last and not has_next):
            return offers
        page += 1


def load_offers():
    if not os.environ.get("GAMEBOOST_API_KEY"):
        print("No GAMEBOOST_API_KEY: test mode with data/sample_offers.json")
        return json.load(open("data/sample_offers.json", encoding="utf-8"))
    offers = []
    for path, kind in CFG["watch"].items():
        offers += fetch_offers(path, kind)
    return offers


# ---------- helpers ----------
def num(v):
    if isinstance(v, dict):
        v = v.get("amount", v.get("value"))
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def when(v):
    if not v:
        return None
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except ValueError:
        return None


def round_price(p):
    """Snap down to a .49 / .99 price, never below 0.99."""
    whole = int(p)
    for c in (whole + 0.99, whole + 0.49, whole - 0.01):
        if c <= p + 1e-9:
            return max(round(c, 2), 0.99)
    return 0.99


def load_floors():
    floors = {}
    if os.path.exists("data/floors.csv"):
        for r in csv.DictReader(open("data/floors.csv", encoding="utf-8")):
            if r.get("floor_price"):
                floors[r["external_id_or_title"].strip().lower()] = float(r["floor_price"])
    return floors


# ---------- Telegram ----------
def telegram(text):
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("---- Telegram (not configured, printing) ----\n" + text)
        return
    for i in range(0, len(text), 3800):
        data = urllib.parse.urlencode({"chat_id": chat, "text": text[i:i + 3800],
                                       "disable_web_page_preview": "true"}).encode()
        urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", data, timeout=30)


# ---------- main ----------
def main():
    state = json.load(open(STATE_PATH)) if os.path.exists(STATE_PATH) else {"offers": {}, "sales": []}
    floors, rules = load_floors(), CFG["rules"]
    offers = load_offers()
    suggestions, new_sales, live = [], [], 0

    for o in offers:
        oid = f'{o["_kind"]}:{o.get("id")}'
        ext = str(o.get("external_id") or "")
        title = o.get("title") or o.get("name") or ext or oid
        price = num(o.get("price"))
        status = str(o.get("status", "")).lower()
        listed = when(o.get("listed_at") or o.get("created_at"))
        cur = str(o.get("currency") or (o.get("price") or {}).get("currency", "") if isinstance(o.get("price"), dict) else o.get("currency") or "").upper()
        c = {"EUR": "€", "USD": "$", "GBP": "£"}.get(cur, CFG.get("currency_symbol", "$"))
        s = state["offers"].setdefault(oid, {"first_price": price, "last_suggested": None})

        if status == "sold" and oid not in state["sales"]:
            state["sales"].append(oid)
            day = NOW.astimezone(IST).date().isoformat()
            state.setdefault("sales_by_day", {})[day] = state.get("sales_by_day", {}).get(day, 0) + 1
            new_sales.append(f"💰 SOLD: {title} — {c}{price:.2f}" if price else f"💰 SOLD: {title}")
            continue
        if status != "listed" or price is None or listed is None:
            continue
        live += 1
        if o["_kind"] not in rules["reprice_kinds"]:
            continue

        days_listed = (NOW - listed).days
        last = when(s["last_suggested"])
        if days_listed < rules["drop_after_days"]:
            continue
        if last and NOW - last < timedelta(days=rules["days_between_suggestions"]):
            continue

        floor = floors.get(ext.lower()) or floors.get(title.lower()) or \
            round((s["first_price"] or price) * rules["default_floor_percent"] / 100, 2)
        new_price = max(round_price(price * (1 - rules["drop_percent"] / 100)), floor)
        if new_price >= price:
            suggestions.append(f"⛔ {title}\n   {c}{price:.2f} is at its floor ({c}{floor:.2f}). "
                               f"Listed {days_listed} days: consider bulk sale.")
        else:
            views = o.get("views")
            suggestions.append(f"🔻 {title}\n   {c}{price:.2f} → {c}{new_price:.2f}   "
                               f"(listed {days_listed} days{f', {views} views' if views is not None else ''}, "
                               f"floor {c}{floor:.2f})")
        s["last_suggested"] = NOW.isoformat()

    msgs = []
    if new_sales:
        msgs.append("\n".join(new_sales))
    if suggestions:
        msgs.append("📋 Price changes to make on GameBoost:\n\n" + "\n\n".join(suggestions))

    today = NOW.astimezone(IST).date().isoformat()
    if NOW.astimezone(IST).hour >= CFG["daily_summary_hour_ist"] and state.get("summary_day") != today:
        state["summary_day"] = today
        by_day = state.get("sales_by_day", {})
        last7 = sum(v for d, v in by_day.items() if d > (NOW.astimezone(IST).date() - timedelta(days=7)).isoformat())
        msgs.append(f"📊 Daily summary {today}\nLive listings: {live}\nSales today: {by_day.get(today, 0)}"
                    f"\nSales last 7 days: {last7}\nTotal sales tracked: {len(state['sales'])}")

    if msgs:
        telegram("\n\n".join(msgs))
    else:
        print(f"Nothing to report. {live} live listings checked.")
    json.dump(state, open(STATE_PATH, "w"), indent=1)


if __name__ == "__main__":
    sys.exit(main())
