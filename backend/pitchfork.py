import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime
import re

def parse_date(date_str: str):
    """Парсит дату в формате 'November 6, 2025' → datetime."""
    try:
        return datetime.strptime(date_str.strip(), "%B %d, %Y")
    except Exception:
        return datetime.utcnow()

def generate():
    url = "https://pitchfork.com/features/"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=15)
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")

    fg = FeedGenerator()
    fg.title("Pitchfork — Features")
    fg.link(href=url, rel="alternate")
    fg.description("Latest longreads, interviews, and essays from Pitchfork.")
    fg.language("en")

    articles = soup.select("div.SummaryItemWrapper-ircKXK")
    for art in articles:
        # Заголовок и ссылка
        a_tag = art.select_one("a.SummaryItemHedLink-cxRzVg")
        title = a_tag.get_text(strip=True) if a_tag else None
        link = (
            "https://pitchfork.com" + a_tag["href"]
            if a_tag and a_tag.has_attr("href")
            else None
        )

        # Описание (если есть)
        desc_tag = art.select_one("div.SummaryItemDek-IjVzD")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        # Автор(ы)
        authors = [
            span.get_text(strip=True)
            for span in art.select("span.BylineName-kqTBDS")
            if span.get_text(strip=True)
        ]
        author_str = ", ".join(authors) if authors else "Pitchfork Staff"

        # Дата
        time_tag = art.select_one("time")
        date_str = time_tag.get_text(strip=True) if time_tag else ""
        pub_date = parse_date(date_str)

        if not (title and link):
            continue

        fe = fg.add_entry()
        fe.title(title)
        fe.link(href=link)
        fe.description(f"{description}\n\nBy {author_str}")
        fe.pubDate(pub_date)

    fg.rss_file("pitchfork.xml", encoding="utf-8")

if __name__ == "__main__":
    generate()
