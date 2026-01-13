import re
import json
from typing import Optional
from bs4 import BeautifulSoup


def parse_html(html: str, page_url: Optional[str] = None) -> dict:
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

    # Clean visible text
    clean = BeautifulSoup(str(soup), "lxml")
    for t in clean(["script", "style", "noscript"]):
        t.decompose()

    text = clean.get_text(" ", strip=True)
    word_count = len(re.findall(r"\b\w+\b", text))

    # Counts needed by compliance/media
    table_count = len(soup.find_all("table"))
    image_count = len(soup.find_all("img"))
    video_count = len(soup.find_all("video"))
    iframe_count = len(soup.find_all("iframe"))

    # Map signal (basic, works well)
    has_map_signal = False
    for iframe in soup.find_all("iframe"):
        src = (iframe.get("src") or "").lower()
        if "google.com/maps" in src or "maps.google" in src or "map" in src:
            has_map_signal = True
            break

    # FAQ signal (used by compliance analyzer)
    faq_signal = any(
        "faq" in (h or "").lower() or "frequently asked" in (h or "").lower()
        for h in (h2 + h3)
    )

    # Schema detection
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
        "has_faq_signal": faq_signal,
        "table_count": table_count,
        "image_count": image_count,
        "video_count": video_count,
        "iframe_count": iframe_count,
        "has_map_signal": has_map_signal,
        "raw_text": text,
    }
