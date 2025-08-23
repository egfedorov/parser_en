import re, json, time, csv, datetime as dt
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup

BASE = "https://www.reuters.com"

# Основная лента и архивы по годам (при необходимости добавляй новые годы)
INDEX_URLS = [
    f"{BASE}/investigates/section/homepage/",
    f"{BASE}/investigates/section/reuters-investigates-2025/",
    f"{BASE}/investigates/section/reuters-investigates-2024/",
    f"{BASE}/investigates/section/reuters-investigates-2023/",
]

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

session = requests.Session()
session.headers.update({
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.reuters.com/",
    "Upgrade-Insecure-Requests": "1",
})

def get(url: str, tries: int = 3, sleep: float = 1.0) -> requests.Response:
    for i in range(tries):
        r = session.get(url, timeout=20)
        if r.status_code == 200:
            return r
        time.sleep(sleep * (i + 1))
    r.raise_for_status()
    return r  # for type checkers

def extract_article_links_from_index(html: str) -> List[str]:
    """
    Берём все <a>, чьи href ведут на /investigates/special-report/...,
    /investigates/article/... или /investigates/story/...
    (иногда структуры меняются — поэтому берём шире с фильтром).
    """
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("/"):
            full = BASE + href
        elif href.startswith("http"):
            full = href
        else:
            continue

        if re.search(r"/investigates/(special-report|article|story)/", full) or \
           re.search(r"/investigates/[^/]+/?$", full):
            # Отсечём «категории»/архивы и оставим материалы со slug'ами
            if any(seg.isdigit() for seg in full.split("-")[-2:]) or "/special-report/" in full:
                links.add(full)
            else:
                links.add(full)
    return sorted(links)

def pick_newsarticle_jsonld(soup: BeautifulSoup) -> Optional[Dict]:
    """
    Находим JSON-LD блок(и); возвращаем тот, где @type == NewsArticle.
    Иногда JSON-LD – массив; обрабатываем аккуратно.
    """
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or tag.get_text() or "{}")
        except json.JSONDecodeError:
            continue
        candidates = data if isinstance(data, list) else [data]
        for obj in candidates:
            t = obj.get("@type")
            if t == "NewsArticle" or (isinstance(t, list) and "NewsArticle" in t):
                return obj
    return None

def normalize_authors(js: Dict) -> List[str]:
    authors = []
    a = js.get("author")
    if isinstance(a, dict):
        n = a.get("name")
        if n: authors.append(n)
    elif isinstance(a, list):
        for item in a:
            if isinstance(item, dict):
                n = item.get("name")
                if n: authors.append(n)
            elif isinstance(item, str):
                authors.append(item)
    return authors

def extract_text_fallback(soup: BeautifulSoup) -> str:
    """
    Если articleBody в JSON-LD нет — берём абзацы из основного контента.
    """
    main = soup.find("main") or soup
    for sel in ["nav", "header", "footer", "aside"]:
        for tag in main.find_all(sel):
            tag.decompose()
    paras = []
    for p in main.find_all("p"):
        txt = p.get_text(" ", strip=True)
        if len(txt) >= 40 and not txt.lower().startswith(("reuters/", "reporting by")):
            paras.append(txt)
    return "\n\n".join(paras).strip()

def parse_article(url: str) -> Optional[Dict]:
    try:
        r = get(url)
    except Exception:
        return None
    soup = BeautifulSoup(r.text, "html.parser")

    js = pick_newsarticle_jsonld(soup) or {}
    headline = js.get("headline")
    date_published = js.get("datePublished")
    date_modified = js.get("dateModified")
    description = js.get("description")
    section = js.get("articleSection")
    image = None
    if isinstance(js.get("image"), dict):
        image = js["image"].get("url")
    elif isinstance(js.get("image"), str):
        image = js["image"]

    authors = normalize_authors(js)
    body = js.get("articleBody")
    if not body:
        body = extract_text_fallback(soup)

    if not headline:
        t = soup.find("title")
        headline = t.get_text(strip=True) if t else None
    if not headline:
        return None

    return {
        "url": url,
        "headline": headline,
        "description": description,
        "authors": authors,
        "section": section,
        "image": image,
        "date_published": date_published,
        "date_modified": date_modified,
        "body": body,
        "scraped_at": dt.datetime.utcnow().isoformat() + "Z",
    }

def crawl_investigations(limit: int = 30, sleep: float = 0.8) -> List[Dict]:
    """
    Обходим несколько индексов /investigates/section/...,
    собираем ссылки и парсим статьи.
    """
    links: List[str] = []
    for idx_url in INDEX_URLS:
        try:
            idx = get(idx_url)
            links.extend(extract_article_links_from_index(idx.text))
        except Exception:
            continue
    links = sorted(set(links))[:max(limit, 0)]

    items: List[Dict] = []
    for url in links:
        item = parse_article(url)
        if item:
            items.append(item)
        time.sleep(sleep)
    return items

def dump_json(items: List[Dict], path: str = "reuters_investigations.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    return path

def dump_csv(items: List[Dict], path: str = "reuters_investigations.csv"):
    fields = ["url","headline","description","authors","section","image",
              "date_published","date_modified","scraped_at","body"]
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for it in items:
            row = it.copy()
            row["authors"] = ", ".join(row.get("authors", []) or [])
            w.writerow(row)
    return path

# --- (опционально) RSS ---
def build_rss(items: List[Dict], path: str = "reuters.xml",
              feed_title="Reuters Investigations (unofficial)",
              feed_link=f"{BASE}/investigates/section/homepage/",
              feed_desc="Unofficial feed of Reuters Investigations scraped for personal use."):
    try:
        from feedgen.feed import FeedGenerator
    except ImportError:
        print("pip install feedgen для RSS")
        return None
    fg = FeedGenerator()
    fg.id(feed_link)
    fg.title(feed_title)
    fg.link(href=feed_link, rel="alternate")
    fg.language("en")
    fg.description(feed_desc)

    for it in items:
        fe = fg.add_entry()
        fe.id(it["url"])
        fe.title(it["headline"])
        fe.link(href=it["url"])
        if it.get("description"):
            fe.description(it["description"])
        try:
            dt_pub = dt.datetime.fromisoformat((it.get("date_published") or "").replace("Z",""))
            fe.pubDate(dt_pub)
        except Exception:
            pass
        fe.content(it.get("body") or "")
    fg.rss_str(pretty=True)
    fg.rss_file(path)
    return path

if __name__ == "__main__":
    items = crawl_investigations(limit=40, sleep=0.8)
    print(f"Collected {len(items)} items")
    dump_json(items)
    dump_csv(items)
    build_rss(items)
