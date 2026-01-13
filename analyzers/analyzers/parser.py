import re
import json
from bs4 import BeautifulSoup


def parse_html(html: str) -> dict:
    """
    Parse HTML and extract content + structure for SEO & AI analysis
    """
    soup = BeautifulSoup(html, "lxml")

    # -------- Basic Meta --------
    title = soup.title.get_text(strip=True) if soup.title else ""

    def meta(name: str) -> str:
        tag = soup.find("meta", attrs={"name": name})
        return tag.get("content", "").strip() if tag else ""

    def meta_prop(prop: str) -> str:
        tag = soup.find("meta", attrs={"property": prop})
        return tag.get("content", "").strip() if tag else ""

    meta_description = meta("description")
    robots = meta("robots")
    viewport = meta("viewport")

    # -------- Headings --------
    h1 = [h.get_text(" ", strip=True) for h in soup.find_all("h1")]
    h2 = [h.get_text(" ", strip=True) for h in soup.find_all("h2")]
    h3 = [h.get_text(" ", strip=True) for h in soup.find_all("h3")]

    # -------- Clean text --------
    text_soup = BeautifulSoup(str(soup), "lxml")
    for tag in text_soup(["script", "style", "noscript"]):
        tag.decompose()

    text = text_soup.get_text(" ", strip=True)
    words = re.findall(r"\b\w+\b", text)
    word_count = len(words)

    # -------- JSON-LD Schema --------
    schema_types = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string
        if not raw:
            continue
        try:
            data = json.loads(raw)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict) and "@type" in item:
                    t = item["@type"]
                    if isinstance(t, list):
                        schema_types.extend(t)
                    else:
                        schema_types.append(t)
        except Exception:
            continue

    schema_types = list(dict.fromkeys(schema_types))  # unique

    return {
        "title": title,
        "meta_description": meta_description,
        "robots": robots,
        "viewport": viewport,
        "og_title": meta_prop("og:title"),
        "og_description": meta_prop("og:description"),
        "og_image": meta_prop("og:image"),
        "h1": h1,
        "h2": h2,
        "h3": h3,
        "word_count": word_count,
        "schema_types": schema_
