import re
import json
from bs4 import BeautifulSoup


def parse_html(html: str, page_url: str | None = None) -> dict:
    soup = BeautifulSoup(html, "lxml")

    title = soup.title.get_text(strip=True) if soup.title else ""

    def meta(name: str) -> str:
        tag = soup.find("meta", attrs={"name": name})
        return (tag.get("content") or "").strip() if tag else ""

    def meta_prop(prop: str) -> str:
        tag = soup.find("meta", attrs={"property": prop})
        return (tag.get("content") or "").strip() if tag else ""

    h1 = [h.get_text(" ", strip=True) for h in soup.find_all("h1")]
    h2 = [h.get_text(" ", strip=True) for h in soup.find_all("h2")]
    h3 = [h.get_text(" ", strip=True) for h in soup.find_all("h3")]

    clean = BeautifulSoup(str(soup), "lxml")
    for t in clean(["script", "style", "noscript"]):
        t.decompose()

    text = clean.get_text(" ", strip=True)
    word_count = len(re.findall(r"\b\w+\b", text))

    schema_types = []
    for s in soup.find_all("script", type="application/ld+json"):
        raw = (s.string or "").strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict) and "@type" in item:
                    t = item["@type"]
                    if isinstance(t, list):
                        schema_types.extend([str(x) for x in t if x])
                    else:
                        schema_types.append(str(t))
        except Exception:
            continue

    # unique
    schema_types = list(dict.fromkeys(schema_types))

    return {
        "title": title,
        "meta_description": meta("description"),
        "robots": meta("robots"),
        "viewport": meta("viewport"),
        "og_title": meta_prop("og:title"),
        "og_description": meta_prop("og:description"),
        "og_image": meta_prop("og:image"),
        "h1": h1,
        "h2": h2,
        "h3": h3,
        "word_count": word_count,
        "schema_types": schema_types,
        "raw_text": text,
    }
