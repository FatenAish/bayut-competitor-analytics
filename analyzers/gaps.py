import re
import json
import time
from urllib.parse import urlparse
from typing import List, Dict, Any

import requests
from bs4 import BeautifulSoup

# =========================================
# HARD RULE: ONLY THESE GAP ROWS ARE ALLOWED
# =========================================
GAPS = [
    {
        "id": "comparison",
        "title": "Comparison with Other Dubai Neighborhoods",
        "desc": "Comparison between Business Bay and nearby areas (e.g., JLT/Downtown/Marina), highlighting differences in lifestyle, pricing, and community feel.",
        "need": [r"\bcomparison\b", r"\bvs\b", r"\bversus\b", r"\bother dubai\b", r"\bneighbou?rhoods?\b", r"\bJLT\b", r"\bDowntown Dubai\b", r"\bDubai Marina\b"],
        "avoid": [],
    },
    {
        "id": "connectivity",
        "title": "Location & Connectivity (expanded)",
        "desc": "More specific detail on transport links and connectivity (metro/roads/access), beyond a basic location mention.",
        "need": [r"\bmetro\b", r"\broad(s)?\b", r"\bhighway\b", r"\baccess\b", r"\bconnect(ion|ivity)\b", r"\bcommute\b"],
        "avoid": [],
    },
    {
        "id": "extras_pros",
        "title": "Extras within Pros",
        "desc": "Lifestyle-driven advantages (e.g., dining, nightlife, networking, modern urban appeal) that go beyond generic pros.",
        "need": [r"\bnightlife\b", r"\bfine dining\b", r"\brestaurant(s)?\b", r"\bmichelin\b", r"\bnetwork(ing)?\b", r"\blifestyle\b"],
        "avoid": [],
    },
    {
        "id": "prefer_despite_cons",
        "title": "Additional Reasons Some Prefer Business Bay",
        "desc": "Explains why some residents still choose Business Bay despite the downsides (trade-offs, who it suits, why it’s worth it).",
        "need": [r"\bdespite\b", r"\beven though\b", r"\bstill choose\b", r"\bworth it\b", r"\bwho should\b", r"\bsuits\b"],
        "avoid": [],
    },
    {
        "id": "final_thoughts",
        "title": "Final Thoughts / Conclusion",
        "desc": "A closing synthesis weighing pros and cons and guiding which types of residents the area is most suitable for.",
        "need": [r"\bfinal thoughts\b", r"\bconclusion\b", r"\bin conclusion\b", r"\bsummary\b", r"\bto sum up\b"],
        "avoid": [],
    },
    {
        "id": "pros_detail",
        "title": "Detailed “Pros” sub-sections",
        "desc": "Pros are broken into clearer themes (amenities, lifestyle, transport, community) rather than a short/general list.",
        "need": [r"\bpros\b", r"\badvantages\b", r"\bbenefits\b"],
        "avoid": [],
        "require_density": True,  # needs more than just one 'pros' mention
    },
    {
        "id": "cons_detail",
        "title": "Detailed “Cons” sub-sections",
        "desc": "Cons are explicitly broken down (e.g., traffic, cost, crowding, limited green space) rather than a brief mention.",
        "need": [r"\bcons\b", r"\bdisadvantages\b", r"\bdrawbacks\b", r"\btraffic\b", r"\bcongestion\b", r"\bcrowd(ed|ing)\b", r"\bgreen space(s)?\b", r"\bhigh cost\b"],
        "avoid": [],
        "require_density": True,
    },
    {
        "id": "faqs",
        "title": "FAQs",
        "desc": "Competitor covers common questions (e.g., cost of living, schools, safety, market), which Bayut does not currently address as FAQs.",
        "need": [r"\bFAQ\b", r"\bfrequently asked\b", r"\bhow much\b", r"\bcost of living\b", r"\bschools?\b", r"\bsafety\b", r"\bmarket\b"],
        "avoid": [],
        "faq_special": True,
    },
]

# junk headings/blocks we never want to treat as gaps
JUNK = [
    r"looking to buy", r"looking to rent", r"explore", r"latest blogs", r"podcasts?",
    r"register", r"subscribe", r"get in touch", r"contact", r"please stand by"
]

HEADERS = {"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"}


# =========================================
# FETCH + CLEAN TEXT (semantic only)
# =========================================
def _clean_text(s: str) -> str:
    s = re.sub(r"\s+", " ", (s or "")).strip()
    return s


