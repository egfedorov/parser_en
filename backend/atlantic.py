import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone

def parse_date(date_str: str) -> datetime:
    # Пример: '2025-07-22T13:30:00Z'
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except Exception:
        return datetime.now(timezone.utc)

def generate():
    url = 'https://www.theatlantic.com/category/features/'
    response = requests.get(url)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')

    fg = FeedGenerator()
    fg.title('The Atlantic — Features')
    fg.link(href=url, rel='alternate')
    fg.description('Latest features from The Atlantic')
    fg.language('en')

    articles = soup.select('article.CollectionArticleCard_root__8scmn')
    for art in articles:
        # Заголовок
        title_tag = art.select_one('h3.CollectionArticleCard_hed__mPXAv a')
        title = title_tag.get_text(strip=True) if title_tag else None
        link = title_tag['href'] if title_tag and title_tag.has_attr('href') else None

        # Описание
        desc_tag = art.select_one('p.CollectionArticleCard_dek__cgKmj')
        description = desc_tag.get_text(strip=True) if desc_tag else ''

        # Дата публикации (datetime в атрибуте)
        time_tag = art.select_one('time.CollectionArticleCard_datePublished__eg6_v')
        pub_date_str = time_tag['datetime'] if time_tag and time_tag.has_attr('datetime') else None
        pub_date = parse_date(pub_date_str) if pub_date_str else datetime.now(timezone.utc)

        if not (title and link):
            continue

        fe = fg.add_entry()
        fe.title(title)
        fe.link(href=link)
        fe.description(description)
        fe.pubDate(pub_date)

    fg.rss_file('atlantic.xml', encoding='utf-8')

if __name__ == '__main__':
    generate()
