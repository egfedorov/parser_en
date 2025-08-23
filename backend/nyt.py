import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
import re

def parse_nyt_date_from_url(url: str) -> datetime:
    m = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
    if m:
        year, month, day = map(int, m.groups())
        return datetime(year, month, day, 12, 0, tzinfo=timezone.utc)
    return datetime.now(timezone.utc)

def generate():
    url = 'https://www.nytimes.com/international/section/magazine'
    response = requests.get(url)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')

    fg = FeedGenerator()
    fg.title('NYT — Magazine')
    fg.link(href=url, rel='alternate')
    fg.description('Latest stories from NYT Magazine')
    fg.language('en')

    seen_links = set()
    # Парсим ВСЕ article с ссылками на /magazine/
    articles = soup.find_all('article')
    for art in articles:
        # Поиск <a> с magazine
        link_tag = art.find('a', href=re.compile(r'/\d{4}/\d{2}/\d{2}/magazine/'))
        if not link_tag:
            continue
        title = link_tag.get_text(strip=True)
        link = link_tag['href']
        if not link.startswith('http'):
            link = 'https://www.nytimes.com' + link
        # Не дублируем материалы
        if link in seen_links:
            continue
        seen_links.add(link)
        # Описание — первый <p> после заголовка
        desc_tag = link_tag.find_parent().find_next_sibling('p')
        if not desc_tag:
            # fallback: любой <p> в статье, кроме byline
            desc_tag = art.find('p', attrs={'class': re.compile('css-.*')})
        description = desc_tag.get_text(strip=True) if desc_tag else ''
        # Дата из url
        pub_date = parse_nyt_date_from_url(link)
        # Добавляем в rss
        fe = fg.add_entry()
        fe.title(title)
        fe.link(href=link)
        fe.description(description)
        fe.pubDate(pub_date)

    fg.rss_file('nyt_magazine.xml', encoding='utf-8')

if __name__ == '__main__':
    generate()
