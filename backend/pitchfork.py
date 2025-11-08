import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
from urllib.parse import urljoin

def parse_date(date_str: str) -> datetime:
    """Парсит строку вида 'November 6, 2025'"""
    try:
        dt = datetime.strptime(date_str.strip(), "%B %d, %Y")
        return dt.replace(tzinfo=timezone.utc)
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

        date_text = date_tag.get_text(strip=True) if date_tag else ""
        pub_date = parse_date(date_text) if date_text else datetime.now(timezone.utc)

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
