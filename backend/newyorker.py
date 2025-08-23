import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
import re

def parse_ny_date(date_str: str) -> datetime:
    """
    Пример: 'July 21, 2025'
    """
    try:
        return datetime.strptime(date_str.strip(), "%B %d, %Y").replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)

def generate():
    url = 'https://www.newyorker.com/magazine/reporting'
    response = requests.get(url)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')

    fg = FeedGenerator()
    fg.title('The New Yorker — Reporting')
    fg.link(href=url, rel='alternate')
    fg.description('Latest reporting from The New Yorker')
    fg.language('en')

    # Каждый материал — div с классом summary-list__item
    articles = soup.select('div.summary-list__item')
    for art in articles:
        # Заголовок
        title_tag = art.select_one('a.summary-item__hed-link h3')
        title = title_tag.get_text(strip=True) if title_tag else None
        # Ссылка (относительная)
        link_tag = art.select_one('a.summary-item__hed-link')
        link = link_tag['href'] if link_tag and link_tag.has_attr('href') else None
        if link and not link.startswith('http'):
            link = 'https://www.newyorker.com' + link

        # Описание
        desc_tag = art.select_one('div.summary-item__dek')
        description = desc_tag.get_text(strip=True) if desc_tag else ''

        # Дата публикации — это последний <time> внутри блока (она в текстовом формате)
        time_tag = art.select_one('time.summary-item__publish-date')
        pub_date_str = time_tag.get_text(strip=True) if time_tag else None
        pub_date = parse_ny_date(pub_date_str) if pub_date_str else datetime.now(timezone.utc)

        if not (title and link):
            continue

        fe = fg.add_entry()
        fe.title(title)
        fe.link(href=link)
        fe.description(description)
        fe.pubDate(pub_date)

    fg.rss_file('newyorker.xml', encoding='utf-8')

if __name__ == '__main__':
    generate()
