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
    r"subscribe", r"newsletter", r"looking to buy", r"looking to rent",
    r"speak with us", r"contact us", r"register your interest",
    r"get in touch", r"download", r"podcast", r"latest blogs",
]

_STOPWORDS = {
    "about","above","after","again","against","along","among","around",
    "because","before","being","below","between","could","does","doing",
    "during","each","either","every","first","found","great","here","into",
    "its","itself","many","might","more","most","other","over","some",
    "such","than","that","their","there","these","those","through","under",
    "very","what","where","which","while","would","your","yours",
    "business","bay","dubai"
}


# =====================================================
# HELPERS
# =====================================================
def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9\s]", "", _clean(s).lower())


def _is_ignored_heading(title: str) -> bool:
    return any(re.search(p, title.lower()) for p in _IGNORE_PATTERNS)


def _competitor_label(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if "drivenproperties" in host:
        return "Driven Properties"
    if "propertyfinder" in host:
        return "Property Finder"
    if "bayut" in host:
        return "Bayut"
    if "dubizzle" in host:
        return "Dubizzle"
    return host.replace("www.", "").split(".")[0].title()


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


def parse_page(url: str) -> Dict[str, Any]:
    soup = BeautifulSoup(_fetch_html(url), "html.parser")

    parsed = {
        "competitor_name": _competitor_label(url),
        "h2": [],
        "h3": [],
        "h4": [],
        "faq_questions": [],
    }

    # Headings
    for tag in ["h2", "h3", "h4"]:
        for h in soup.find_all(tag):
            title = _clean(h.get_text())
            if title and not _is_ignored_heading(title):
                parsed[tag].append(title)

    # FAQs (JSON-LD only, no explosion)
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
                        qn = _clean(q.get("name", ""))
                        if qn:
                            parsed["faq_questions"].append(qn)

    parsed["faq_questions"] = list(dict.fromkeys(parsed["faq_questions"]))
    return parsed


# =====================================================
# GAP ANALYSIS (FINAL LOGIC)
# =====================================================
def update_gaps(bayut: Dict[str, Any], competitors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []

    bayut_heads = {_norm(h) for h in bayut["h2"] + bayut["h3"]}

    for comp in competitors:
        p = comp["parsed"]
        source = p["competitor_name"]

        # ---- Missing H2 / H3 (H4 grouped)
        for h in p["h2"] + p["h3"]:
            if _norm(h) in bayut_heads:
                continue

            # collect child H4s if any
            children = [c for c in p["h4"] if _norm(h) in _norm(c)]
            child_summary = ""
            if children:
                child_summary = f" Includes sub-sections such as {', '.join(children[:3])}."

            rows.append({
                "Missing header": h,
                "What the header contains":
                    f"This section is covered by the competitor but missing on Bayut.{child_summary}",
                "Source": source
            })

        # ---- FAQs (ONE ROW ONLY)
        bayut_faq = {_norm(q) for q in bayut["faq_questions"]}
        missing_faq = [q for q in p["faq_questions"] if _norm(q) not in bayut_faq]

        if missing_faq:
            rows.append({
                "Missing header": "FAQs",
                "What the header contains":
                    "Missing FAQ coverage such as: " + ", ".join(missing_faq[:5]) + ".",
                "Source": source
            })

    # de-dup
    seen = set()
    out = []
    for r in rows:
        key = tuple(r.values())
        if key not in seen:
            seen.add(key)
            out.append(r)

    return out


# =====================================================
# ENTRY POINT
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
