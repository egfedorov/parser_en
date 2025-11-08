import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
from urllib.parse import urljoin
import time

def parse_date(date_str: str) -> datetime:
    """Парсит дату вида '20 октября 2025 г.' (русская локаль)"""
    months = {
        "января": 1, "февраля": 2, "марта": 3, "апреля": 4,
        "мая": 5, "июня": 6, "июля": 7, "августа": 8,
        "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
    }
    parts = date_str.replace("г.", "").split()
    try:
        day = int(parts[0])
        month = months[parts[1].lower()]
        year = int(parts[2])
        return datetime(year, month, day, tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)

def get_article_date(article_url: str) -> datetime:
    """Достает дату публикации со страницы статьи"""
    try:
        r = requests.get(article_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        r.raise_for_status()
        s = BeautifulSoup(r.text, "html.parser")
        date_tag = s.select_one("p.date")
        if date_tag:
            return parse_date(date_tag.get_text(strip=True))
    except Exception as e:
        print(f"⚠️  Failed to get date from {article_url}: {e}")
    return datetime.now(timezone.utc)

def generate():
    base_url = "https://macleans.ca"
    url = f"{base_url}/tag/big-stories/"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    articles = soup.select("div.__articles__Z0v1U article")

    fg = FeedGenerator()
    fg.id(url)
    fg.title("Maclean’s — Big Stories")
    fg.link(href=url, rel="alternate")
    fg.description("Latest longform and big stories from Maclean’s")
    fg.language("en")

    print(f"📰 Found {len(articles)} articles. Fetching details...")

    for art in articles[:15]:
        title_tag = art.select_one("h3 a")
        excerpt_tag = art.select_one("div.excerpt")
        img_tag = art.select_one("img")
        if not title_tag:
            continue

        title = title_tag.get_text(strip=True)
        link = urljoin(base_url, title_tag.get("href"))
        description = excerpt_tag.get_text(strip=True) if excerpt_tag else ""
        image_url = img_tag.get("src") if img_tag else ""

        pub_date = get_article_date(link)
        time.sleep(1)

        fe = fg.add_entry()
        fe.id(link)
        fe.title(title)
        fe.link(href=link)
        fe.description(description)
        if image_url:
            fe.enclosure(url=image_url, type="image/jpeg")
        fe.pubDate(pub_date)

        print(f"✓ Parsed: {title} — {pub_date.date()}")

    fg.rss_file("../macleans.xml", encoding="utf-8")
    print("✅ macleans1.xml generated successfully")

if __name__ == "__main__":
    generate()
