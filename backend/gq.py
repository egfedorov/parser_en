import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
import re

def parse_date(date_str: str) -> datetime:
    """
    Преобразует дату вроде 'July 21, 2025' в datetime.
    """
    try:
        return datetime.strptime(date_str.strip(), "%B %d, %Y").replace(tzinfo=timezone.utc)
    except Exception:
        print(f"[WARN] Не удалось распарсить дату: '{date_str}'")
        return datetime.now(timezone.utc)

def generate():
    url = "https://www.gq.com/about/profiles"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    fg = FeedGenerator()
    fg.title("GQ — Profiles")
    fg.link(href=url, rel="alternate")
    fg.description("Fresh profiles from GQ")
    fg.language("en")

    # Каждый профиль — div c классом summary-list__item
    articles = soup.select("div.summary-list__item")

    for art in articles:
        # Заголовок
        title_tag = art.select_one("a.SummaryItemHedLink-cxRzVg")
        title = title_tag.get_text(strip=True) if title_tag else None

        # Ссылка
        link = title_tag["href"] if title_tag and title_tag.has_attr("href") else None
        if link and not link.startswith("http"):
            link = "https://www.gq.com" + link

        # Картинка
        img_tag = art.select_one("picture img")
        img_url = img_tag["src"] if img_tag and img_tag.has_attr("src") else None

        # Описание
        teaser_tag = art.select_one(".summary-item__dek")
        teaser = teaser_tag.get_text(strip=True) if teaser_tag else ""

        # Автор
        author_tag = art.select_one("span[data-testid='BylineName']")
        author = author_tag.get_text(strip=True) if author_tag else ""

        # Дата публикации
        date_tag = art.select_one("time.summary-item__publish-date")
        date_str = date_tag.get_text(strip=True) if date_tag else ""
        pub_date = parse_date(date_str) if date_str else datetime.now(timezone.utc)

        # Рубрика (категория)
        category_tag = art.select_one(".rubric__name")
        category = category_tag.get_text(strip=True) if category_tag else ""

        if not (title and link):
            continue

        fe = fg.add_entry()
        fe.title(title)
        fe.link(href=link)
        fe.pubDate(pub_date)
        fe.description(teaser)
        if author:
            fe.author({"name": author})
        if category:
            fe.category(term=category)
        if img_url:
            fe.enclosure(img_url, 0, "image/jpeg")

    fg.rss_file("gq.xml", encoding="utf-8")

if __name__ == "__main__":
    generate()
