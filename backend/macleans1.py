import argparse
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
import json
import logging
import mimetypes

import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari"
BASE = "https://macleans.ca"

# ---------- logging ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s"
)
log = logging.getLogger("macleans")

# ---------- date parsers ----------
RU_MONTHS = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4,
    "мая": 5, "июня": 6, "июля": 7, "августа": 8,
    "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
}

def parse_date_ru(txt: str) -> datetime | None:
    # "20 октября 2025 г." или "20 октября 2025"
    t = txt.strip().lower().replace("г.", "").replace("г", "")
    parts = t.split()
    if len(parts) >= 3:
        try:
            day = int(parts[0])
            month = RU_MONTHS[parts[1]]
            year = int(parts[2])
            return datetime(year, month, day, tzinfo=timezone.utc)
        except Exception:
            return None
    return None

def parse_date_en(txt: str) -> datetime | None:
    # "October 20, 2025"
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            dt = datetime.strptime(txt.strip(), fmt)
            return dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue
    return None

def parse_date_iso(txt: str) -> datetime | None:
    # "2025-11-06T11:58:56-05:00" -> convert to UTC
    try:
        # fromisoformat handles offsets like -05:00
        dt = datetime.fromisoformat(txt.strip())
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None

def smart_parse_date(txt: str) -> datetime | None:
    return parse_date_iso(txt) or parse_date_ru(txt) or parse_date_en(txt)

# ---------- network ----------
def get(url: str, *, timeout=15) -> requests.Response:
    r = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
    r.raise_for_status()
    return r

# ---------- extraction ----------
def extract_date_from_article(html: str) -> datetime | None:
    s = BeautifulSoup(html, "html.parser")

    # 1) Явная разметка на странице — p.date
    tag = s.select_one("p.date")
    if tag and tag.get_text(strip=True):
        dt = smart_parse_date(tag.get_text(strip=True))
        if dt:
            return dt

    # 2) Точный published time в head
    for sel in [
        'meta[property="article:published_time"]',
        'meta[name="article:published_time"]',
        'meta[property="og:published_time"]',
        'meta[name="og:published_time"]',
        'meta[name="pubdate"]',
        'meta[itemprop="datePublished"]',
    ]:
        m = s.select_one(sel)
        if m and m.has_attr("content"):
            dt = smart_parse_date(m["content"])
            if dt:
                return dt

    # 3) JSON-LD
    for script in s.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            # Может быть объектом или списком
            candidates = data if isinstance(data, list) else [data]
            for obj in candidates:
                if isinstance(obj, dict):
                    for key in ("datePublished", "dateCreated", "uploadDate"):
                        if key in obj and obj[key]:
                            dt = smart_parse_date(str(obj[key]))
                            if dt:
                                return dt
        except Exception:
            continue

    # 4) time[datetime]
    t = s.select_one("time[datetime]")
    if t and t.has_attr("datetime"):
        dt = smart_parse_date(t["datetime"])
        if dt:
            return dt

    return None

def guess_mime(url: str) -> str | None:
    path = urlparse(url).path
    ext = path.split(".")[-1].lower() if "." in path else ""
    if ext:
        mt, _ = mimetypes.guess_type("x."+ext)
        return mt
    return None

def fetch_articles(list_url: str, max_items: int, delay: float) -> list[dict]:
    r = get(list_url)
    soup = BeautifulSoup(r.text, "html.parser")
    cards = soup.select("div.__articles__Z0v1U article")
    items = []

    log.info(f"Найдено карточек: {len(cards)}")

    for art in cards[:max_items]:
        a = art.select_one("h3 a")
        if not a:
            continue
        title = a.get_text(strip=True)
        link = urljoin(BASE, a.get("href", ""))

        excerpt = ""
        ex = art.select_one("div.excerpt")
        if ex:
            excerpt = ex.get_text(strip=True)

        img = None
        img_tag = art.select_one("img")
        if img_tag and img_tag.get("src"):
            img = urljoin(BASE, img_tag["src"])

        # подтягиваем дату из самой статьи
        try:
            ar = get(link)
            dt = extract_date_from_article(ar.text)
        except Exception as e:
            log.warning(f"Дата не извлечена ({link}): {e}")
            dt = None

        # fallback — сейчас UTC now (лучше, чем «just now» везде одинаково)
        pub = dt or datetime.now(timezone.utc)

        items.append({
            "title": title,
            "link": link,
            "summary": excerpt,
            "image": img,
            "published": pub,
        })

        log.info(f"✓ {title} — {pub.isoformat()}")
        time.sleep(delay)

    return items

def build_feed(items: list[dict], feed_link: str) -> FeedGenerator:
    fg = FeedGenerator()
    fg.id(feed_link)
    fg.title("Maclean’s — Big Stories")
    fg.link(href=feed_link, rel="alternate")
    fg.description("Latest longform and big stories from Maclean’s")
    fg.language("en")

    # сортируем по дате убыв.
    items_sorted = sorted(items, key=lambda x: x["published"], reverse=True)

    for it in items_sorted:
        fe = fg.add_entry()
        fe.id(it["link"])
        fe.title(it["title"])
        fe.link(href=it["link"])
        if it["summary"]:
            fe.description(it["summary"])
        # enclosure по возможности с корректным MIME
        if it.get("image"):
            mt = guess_mime(it["image"]) or "image/jpeg"
            fe.enclosure(url=it["image"], type=mt)
        fe.pubDate(it["published"])

    return fg

def main():
    ap = argparse.ArgumentParser(description="Maclean's Big Stories RSS generator")
    ap.add_argument("--url", default=f"{BASE}/tag/big-stories/", help="Listing URL")
    ap.add_argument("--out", default="macleans.xml", help="Output RSS file path")
    ap.add_argument("--max", type=int, default=15, help="Max items")
    ap.add_argument("--delay", type=float, default=0.8, help="Delay between article requests (sec)")
    ap.add_argument("--debug", action="store_true", help="Verbose logging")
    args = ap.parse_args()

    if args.debug:
        log.setLevel(logging.DEBUG)

    try:
        items = fetch_articles(args.url, max_items=args.max, delay=args.delay)
        if not items:
            log.error("Не удалось получить ни одной статьи — проверь разметку и селекторы.")
            sys.exit(2)

        fg = build_feed(items, feed_link=args.url)
        fg.rss_file(args.out, encoding="utf-8")
        log.info(f"✅ RSS сохранён: {args.out} (элементов: {len(items)})")
    except requests.HTTPError as e:
        log.error(f"HTTPError: {e}")
        sys.exit(1)
    except Exception as e:
        log.exception(f"Непредвиденная ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
