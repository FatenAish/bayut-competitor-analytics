import re
import json
from urllib.parse import urlparse
from bs4 import BeautifulSoup


_STOP = {
    "the","and","for","with","that","this","from","you","your","are","was","were","will","have","has","had",
    "but","not","can","may","more","most","into","than","then","they","them","their","our","out","about",
    "also","over","under","between","within","near","where","when","what","why","how","who","which",
    "a","an","to","of","in","on","at","as","is","it","be","or","by"
}

_IGNORE_TAGS = {"nav", "footer", "header", "aside", "form", "noscript", "script", "style"}


def _clean_text(s: str) -> str:
    s = re.sub(r"\s+", " ", (s or "")).strip()
    return s


def _norm_heading(s: str) -> str:
    s = _clean_text(s).lower()
    s = re.sub(r"[\|\-\—\–•·•]+", " ", s)
    s = re.sub(r"[^a-z0-9\s\?\&\(\)\:\/]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _competitor_name_from_url(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        host = ""
    host = host.replace("www.", "")

    if "drivenproperties" in host:
        return "Driven Properties"
    if "dubizzle" in host:
        return "Dubizzle"
    if "emaar" in host:
        return "Emaar"
    if not host:
        return "Competitor"
    return host.split(":")[0]


def _get_main_container(soup: BeautifulSoup):
    main = soup.find("main")
    if main:
        return main
    article = soup.find("article")
    if article:
        return article
    body = soup.body
    return body if body else soup


from bs4.element import Tag  # add near the top if not already imported

def _strip_layout_noise(container):
    if not container:
        return

    # remove obvious non-content blocks
    kill_tags = {"header", "footer", "nav", "aside", "form"}
    for x in container.find_all(kill_tags):
        x.decompose()

    # remove nodes by class/id keywords (safe attrs handling)
    bad_words = (
        "cookie", "consent", "gdpr", "subscribe", "newsletter", "signup",
        "modal", "popup", "banner", "breadcrumbs", "breadcrumb",
        "share", "social", "comment", "comments", "related", "recommend",
        "sidebar", "sticky", "nav", "menu", "footer", "header", "promo", "ads", "advert"
    )

    for t in container.find_all(True):
        # ✅ only Tags have reliable attrs
        if not isinstance(t, Tag):
            continue

        attrs = t.attrs or {}  # ✅ fixes attrs=None
        cls = attrs.get("class") or []
        if isinstance(cls, str):
            cls = [cls]

        tid = attrs.get("id") or ""
        cid = (" ".join(cls) + " " + tid).lower()

        if any(w in cid for w in bad_words):
            t.decompose()


def _extract_schema_types(soup: BeautifulSoup):
    schema_types = []
    for s in soup.find_all("script", type="application/ld+json"):
        raw = (s.string or "").strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict):
                    t = item.get("@type")
                    if isinstance(t, list):
                        schema_types.extend([str(x) for x in t if x])
                    elif t:
                        schema_types.append(str(t))
        except Exception:
            continue

    schema_types = list(dict.fromkeys(schema_types))
    return schema_types


def _has_map(container: BeautifulSoup) -> bool:
    # google maps / mapbox / embeds
    for iframe in container.find_all("iframe"):
        src = (iframe.get("src") or "").lower()
        if "google.com/maps" in src or "mapbox" in src or "maps/embed" in src or "embed?pb=" in src:
            return True
    txt = container.get_text(" ", strip=True).lower()
    if "view on map" in txt or "google map" in txt:
        return True
    return False


def _count_media(container: BeautifulSoup) -> dict:
    img_count = len([i for i in container.find_all("img") if (i.get("src") or "").strip()])
    table_count = len(container.find_all("table"))
    video_count = len(container.find_all("video"))

    # youtube/vimeo iframes count as video
    for iframe in container.find_all("iframe"):
        src = (iframe.get("src") or "").lower()
        if "youtube.com" in src or "youtu.be" in src or "vimeo.com" in src:
            video_count += 1

    return {"image_count": img_count, "video_count": video_count, "table_count": table_count}