def _fetch_visible_text(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    for bad in soup.find_all(["script", "style", "noscript", "nav", "footer", "header", "aside", "form"]):
        bad.decompose()

    text = _clean_text(soup.get_text(" "))
    return text


def _competitor_label(url: str) -> str:
    host = urlparse(url).netloc.lower().replace("www.", "")
    if "drivenproperties" in host:
        return "Driven Properties"
    if "propertyfinder" in host:
        return "Property Finder"
    if "bayut" in host:
        return "Bayut"
    if "dubizzle" in host:
        return "Dubizzle"
    return host.split(":")[0] if host else "Competitor"


def _count(patterns: List[str], text: str) -> int:
    total = 0
    for p in patterns:
        total += len(re.findall(p, text, flags=re.I))
    return total


def _has_junk(text: str) -> bool:
    t = text.lower()
    return any(re.search(p, t) for p in JUNK)


def _extract_jsonld_faq_questions(html_text: str) -> List[str]:
    soup = BeautifulSoup(html_text, "html.parser")
    qs = []
    for sc in soup.find_all("script", type="application/ld+json"):
        raw = (sc.string or "").strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue

        blocks = data if isinstance(data, list) else [data]
        for b in blocks:
            graph = b.get("@graph", [b]) if isinstance(b, dict) else []
            for g in graph:
                if isinstance(g, dict) and g.get("@type") == "FAQPage":
                    ents = g.get("mainEntity", [])
                    if isinstance(ents, dict):
                        ents = [ents]
                    for ent in ents:
                        if isinstance(ent, dict):
                            name = _clean_text(str(ent.get("name", "")))
                            if name and name not in qs:
                                qs.append(name)
    return qs


# =========================================
# SEMANTIC GAP ENGINE (ONLY ALLOWED ROWS)
# =========================================
def _detect_gaps(bayut_text: str, comp_text: str, source: str) -> List[Dict[str, str]]:
    bt = bayut_text.lower()
    ct = comp_text.lower()

    rows = []

    # special: FAQs as ONE ROW (no explosion)
    # If competitor has FAQ signals or JSONLD FAQ questions and Bayut doesn't -> include row
    # (we treat Bayut FAQ absence as: few/none FAQ triggers)
    for g in GAPS:
        if not g.get("faq_special"):
            continue
        comp_score = _count(g["need"], comp_text)
        bayut_score = _count(g["need"], bayut_text)
        if comp_score >= 2 and bayut_score < 2:
            rows.append({
                "Missing header": g["title"],
                "What the header contains": g["desc"],
                "Source": source
            })

    # other gaps
    for g in GAPS:
        if g.get("faq_special"):
            continue

        comp_score = _count(g["need"], comp_text)
        bayut_score = _count(g["need"], bayut_text)

        # density requirement for pros/cons detail (avoid false positives)
        if g.get("require_density"):
            if comp_score < 5:
                continue

        # competitor has it, Bayut doesn't
        if comp_score >= 2 and bayut_score < 2:
            rows.append({
                "Missing header": g["title"],
                "What the header contains": g["desc"],
                "Source": source
            })

    # de-dup by Missing header
    seen = set()
    out = []
    for r in rows:
        if r["Missing header"] in seen:
            continue
        seen.add(r["Missing header"])
        out.append(r)

    return out


# =========================================
# PUBLIC API
# =========================================
def analyze_article(bayut_url: str, competitor_urls: List[str]) -> Dict[str, Any]:
    # fetch Bayut
    bayut_html = requests.get(bayut_url, headers=HEADERS, timeout=25).text
    bayut_text = _fetch_visible_text(bayut_url)

    results = []
    for url in competitor_urls[:5]:
        source = _competitor_label(url)

        try:
            comp_html = requests.get(url, headers=HEADERS, timeout=25).text
            comp_text = _fetch_visible_text(url)

            # If page is junk/blocked, return no rows rather than nonsense
            if not comp_text or len(comp_text) < 300 or _has_junk(comp_text):
                results.append({"competitor": source, "url": url, "rows": []})
                continue

            rows = _detect_gaps(bayut_text=bayut_text, comp_text=comp_text, source=source)

            results.append({"competitor": source, "url": url, "rows": rows})

        except Exception:
            # fail safe: no spam rows, just empty
            results.append({"competitor": source, "url": url, "rows": []})

        time.sleep(0.35)

    return {"bayut_url": bayut_url, "results": results}
