import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
import re

# Словари для месяцев
MONTHS_RU = {
    'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4, 'мая': 5, 'июня': 6,
    'июля': 7, 'августа': 8, 'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12,
}
MONTHS_EN = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
}

def parse_date(date_str: str) -> datetime:
    """
    Поддержка форматов:
      - 'July 18, 2025'
      - 'Feb. 26, 2024'
      - '11 июля, 2025, 17:21' (оставлено на будущее)
    """
    date_str = date_str.strip()
    # Английский формат 'July 18, 2025' или 'Feb. 26, 2024'
    match = re.match(r'([A-Za-z]+)\.?\s+(\d{1,2}),\s+(\d{4})', date_str)
    if match:
        month_raw = match.group(1).lower()[:3]
        month = MONTHS_EN.get(month_raw)
        if month:
            day = int(match.group(2))
            year = int(match.group(3))
            return datetime(year, month, day, 12, 0, tzinfo=timezone.utc)
    # Русский формат (оставлен на случай других лент)
    match = re.match(
        r"(\d{1,2})\s+([а-яА-ЯёЁ]+)[,]?\s*(\d{4})[,]?\s*(\d{1,2})?:?(\d{2})?",
        date_str
    )
    if match:
        day = int(match.group(1))
        month = MONTHS_RU.get(match.group(2).lower())
        year = int(match.group(3))
        hour = int(match.group(4) or 12)
        minute = int(match.group(5) or 0)
        return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)
    print(f"[WARN] Не удалось распарсить дату: '{date_str}'")
    return datetime.now(timezone.utc)

def generate():
    url = 'https://www.vulture.com/tags/profile/'
    response = requests.get(url)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')

    fg = FeedGenerator()
    fg.title('Vulture — Profile')
    fg.link(href=url, rel='alternate')
    fg.description('Latest profiles from Vulture')
    fg.language('en')

    articles = soup.select('ol.paginated-feed-list-wrapper > li.article')

    for art in articles:
        # Title
        title_tag = art.select_one('.headline')
        title = title_tag.get_text(strip=True) if title_tag else None

        # Link
        link_tag = art.select_one('a.link-text')
        link = link_tag['href'] if link_tag and link_tag.has_attr('href') else None

        # Date
        date_tag = art.select_one('time.paginate-time')
        date_str = date_tag.get_text(strip=True) if date_tag else None
        pub_date = parse_date(date_str) if date_str else datetime.now(timezone.utc)

        # Description
        teaser_tag = art.select_one('.teaser')
        teaser = teaser_tag.get_text(strip=True) if teaser_tag else ''

        # Author
        author_tag = art.select_one('.main-author span:last-child')
        author = author_tag.get_text(strip=True) if author_tag else ''

        # Image
        img_tag = art.select_one('.article-img')
        img_url = img_tag['src'] if img_tag and img_tag.has_attr('src') else None

        # Категория (profile / encounter и т.п.)
        rubric_tag = art.select_one('.rubric')
        category = rubric_tag.get_text(strip=True) if rubric_tag else ''

        if not (title and link):
            continue

        fe = fg.add_entry()
        fe.title(title)
        fe.link(href=link)
        fe.pubDate(pub_date)
        if teaser:
            fe.description(teaser)
        if author:
            fe.author({'name': author})
        if img_url:
            fe.enclosure(img_url, 0, 'image/jpeg')
        if category:
            fe.category({'term': category})

    fg.rss_file('vulture.xml', encoding='utf-8')

if __name__ == '__main__':
    generate()
