from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
import re
import os

def parse_wp_date_from_url(url: str):
    m = re.search(r'/internet-culture/(\d{4})/(\d{2})/(\d{2})/', url)
    if m:
        year, month, day = map(int, m.groups())
        return datetime(year, month, day, 12, 0, tzinfo=timezone.utc)
    return datetime.now(timezone.utc)

def generate():
    url = "https://www.washingtonpost.com/internet-culture/"

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=60000, wait_until="domcontentloaded")
        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")

    fg = FeedGenerator()
    fg.title("Washington Post — Internet Culture")
    fg.link(href=url, rel="alternate")
    fg.description("Latest internet culture stories from Washington Post")
    fg.language("en")

    seen_links = set()

    for link_tag in soup.find_all("a", href=re.compile(r"/internet-culture/\d{4}/\d{2}/\d{2}/")):
        title = link_tag.get_text(strip=True)
        if not title:
            continue

        link = link_tag["href"]
        if not link.startswith("http"):
            link = "https://www.washingtonpost.com" + link

        if link in seen_links:
            continue
        seen_links.add(link)

        desc_tag = link_tag.find_parent().find_next_sibling("p")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        pub_date = parse_wp_date_from_url(link)

        fe = fg.add_entry()
        fe.title(title)
        fe.link(href=link)
        fe.description(description)
        fe.pubDate(pub_date)

    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    output_path = os.path.join(parent_dir, "wapo_internet.xml")
    fg.rss_file(output_path, encoding="utf-8")

    print(f"RSS создан: {output_path}")

if __name__ == "__main__":
    generate()
