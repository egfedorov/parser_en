import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone

def parse_wired_date(date_str):
    # Поддержка двух форматов: "07.23.2025 07:00 AM" и "Mar 25, 2025 6:00 AM"
    for fmt in ("%m.%d.%Y %I:%M %p", "%b %d, %Y %I:%M %p"):
        try:
            return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
        except Exception:
            continue
    print(f"[WARN] Не удалось распарсить дату: {date_str}")
    return None

def get_article_pubdate(article_url):
    try:
        resp = requests.get(article_url, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        # Первый вариант: <time data-testid="PublishedTimestamp">...</time>
        time_tag = soup.find("time", attrs={"data-testid": "PublishedTimestamp"})
        # Второй вариант: просто <time>
        if not time_tag:
            time_tag = soup.find("time")
        if time_tag and time_tag.text.strip():
            dt = parse_wired_date(time_tag.text.strip())
            if dt:
                return dt
    except Exception as ex:
        print(f"[WARN] Не удалось получить дату из {article_url}: {ex}")
    return None

def generate():
    url = "https://www.wired.com/category/big-story/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    fg = FeedGenerator()
    fg.title("WIRED — Big Story")
    fg.link(href=url, rel="alternate")
    fg.description("Big stories from WIRED magazine")
    fg.language("en")

    articles = soup.select("div.SummaryItemWrapper-ircKXK")

    for art in articles:
        a_tag = art.select_one("a.SummaryItemHedLink-cxRzVg")
        if not a_tag:
            continue
        title = a_tag.get_text(strip=True)
        link = a_tag["href"]
        if link and not link.startswith("http"):
            link = "https://www.wired.com" + link

        desc_tag = art.select_one("div.summary-item__dek")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        author_tag = art.select_one("span.BylineName-kqTBDS")
        author = author_tag.get_text(strip=True) if author_tag else ""

        img_tag = art.select_one("img.responsive-image__image")
        img_url = img_tag["src"] if img_tag and img_tag.has_attr("src") else None

        # Получаем pubDate со страницы самой статьи!
        pub_date = get_article_pubdate(link)
        if not pub_date:
            print(f"[WARN] Не удалось получить дату для {link}")
            continue

        fe = fg.add_entry()
        fe.title(title)
        fe.link(href=link)
        fe.description(description)
        if author:
            fe.author({"name": author})
        fe.pubDate(pub_date)
        if img_url:
            fe.enclosure(img_url, 0, "image/jpeg")

    fg.rss_file("wired.xml", encoding="utf-8")

if __name__ == "__main__":
    generate()
