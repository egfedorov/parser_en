#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gallup content.rss → gallup.xml
Простая репликация или фильтр официального фида Gallup.
Создаёт RSS-файл в корневой папке репозитория.
"""

import os
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
import feedparser
from feedgen.feed import FeedGenerator
from dateutil import parser as dtparse

SRC_URL = "https://news.gallup.com/sitemaps/content.rss"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari"


def fetch_rss(url: str):
    """Скачивает и парсит RSS."""
    r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
    r.raise_for_status()
    feed = feedparser.parse(r.content)
    return feed


def to_datetime(value):
    """Преобразует любую дату в UTC datetime."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if hasattr(value, "tm_year"):  # struct_time
        return datetime(*value[:6], tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            dt = dtparse.parse(value)
            return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return datetime.now(timezone.utc)
    return datetime.now(timezone.utc)


def build_feed(src_feed, out_path):
    """Создаёт новую RSS-ленту на основе Gallup."""
    fg = FeedGenerator()
    fg.id(SRC_URL)
    fg.title("Gallup — Latest News (republished)")
    fg.link(href="https://news.gallup.com", rel="alternate")
    fg.link(href=SRC_URL, rel="self")
    fg.description("Automated mirror of Gallup News RSS feed")
    fg.language("en")

    items = []
    for e in src_feed.entries:
        title = e.get("title", "").strip()
        link = e.get("link", "").strip()
        desc = e.get("summary", e.get("description", "")).strip()
        date_raw = (
            e.get("published_parsed")
            or e.get("updated_parsed")
            or e.get("published")
            or e.get("updated")
        )
        pub = to_datetime(date_raw)
        items.append({"title": title, "link": link, "desc": desc, "pub": pub})

    # Сортируем по дате убывания
    items.sort(key=lambda x: x["pub"], reverse=True)

    for it in items:
        fe = fg.add_entry()
        fe.id(it["link"])
        fe.title(it["title"])
        fe.link(href=it["link"])
        if it["desc"]:
            fe.description(it["desc"])
        fe.pubDate(it["pub"])

    fg.rss_file(out_path, encoding="utf-8")
    print(f"✅ RSS saved: {out_path} ({len(items)} items)")


def main():
    print(f"Fetching {SRC_URL} …")
    feed = fetch_rss(SRC_URL)
    out_path = os.path.join(os.path.dirname(__file__), "..", "gallup.xml")
    build_feed(feed, out_path)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
