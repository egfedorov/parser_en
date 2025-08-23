import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
import re

def parse_semafor_date_from_url(url: str) -> datetime:
    m = re.search(r'/(\d{2})/(\d{2})/(\d{4})/', url)
    if m:
        month, day, year = map(int, m.groups())
        return datetime(year, month, day, 12, 0, tzinfo=timezone.utc)
    return datetime.now(timezone.utc)

def generate():
    url = 'https://www.semafor.com/vertical/media'
    response = requests.get(url)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')

    fg = FeedGenerator()
    fg.title('Semafor — Media')
    fg.link(href=url, rel='alternate')
    fg.description('Latest media stories from Semafor')
    fg.language('en')

    seen_links = set()
    # Ищем все <a> со ссылкой на статью с датой
    article_links = soup.find_all('a', href=re.compile(r'/article/\d{2}/\d{2}/\d{4}/'))
    for link_tag in article_links:
        link = link_tag['href']
        if not link.startswith('http'):
            link = 'https://www.semafor.com' + link
        if link in seen_links:
            continue
        seen_links.add(link)

        # Заголовок ищем в <h2> или <h3> внутри этой же ссылки, либо берём текст самой ссылки
        title_tag = link_tag.find(['h2', 'h3'])
        title = title_tag.get_text(strip=True) if title_tag else link_tag.get_text(strip=True)
        if not title:
            continue

        # Описание — ищем соседний <div> с intro или description
        description = ''
        parent = link_tag.parent
        intro_div = parent.find('div', class_=re.compile(r'styles_intro__'))
        if not intro_div:
            # Иногда intro может быть глубже или у следующего родителя
            parent2 = parent.parent
            intro_div = parent2.find('div', class_=re.compile(r'styles_intro__')) if parent2 else None
        if intro_div:
            description = intro_div.get_text(strip=True)

        # Дата из url
        pub_date = parse_semafor_date_from_url(link)

        fe = fg.add_entry()
        fe.title(title)
        fe.link(href=link)
        fe.description(description)
        fe.pubDate(pub_date)

    fg.rss_file('semafor.xml', encoding='utf-8')

if __name__ == '__main__':
    generate()
