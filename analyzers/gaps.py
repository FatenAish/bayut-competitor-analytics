import re
import json
import time
from urllib.parse import urlparse
from typing import List, Dict, Any

import requests
from bs4 import BeautifulSoup


# =====================================================
# CONFIG
# =====================================================
_IGNORE_PATTERNS = [
    r"subscribe",
    r"newsletter",
    r"looking to buy",
    r"looking to rent",
    r"speak with us",
    r"contact us",
    r"register your interest",
    r"get in touch",
    r"download",
    r"podcast",
    r"latest blogs",
]

_STOPWORDS = {
    "about","above","after","again","against","along","among","around","because","before","being","below","between",
    "could","does","doing","during","each","either","every","first","found","great","here","into","its","itself",
    "many","might","more","most","other","over","some","such","than","that","their","there","these","those","through",
    "under","very","what","where","which","while","would","your","yours",
    "business","bay","dubai"
}


# =====================================================
# NORMALIZATION
# =====================================================
def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def _norm(s: str) -> str:
    s = _clean(s).lower()
    return re.sub(r"[^a-z0-9\s\?\-\(\)]", "", s)


def _is_ignored_heading(title: str) -> bool:
    t = title.lower()
    return any(re.search(p, t) for p in _IGNORE_PATTERNS)


# =====================================================
# COMPETITOR LABEL
# =====================================================
def _competitor_label(url: str) -> str:
    host = urlparse(url).netloc.lower().replace("www.", "")
    if "bayut" in host:
        return "Bayut"
    if "drivenproperties" in host:
        return "Driven Properties"
    if "propertyfinder" in host:
        return "Property Finder"
    if "dubizzle" in host:
        return "Dubizzle"
    return host.split(":")[0] or "Competitor"


# =====================================================
# FETCH & PARSE
# =====================================================
def _fetch_html(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9",
    }
    r = requests.get(url, headers=headers, timeout=25)
    r.raise_for_status()
    return r.text


def _visible_text(el) -> str:
    for bad in el.find_all(["script", "style", "noscript"]):
        bad.decompose()
    return _clean(el.get_text(" ", strip=True))


def _collect_section_text(heading) -> str:
    lvl = int(heading.name[1])
    chunks = []
    node = heading

    while True:
        node = node.find_next_sibling()
        if not node:
            break
        if getattr(node, "name", None) and node.name.startswith("h"):
            if int(node.name[1]) <= lvl:
                break
        txt = _visible_text(node)
        if txt:
            chunks.append(txt)
        if sum(len(c) for c in chunks) > 2500:
            break

    return " ".join(chunks)[:2500]


def _extract_faq(soup: BeautifulSoup) -> List[str]:
    qs = []

    # JSON-LD first
    for sc in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(sc.string or "")
        except Exception:
            continue

        blocks = data if isinstance(data, list) else [data]
        for b in blocks:
            graph = b.get("@graph", [b])
            for g in graph:
                if g.get("@type") == "FAQPage":
                    for q in g.get("mainEntity", []):
                        name = _clean(q.get("name", ""))
                        if name:
                            qs.append(name)

    if qs:
        return list(dict.fromkeys(qs))

    # Fallback: question-like headings / buttons
    for el in soup.find_all(["h2", "h3", "button", "summary"]):
        t = _clean(el.get_text())
        if t.endswith("?"):
            qs.append(t)

    return list(dict.fromkeys(qs))[:20]


def parse_page(url: str) -> Dict[str, Any]:
    html = _fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    parsed = {
        "competitor_name": _competitor_label(url),
        "h2": [],
        "h3": [],
        "h4": [],
        "section_texts": {},
        "faq_questions": [],
        "word_count": 0,
    }

    body_text = _visible_text(soup.body or soup)
    parsed["word_count"] = len(re.findall(r"\w+", body_text))

    for tag in ["h2", "h3", "h4"]:
        for h in soup.find_all(tag):
            title = _clean(h.get_text())
            if not title:
                continue
            parsed[tag].append(title)
            txt = _collect_section_text(h)
            if txt:
                parsed["section_texts"][f"{tag[1]}:{title}"] = txt

    parsed["faq_questions"] = _extract_faq(soup)
    return parsed


# =====================================================
# GAP LOGIC
# =====================================================
def _keywords(text: str) -> List[str]:
    words = re.findall(r"[A-Za-z]{5,}", text.lower())
    return list(dict.fromkeys(
        w for w in words if w not in _STOPWORDS
    ))[:15]


def _get_section(parsed, lvl, title):
    return parsed["section_texts"].get(f"{lvl}:{title}", "")


def update_gaps(bayut: Dict[str, Any], competitors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []

    bayut_heads = {
        _norm(h) for h in bayut["h2"] + bayut["h3"] + bayut["h4"]
    }

    for comp in competitors:
        p = comp["parsed"]
        source = p["competitor_name"]

        # ---- Missing headers
        for tag in ["h2", "h3", "h4"]:
            lvl = int(tag[1])
            for h in p[tag]:
                if _is_ignored_heading(h):
                    continue
                if _norm(h) not in bayut_heads and "faq" not in h.lower():
                    txt = _get_section(p, lvl, h)
                    rows.append({
                        "Missing header": h,
                        "What the header contains": txt[:220] + ("..." if len(txt) > 220 else ""),
                        "Source": source
                    })

        # ---- Missing FAQ questions
        bayut_faq = {_norm(q) for q in bayut["faq_questions"]}
        missing_faq = [q for q in p["faq_questions"] if _norm(q) not in bayut_faq]
        if missing_faq:
            rows.append({
                "Missing header": "FAQs",
                "What the header contains": "; ".join(missing_faq[:10]),
                "Source": source
            })

        # ---- Content gaps inside shared headers
        for tag in ["h2", "h3", "h4"]:
            lvl = int(tag[1])
            for h in p[tag]:
                if _norm(h) not in bayut_heads:
                    continue
                comp_txt = _get_section(p, lvl, h)
                bayut_txt = _get_section(bayut, lvl, h)
                if len(comp_txt) < 120:
                    continue
                diff = [
                    w for w in _keywords(comp_txt)
                    if w not in _keywords(bayut_txt)
                ]
                if len(diff) >= 5:
                    rows.append({
                        "Missing header": f"{h} (content gap)",
                        "What the header contains": ", ".join(diff[:12]),
                        "Source": source
                    })

    # dedupe
    seen = set()
    out = []
    for r in rows:
        k = tuple(r.values())
        if k not in seen:
            seen.add(k)
            out.append(r)

    return out


# =====================================================
# MAIN ENTRY POINT
# =====================================================
def analyze_article(bayut_url: str, competitor_urls: List[str]) -> Dict[str, Any]:
    bayut = parse_page(bayut_url)

    results = []
    for url in competitor_urls[:5]:
        parsed = parse_page(url)
        rows = update_gaps(
            bayut,
            [{"url": url, "parsed": parsed}]
        )
        results.append({
            "competitor": parsed["competitor_name"],
            "url": url,
            "rows": rows
        })
        time.sleep(0.4)

    return {
        "bayut_url": bayut_url,
        "results": results
    }