def _build_headings_and_sections(container: BeautifulSoup):
    """
    Returns:
      headings: list of {"level":2|3|4, "text":str}
      section_texts: dict[(level,text)] => extracted text under that heading
    """
    headings = []
    section_texts = {}

    # collect heading nodes in order
    nodes = container.find_all(["h2", "h3", "h4"])
    for n in nodes:
        level = int(n.name[1])
        txt = _clean_text(n.get_text(" ", strip=True))
        if txt:
            headings.append({"level": level, "text": txt})

    # extract text under each heading until next heading of same-or-higher priority
    # h2 stops at next h2; h3 stops at next h2/h3; h4 stops at next h2/h3/h4
    for n in nodes:
        level = int(n.name[1])
        title = _clean_text(n.get_text(" ", strip=True))
        if not title:
            continue

        stop_levels = set()
        if level == 2:
            stop_levels = {"h2"}
        elif level == 3:
            stop_levels = {"h2", "h3"}
        else:
            stop_levels = {"h2", "h3", "h4"}

        chunks = []
        cur = n.next_sibling
        while cur is not None:
            # bs4 sibling can be NavigableString
            name = getattr(cur, "name", None)
            if name in stop_levels:
                break

            if name in ["p", "li", "ul", "ol", "div", "span"]:
                txt = _clean_text(cur.get_text(" ", strip=True)) if hasattr(cur, "get_text") else _clean_text(str(cur))
                if txt and len(txt) > 10:
                    chunks.append(txt)

            cur = cur.next_sibling

            # safety: don't explode
            if len(chunks) >= 20:
                break

        section_texts[(level, title)] = _clean_text(" ".join(chunks))

    return headings, section_texts


def _extract_faq_questions(headings, section_texts, schema_types) -> list[str]:
    # 1) if FAQPage schema exists, we'll still try to extract visible questions
    # 2) find a heading containing "faq" or "frequently asked"
    faq_titles = []
    for h in headings:
        t = h["text"].lower()
        if "faq" in t or "frequently asked" in t:
            faq_titles.append((h["level"], h["text"]))

    questions = set()

    # pull questions under FAQ headings
    for (lvl, title) in faq_titles:
        blob = section_texts.get((lvl, title), "")
        for q in re.findall(r"([A-Z][^?]{10,120}\?)", blob):
            questions.add(_clean_text(q))

    # fallback: any headings that look like questions
    for h in headings:
        if "?" in h["text"] and len(h["text"]) <= 140:
            questions.add(_clean_text(h["text"]))

    out = [q for q in questions if q]
    out.sort()
    return out


def parse_html(html: str, page_url: str = "") -> dict:
    soup = BeautifulSoup(html or "", "lxml")

    title = soup.title.get_text(strip=True) if soup.title else ""

    def meta(name: str) -> str:
        tag = soup.find("meta", attrs={"name": name})
        return (tag.get("content") or "").strip() if tag else ""

    def meta_prop(prop: str) -> str:
        tag = soup.find("meta", attrs={"property": prop})
        return (tag.get("content") or "").strip() if tag else ""

    container = _get_main_container(soup)
    _strip_layout_noise(container)

    # headings + section texts
    headings, section_texts = _build_headings_and_sections(container)

    h1 = [_clean_text(h.get_text(" ", strip=True)) for h in soup.find_all("h1")]
    h2 = [h["text"] for h in headings if h["level"] == 2]
    h3 = [h["text"] for h in headings if h["level"] == 3]
    h4 = [h["text"] for h in headings if h["level"] == 4]

    raw_text = _clean_text(container.get_text(" ", strip=True))
    word_count = len(re.findall(r"\b\w+\b", raw_text))

    schema_types = _extract_schema_types(soup)
    schema_count = len(schema_types)

    media_counts = _count_media(container)
    has_map = _has_map(container)

    faq_questions = _extract_faq_questions(headings, section_texts, schema_types)

    return {
        "page_url": page_url or "",
        "competitor_name": _competitor_name_from_url(page_url or ""),
        "title": title,
        "meta_description": meta("description"),
        "robots": meta("robots"),
        "viewport": meta("viewport"),
        "og_title": meta_prop("og:title"),
        "og_description": meta_prop("og:description"),
        "og_image": meta_prop("og:image"),
        "h1": [x for x in h1 if x],
        "h2": [x for x in h2 if x],
        "h3": [x for x in h3 if x],
        "h4": [x for x in h4 if x],
        "headings": headings,                 # ordered list with levels
        "section_texts": {
            f"{lvl}:{txt}": section_texts.get((lvl, txt), "")
            for (lvl, txt) in section_texts.keys()
        },
        "faq_questions": faq_questions,
        "word_count": word_count,
        "schema_types": schema_types,
        "schema_count": schema_count,
        "has_map": has_map,
        **media_counts,
        "raw_text": raw_text,
    }
