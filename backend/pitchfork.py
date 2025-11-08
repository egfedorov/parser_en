import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
from urllib.parse import urljoin

def parse_date(date_str: str) -> datetime:
    """Парсит дату из Pitchfork (формат: 2025-11-04T00:00:00)"""
    try:
        dt = datetime.fromisoformat(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
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

    for art in articles:
        title_tag = art.select_one("h3.SummaryItemHedBase-hnYOxl")
        link_tag = art.select_one("a.SummaryItemHedLink-cxRzVg")
        author_tag = art.select_one("span.BylineName-kqTBDS")
        date_tag = art.select_one("time.SummaryItemBylinePublishDate-czeIQl")
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

        date_str = date_tag.get("datetime") if date_tag and date_tag.has_attr("datetime") else None
        pub_date = parse_date(date_str) if date_str else datetime.now(timezone.utc)

        fe = fg.add_entry()
        fe.id(link)
        fe.title(f"[{rubric}] {title}" if rubric else title)
        fe.link(href=link)
        fe.description(f"{description}\n\nAuthor: {author}" if author else description)
        if image_url:
            fe.enclosure(url=image_url, type="image/jpeg")
        fe.pubDate(pub_date)

    # Сохраняем XML в корень репозитория
    fg.rss_file("../pitchfork.xml", encoding="utf-8")

if __name__ == "__main__":
    generate()
