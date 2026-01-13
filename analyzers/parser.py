import re
import json
from typing import Optional, Dict, Any, List
from bs4 import BeautifulSoup


def parse_html(html: str, page_url: Optional[str] = None) -> dict:
    soup = BeautifulSoup(html or "", "lxml")

    title = soup.title.get_text(strip=True) if soup.title else ""

    def meta(name: str) -> str:
        tag = soup.find("meta", attrs={"name": name})
        return (tag.get("content") or "").strip() if tag else ""

    def meta_prop(prop: str) -> str:
        tag = soup.find("meta", attrs={"property": prop})
        return (tag.get("content") or "").strip() if tag else ""

    canonical = ""
    canon = soup.find("link", attrs={"rel": "canonical"})
    if canon and canon.get("href"):
        canonical = str(canon.get("href")).strip()

    h1 = [h.get_text(" ", strip=True) for h in soup.find_all("h1")]
    h2 = [h.get_text(" ", strip=True) for h in soup.find_all("h2")]
    h3 = [h.get_text(" ", strip=True) for h in soup.find_all("h3")]

    # Clean text
    clean = BeautifulSoup(str(soup), "lxml")
    for t in clean(["script", "style", "noscript"]):
        t.decompose()
    text = clean.get_text(" ", strip=True)
    word_count = len(re.findall(r"\b\w+\b", text))

    # Basic structure
    img_tags = soup.find_all("img")
    iframe_tags = soup.find_all("iframe")
    table_tags = soup.find_all("table")
    ul_tags = soup.find_all("ul")
    ol_tags = soup.find_all("ol")

    image_count = len(img_tags)
    iframe_count = len(iframe_tags)
    table_count = len(table_tags)
    list_count = len(ul_tags) + len(ol_tags)

    # Map detection (best-effort)
    map_iframes = 0
    for fr in iframe_tags:
        src = (fr.get("src") or "").lower()
        if any(k in src for k in ["google.com/maps", "mapbox", "openstreetmap", "arcgis", "/maps", "maps.google"]):
            map_iframes += 1

    has_map = map_iframes > 0 or (" map " in f" {text.lower()} " and "location" in text.lower())

    # FAQ signal (best-effort)
    headings_all = " ".join([*(h2 or []), *(h3 or [])]).lower()
    question_like = 0
    for hx in (h2 or []) + (h3 or []):
        hx_s = (hx or "").strip()
        if "?" in hx_s:
            question_like += 1
        elif re.match(r"^(what|why|how|where|when|is|are|can|does|do)\b", hx_s.strip().lower()):
            question_like += 1
    has_faq_signal = ("faq" in headings_all or "frequently asked" in headings_all or question_like >= 4)

    # Schema types
    schema_types: List[str] = []
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
        "page_url": (page_url or "").strip(),
        "canonical": canonical,
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
        # for compliance/media modules
        "image_count": image_count,
        "iframe_count": iframe_count,
        "table_count": table_count,
        "list_count": list_count,
        "has_map": has_map,
        "map_iframes": map_iframes,
        "has_faq_signal": has_faq_signal,
        "question_like_count": question_like,
    }
