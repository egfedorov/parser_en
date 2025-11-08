import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
from urllib.parse import urljoin
import time

def parse_date(date_str: str) -> datetime:
    """Парсит ISO-даты с часовым поясом, возвращает UTC"""
    try:
        dt = datetime.fromisoformat(date_str)
        return dt.astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)

def get_article_date(article_url: str) -> datetime:
    """Переходит на страницу статьи и достает <time data-testid="ContentHeaderPublishDate">"""
    try:
        r = requests.get(article_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        r.raise_for_status()
        s = BeautifulSoup(r.text, "html.parser")
        time_tag = s.select_one('time[data-testid="ContentHeaderPublishDate"]')
        if time_tag and time_tag.has_attr("datetime"):
            return parse_date(time_tag["datetime"])
    except Exception as e:
        print(f"⚠️  Failed to get date from {article_url}: {e}")
    return datetime.now(timezone.utc)

def generate():
    base_url = "https://pitchfork.com"
    url = f"{base_url}/features/"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    articles = soup.select("div.SummaryItemWrapper-ircKXK")

    fg = FeedGenerator()
    fg.id(url)
    fg.title("Pitchfork — Features")
    fg.link(href=url, rel="alternate")
    fg.description("Latest feature stories from Pitchfork")
    fg.language("en")

    print(f"📰 Found {len(articles)} articles. Fetching dates...")

    for art in articles[:15]:  # ограничим до 15 записей
        title_tag = art.select_one("h3.SummaryItemHedBase-hnYOxl")
        link_tag = art.select_one("a.SummaryItemHedLink-cxRzVg")
        author_tag = art.select_one("span.BylineName-kqTBDS")
        desc_tag = art.select_one("div.SummaryItemDek-IjVzD")
        rubric_tag = art.select_one("span.RubricName-gkORYq")
        img_tag = art.select_one("img.ResponsiveImageContainer-eNxvmU")

        if not (title_tag and link_tag):
            continue

        title = title_tag.get_text(strip=True)
        link = urljoin(base_url, link_tag.get("href"))
        author = author_tag.get_text(strip=True) if author_tag else ""
        rubric = rubric_tag.get_text(strip=True) if rubric_tag else ""
        description = desc_tag.get_text(strip=True) if desc_tag else ""
        image_url = img_tag.get("src") if img_tag and img_tag.has_attr("src") else ""

        pub_date = get_article_date(link)
        time.sleep(1)  # чтобы не перегружать сервер

        fe = fg.add_entry()
        fe.id(link)
        fe.title(f"[{rubric}] {title}" if rubric else title)
        fe.link(href=link)
        fe.description(f"{description}\n\nAuthor: {author}" if author else description)
        if image_url:
            fe.enclosure(url=image_url, type="image/jpeg")
        fe.pubDate(pub_date)

        print(f"✓ Parsed: {title} — {pub_date.isoformat()}")

    fg.rss_file("../pitchfork.xml", encoding="utf-8")
    print("✅ pitchfork.xml generated successfully")

if __name__ == "__main__":
    generate()
