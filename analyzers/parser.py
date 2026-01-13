import re
import json
from urllib.parse import urlparse
from bs4 import BeautifulSoup

# -----------------------------
# Small helpers
# -----------------------------
_STOPWORDS = set("""
a an and are as at be been being but by for from has have if in into is it its
of on or that the to was were will with without you your we they their this these those
""".split())

def _clean_text(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    return s

def _norm_heading(s: str) -> str:
    s = _clean_text(s).lower()
    s = re.sub(r"[\u2010-\u2015]", "-", s)          # dashes
    s = re.sub(r"[^\w\s-]", "", s)                  # remove punctuation
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _guess_source_name(page_url: str) -> str:
    if not page_url:
        return "Competitor"
    host = (urlparse(page_url).netloc or "").lower()
    host = host.replace("www.", "")
    if "propertyfinder" in host:
        return "Property Finder"
    if "drivenproperties" in host:
        return "Driven Properties"
    if "emaar" in host:
        return "Emaar"
    if "bayut" in host:
        return "Bayut"
    # fallback: domain as name
    return host.split(":")[0]

def _extract_jsonld(soup: BeautifulSoup) -> list:
    blobs = []
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = (tag.string or "").strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                blobs.extend([x for x in data if isinstance(x, (dict, list))])
            elif isinstance(data, dict):
                blobs.append(data)
        except Exception:
            continue
    return blobs

def _find_faq_in_jsonld(jsonld_blobs: list) -> list[str]:
    questions = []

    def walk(node):
        if isinstance(node, dict):
            t = node.get("@type") or node.get("type")
            if isinstance(t, list):
                types = [str(x) for x in t]
            else:
                types = [str(t)] if t else []

            if any(x.lower() == "faqpage" for x in types):
                main = node.get("mainEntity") or node.get("mainentity") or []
                if isinstance(main, dict):
                    main = [main]
                for item in main:
                    if isinstance(item, dict):
                        name = item.get("name")
                        if name:
                            questions.append(_clean_text(str(name)))
            # keep walking
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for x in node:
                walk(x)

    for b in jsonld_blobs:
        walk(b)

    # unique
    out = []
    seen = set()
    for q in questions:
        k = q.lower()
        if k and k not in seen:
            seen.add(k)
            out.append(q)
    return out

def _find_faq_in_dom(soup: BeautifulSoup) -> list[str]:
    # Heuristic: containers with faq in class/id, then extract question-like lines
    questions = []
    containers = soup.find_all(attrs={"class": re.compile(r"\bf(a|)q\b", re.I)}) + \
                 soup.find_all(attrs={"id": re.compile(r"\bf(a|)q\b", re.I)})

    # also common accordion buttons
    for c in containers:
        # buttons/headings inside accordions often hold the question
        for tag in c.find_all(["button", "summary", "h2", "h3", "h4", "p", "strong"]):
            t = _clean_text(tag.get_text(" ", strip=True))
            if not t:
                continue
            # “Question-like” heuristics
            if "?" in t or t.lower().startswith(("what", "where", "how", "when", "why", "is ", "are ", "can ")):
                # avoid very long paragraphs
                if 5 <= len(t) <= 140:
                    questions.append(t)

    # unique
    out, seen = [], set()
    for q in questions:
        k = q.lower()
        if k and k not in seen:
            seen.add(k)
            out.append(q)
    return out[:25]

def _sectionize(soup: BeautifulSoup) -> dict:
    """
    Build a simple map:
      sections_norm[norm_title] = {
        title, level, text, bullets
      }
    based on heading tags and following content until next heading.
    """
    body = soup.body or soup
    sections = {}
    order = []

    current = None

    def start_section(title: str, level: int):
        nonlocal current
        norm = _norm_heading(title)
        if not norm:
            return
        current = norm
        if norm not in sections:
            sections[norm] = {"title": _clean_text(title), "level": level, "text": "", "bullets": []}
            order.append(norm)

    # initialize using first h1 as anchor if exists
    for node in body.descendants:
        if getattr(node, "name", None) in ("h1", "h2", "h3"):
            title = node.get_text(" ", strip=True)
            level = int(node.name[1])
            start_section(title, level)
            continue

        if current and getattr(node, "name", None) in ("p", "li"):
            t = _clean_text(node.get_text(" ", strip=True))
            if not t:
                continue
            if node.name == "li":
                sections[current]["bullets"].append(t)
            else:
                sections[current]["text"] += (t + " ")

    # clean up
    for k in list(sections.keys()):
        sections[k]["text"] = _clean_text(sections[k]["text"])
        # avoid mega bullets
        sections[k]["bullets"] = [b for b in sections[k]["bullets"] if 3 <= len(b) <= 220][:40]

    return {"sections": sections, "order": order}

def _count_media(soup: BeautifulSoup) -> dict:
    imgs = soup.find_all("img")
    videos = soup.find_all("video")
    iframes = soup.find_all("iframe")

    # "map" heuristics: google maps iframe or map keywords
    has_map = False
    for fr in iframes:
        src = (fr.get("src") or "").lower()
        if "google.com/maps" in src or "maps.google" in src:
            has_map = True
            break
    if not has_map:
        txt = soup.get_text(" ", strip=True).lower()
        if "map" in txt and ("google" in txt or "location" in txt):
            has_map = True

    table_count = len(soup.find_all("table"))

    return {
        "image_count": len(imgs),
        "video_count": len(videos),
        "iframe_count": len(iframes),
        "table_count": table_count,
        "has_map": has_map,
    }

def parse_html(html: str, page_url: str = "") -> dict:
    soup = BeautifulSoup(html or "", "lxml")

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

    # Clean visible text for word count
    clean = BeautifulSoup(str(soup), "lxml")
    for t in clean(["script", "style", "noscript"]):
        t.decompose()

    text = clean.get_text(" ", strip=True)
    word_count = len(re.findall(r"\b\w+\b", text))

    # Schema types (simple list)
    schema_types = []
    jsonld_blobs = _extract_jsonld(soup)
    for item in jsonld_blobs:
        if isinstance(item, dict) and "@type" in item:
            t = item["@type"]
            if isinstance(t, list):
                schema_types.extend([str(x) for x in t if x])
            else:
                schema_types.append(str(t))

    schema_types = list(dict.fromkeys([x for x in schema_types if x]))

    # FAQ detection
    faq_q_jsonld = _find_faq_in_jsonld(jsonld_blobs)
    faq_q_dom = _find_faq_in_dom(soup)
    faq_questions = []
    seen = set()
    for q in (faq_q_jsonld + faq_q_dom):
        k = q.lower().strip()
        if k and k not in seen:
            seen.add(k)
            faq_questions.append(q)

    section_pack = _sectionize(soup)
    media = _count_media(soup)

    return {
        "page_url": page_url,
        "source_name": _guess_source_name(page_url),

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
        "faq_questions": faq_questions,
        "faq_count": len(faq_questions),

        "sections": section_pack["sections"],
        "
