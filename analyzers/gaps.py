import re
import json
import time
from urllib.parse import urlparse
from typing import List, Dict, Any, Tuple

import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9",
}

# Headings/blocks that must never become rows
JUNK_HEADING_PATTERNS = [
    r"looking to buy", r"looking to rent", r"subscribe", r"newsletter",
    r"get in touch", r"contact", r"register", r"download", r"podcast",
    r"latest", r"related", r"recommended", r"more (articles|blogs)",
]

# Dubai area hints (used only to enrich comparison description)
DUBAI_AREAS = [
    "JLT", "Jumeirah Lakes Towers", "Downtown Dubai", "Dubai Marina",
    "Business Bay", "DIFC", "Palm Jumeirah", "JBR", "Dubai Hills Estate",
    "Arabian Ranches", "Deira", "Dubai Creek Harbour", "Business Bay"
]


# =====================================================
# Utilities
# =====================================================
def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9\s]", "", _clean(s).lower())


def _is_junk_heading(h: str) -> bool:
    t = (h or "").lower()
    return any(re.search(p, t) for p in JUNK_HEADING_PATTERNS)


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


def _fetch_html(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    return r.text


def _parse_page(url: str) -> Dict[str, Any]:
    html = _fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    # remove obvious noise blocks
    for bad in soup.find_all(["script", "style", "noscript", "nav", "footer", "header", "aside", "form"]):
        bad.decompose()

    headings = []
    for tag in ["h1", "h2", "h3", "h4"]:
        for el in soup.find_all(tag):
            t = _clean(el.get_text(" ", strip=True))
            if not t:
                continue
            if _is_junk_heading(t):
                continue
            headings.append(t)

    full_text = _clean(soup.get_text(" ", strip=True))

    # JSON-LD FAQ questions (if available)
    faq_qs = []
    for sc in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = (sc.string or "").strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue

        blocks = data if isinstance(data, list) else [data]
        for b in blocks:
            if not isinstance(b, dict):
                continue
            graph = b.get("@graph")
            candidates = graph if isinstance(graph, list) else [b]
            for g in candidates:
                if not isinstance(g, dict):
                    continue
                if g.get("@type") == "FAQPage":
                    ents = g.get("mainEntity", [])
                    if isinstance(ents, dict):
                        ents = [ents]
                    for ent in ents:
                        if isinstance(ent, dict):
                            q = _clean(str(ent.get("name", "")))
                            if q and q not in faq_qs:
                                faq_qs.append(q)

    return {
        "url": url,
        "source": _competitor_label(url),
        "headings": headings,
        "text": full_text,
        "faq_questions": faq_qs,
    }


def _count_keywords(text: str, keywords: List[str]) -> int:
    t = text.lower()
    return sum(len(re.findall(r"\b" + re.escape(k) + r"\b", t)) for k in keywords)


def _has_heading_like(headings: List[str], patterns: List[str]) -> bool:
    for h in headings:
        hl = h.lower()
        for p in patterns:
            if re.search(p, hl):
                return True
    return False


def _extract_area_mentions(text: str) -> List[str]:
    found = []
    for a in DUBAI_AREAS:
        if re.search(r"\b" + re.escape(a) + r"\b", text, flags=re.I):
            if a not in found:
                found.append(a)
    # remove "Business Bay" from the list if present (comparison should show others)
    found = [x for x in found if _norm(x) != _norm("Business Bay")]
    return found[:3]


# =====================================================
# Semantic gap rules (rows are FIXED like your examples)
# =====================================================
def _competitor_has_comparison(comp: Dict[str, Any]) -> bool:
    # heading strongly indicates comparison
    if _has_heading_like(comp["headings"], [r"\bcomparison\b", r"\bvs\b", r"other .*neighbou?rhood"]):
        return True
    # text indicates comparison + mentions multiple areas
    areas = _extract_area_mentions(comp["text"])
    if len(areas) >= 1 and _count_keywords(comp["text"], ["comparison", "vs", "versus"]) >= 1:
        return True
    return False


def _bayut_has_comparison(bayut: Dict[str, Any]) -> bool:
    # Bayut should have a dedicated comparison heading to count as "covered"
    return _has_heading_like(bayut["headings"], [r"\bcomparison\b", r"\bvs\b", r"other .*neighbou?rhood"])


def _competitor_has_connectivity(comp: Dict[str, Any]) -> bool:
    return (
        _has_heading_like(comp["headings"], [r"connect", r"location", r"getting around", r"transport"])
        or _count_keywords(comp["text"], ["metro", "road", "roads", "highway", "access", "connectivity", "commute"]) >= 4
    )


def _bayut_has_connectivity_expanded(bayut: Dict[str, Any]) -> bool:
    # needs a transport/connectivity focused heading, not incidental "located in"
    return _has_heading_like(bayut["headings"], [r"connect", r"getting around", r"transport", r"metro", r"road"])


def _competitor_has_extras_within_pros(comp: Dict[str, Any]) -> bool:
    return _count_keywords(comp["text"], ["michelin", "nightlife", "fine dining", "restaurants", "networking", "lifestyle"]) >= 3


def _competitor_has_prefer_despite_cons(comp: Dict[str, Any]) -> bool:
    return (
        _has_heading_like(comp["headings"], [r"why .*prefer", r"despite", r"still choose", r"who .*suit"])
        or _count_keywords(comp["text"], ["despite", "still choose", "worth it", "suits", "who should"]) >= 3
    )


def _competitor_has_final_thoughts(comp: Dict[str, Any]) -> bool:
    return _has_heading_like(comp["headings"], [r"final thoughts", r"in summary", r"wrap up"])


def _competitor_has_conclusion(comp: Dict[str, Any]) -> bool:
    return _has_heading_like(comp["headings"], [r"\bconclusion\b", r"in conclusion"])


def _competitor_has_detailed_pros(comp: Dict[str, Any]) -> bool:
    # must be more than just one "pros" mention: look for structured pros sections or dense pros language
    pros_heading = _has_heading_like(comp["headings"], [r"\bpros\b", r"advantages", r"benefits"])
    pros_density = _count_keywords(comp["text"], ["pros", "advantages", "benefits"]) >= 6
    return pros_heading and pros_density


def _competitor_has_detailed_cons(comp: Dict[str, Any]) -> bool:
    cons_heading = _has_heading_like(comp["headings"], [r"\bcons\b", r"disadvantages", r"drawbacks"])
    cons_density = _count_keywords(comp["text"], ["cons", "disadvantages", "drawbacks", "traffic", "congestion", "high cost", "crowded", "green space"]) >= 6
    return cons_heading and cons_density


def _competitor_has_faqs(comp: Dict[str, Any]) -> bool:
    if comp["faq_questions"]:
        return True
    # fallback: explicit FAQ heading or many question marks + common FAQ topics
    if _has_heading_like(comp["headings"], [r"\bfaq\b", r"frequently asked"]):
        return True
    qmarks = comp["text"].count("?")
    topic_hits = _count_keywords(comp["text"], ["cost of living", "schools", "safety", "market"])
    return (qmarks >= 3 and topic_hits >= 1)


def _bayut_has_faqs(bayut: Dict[str, Any]) -> bool:
    return bool(bayut["faq_questions"]) or _has_heading_like(bayut["headings"], [r"\bfaq\b", r"frequently asked"])


# =====================================================
# PUBLIC: analyze_article (what app.py calls)
# =====================================================
def analyze_article(bayut_url: str, competitor_urls: List[str]) -> Dict[str, Any]:
    bayut = _parse_page(bayut_url)

    out_results = []
    for url in competitor_urls[:5]:
        comp = _parse_page(url)
        source = comp["source"]

        rows: List[Dict[str, str]] = []

        # --- Comparison
        if _competitor_has_comparison(comp) and not _bayut_has_comparison(bayut):
            areas = _extract_area_mentions(comp["text"])
            if areas:
                desc = f"Comparison between the area and nearby neighborhoods such as {', '.join(areas)}, highlighting differences in price, community feel, and suitability."
            else:
                desc = "Comparison between the area and nearby neighborhoods, highlighting differences in price, community feel, and suitability."
            rows.append({"Missing header": "Comparison with Other Dubai Neighborhoods", "What the header contains": desc, "Source": source})

        # --- Connectivity expanded
        if _competitor_has_connectivity(comp) and not _bayut_has_connectivity_expanded(bayut):
            rows.append({
                "Missing header": "Location & Connectivity (expanded)",
                "What the header contains": "Competitor explains more specific transport links and connectivity benefits (metro/roads/access) beyond a basic location overview.",
                "Source": source
            })

        # --- Extras within Pros
        if _competitor_has_extras_within_pros(comp):
            rows.append({
                "Missing header": "Extras within Pros",
                "What the header contains": "Lists lifestyle-driven advantages (e.g., dining, nightlife, networking, modern urban appeal) that are not covered on Bayut.",
                "Source": source
            })

        # --- Additional Reasons Some Prefer (despite cons)
        if _competitor_has_prefer_despite_cons(comp):
            rows.append({
                "Missing header": "Additional Reasons Some Prefer the Area",
                "What the header contains": "Explains why some residents still choose the area despite the downsides, focusing on trade-offs and who it suits.",
                "Source": source
            })

        # --- Final Thoughts / Conclusion split (like your examples)
        if _competitor_has_final_thoughts(comp):
            rows.append({
                "Missing header": "Final Thoughts",
                "What the header contains": "A final summarizing block weighing pros & cons and describing suitability for different resident types.",
                "Source": source
            })

        if _competitor_has_conclusion(comp):
            rows.append({
                "Missing header": "Conclusion Summary",
                "What the header contains": "A concluding wrap-up that helps readers decide if the area fits their needs.",
                "Source": source
            })

        # --- Detailed Pros / Cons
        if _competitor_has_detailed_pros(comp):
            rows.append({
                "Missing header": "Detailed “Pros” sub-sections",
                "What the header contains": "Competitor breaks pros into clearer themes (location, amenities, community, transportation, family infrastructure) beyond Bayut’s coverage.",
                "Source": source
            })

        if _competitor_has_detailed_cons(comp):
            rows.append({
                "Missing header": "Detailed “Cons” sub-sections",
                "What the header contains": "Explicit breakdown of cons such as traffic, cost, crowding, and limited green spaces that Bayut does not cover in the same depth.",
                "Source": source
            })

        # --- FAQs (ONE row only)
        if _competitor_has_faqs(comp):
            if not _bayut_has_faqs(bayut):
                rows.append({
                    "Missing header": "FAQs (missing questions)",
                    "What the header contains": "Competitor includes FAQs around cost of living, schools, safety, and the local market that Bayut does not address as FAQs.",
                    "Source": source
                })
            else:
                # Bayut has FAQs, but competitor may have extra topics -> still keep ONE row (no explosion)
                rows.append({
                    "Missing header": "FAQs (missing questions)",
                    "What the header contains": "Competitor covers additional FAQ topics (e.g., cost of living, schools, safety, market) that are missing from Bayut’s FAQ coverage.",
                    "Source": source
                })

        # de-dup by Missing header (keep first)
        seen = set()
        deduped = []
        for r in rows:
            k = r["Missing header"].strip().lower()
            if k in seen:
                continue
            seen.add(k)
            deduped.append(r)

        out_results.append({
            "competitor": source,
            "url": url,
            "rows": deduped
        })

        time.sleep(0.35)

    return {"bayut_url": bayut_url, "results": out_results}
