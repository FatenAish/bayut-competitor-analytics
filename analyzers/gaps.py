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
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9",
}

IGNORE_PATTERNS = [
    r"subscribe", r"newsletter", r"looking to buy", r"looking to rent",
    r"get in touch", r"contact", r"download", r"latest", r"explore",
]

STOPWORDS = {
    "business","bay","dubai","about","this","that","with","from","your","their",
    "there","where","which","while","would","could","should"
}


# =====================================================
# SEMANTIC GAP RULES (THE HEART OF THE TOOL)
# =====================================================
GAP_RULES = [
    {
        "key": "comparison",
        "title": "Comparison with Other Dubai Neighborhoods",
        "triggers": ["comparison", "vs", "versus", "other dubai", "neighborhood"],
        "description": (
            "Comparison between Business Bay and nearby areas such as JLT or Downtown Dubai, "
            "highlighting differences in lifestyle, pricing, and community feel."
        )
    },
    {
        "key": "connectivity",
        "title": "Location & Connectivity (expanded)",
        "triggers": ["metro", "connectivity", "roads", "highway", "access", "central"],
        "description": (
            "Detailed explanation of transport links, road access, and the benefits of Business Bay’s "
            "central location beyond a basic location overview."
        )
    },
    {
        "key": "pros_detail",
        "title": "Detailed “Pros” sub-sections",
        "triggers": ["pros", "advantages", "benefits"],
        "description": (
            "Breaks down advantages into clearer themes such as amenities, lifestyle, transport, "
            "and community appeal rather than listing them briefly."
        )
    },
    {
        "key": "cons_detail",
        "title": "Detailed “Cons” sub-sections",
        "triggers": ["cons", "disadvantages", "challenges"],
        "description": (
            "Explicit breakdown of disadvantages like traffic congestion, high cost of living, "
            "crowded areas, or limited green spaces."
        )
    },
    {
        "key": "extras",
        "title": "Additional Reasons Some Prefer Business Bay",
        "triggers": ["despite", "still choose", "why choose", "appeal"],
        "description": (
            "Explains why some residents prefer Business Bay despite the cons, focusing on lifestyle "
            "trade-offs such as nightlife, dining, and professional networking."
        )
    },
    {
        "key": "final",
        "title": "Final Thoughts / Conclusion",
        "triggers": ["final thoughts", "conclusion", "summary", "wrap up"],
        "description": (
            "A closing synthesis weighing the pros and cons and advising which types of residents "
            "Business Bay is most suitable for."
        )
    },
    {
        "key": "faq",
        "title": "FAQs",
        "triggers": ["faq", "frequently asked", "how much", "is it safe", "schools", "cost"],
        "description": (
            "Covers common reader questions such as cost of living, schools, safety, and the local "
            "real estate market that are not addressed on Bayut."
        )
    },
]


# =====================================================
# UTILITIES
# =====================================================
def clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def competitor_label(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if "drivenproperties" in host:
        return "Driven Properties"
    if "propertyfinder" in host:
        return "Property Finder"
    if "bayut" in host:
        return "Bayut"
    return host.replace("www.", "").split(".")[0].title()


def fetch_text(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    for bad in soup.find_all(["script", "style", "noscript", "footer", "nav"]):
        bad.decompose()

    return clean(soup.get_text(" "))


# =====================================================
# SIGNAL EXTRACTION
# =====================================================
def extract_signals(text: str) -> Dict[str, int]:
    signals = {}
    for rule in GAP_RULES:
        count = 0
        for t in rule["triggers"]:
            count += len(re.findall(r"\b" + re.escape(t) + r"\b", text))
        signals[rule["key"]] = count
    return signals


# =====================================================
# GAP ANALYSIS (SEMANTIC)
# =====================================================
def analyze_gaps(bayut_text: str, comp_text: str, source: str) -> List[Dict[str, str]]:
    bayut_signals = extract_signals(bayut_text)
    comp_signals = extract_signals(comp_text)

    rows = []

    for rule in GAP_RULES:
        key = rule["key"]

        # competitor meaningfully covers it, Bayut does not
        if comp_signals[key] >= 3 and bayut_signals[key] < 2:
            rows.append({
                "Missing header": rule["title"],
                "What the header contains": rule["description"],
                "Source": source
            })

    return rows


# =====================================================
# MAIN ENTRY POINT
# =====================================================
def analyze_article(bayut_url: str, competitor_urls: List[str]) -> Dict[str, Any]:
    bayut_text = fetch_text(bayut_url)

    results = []

    for url in competitor_urls[:5]:
        comp_text = fetch_text(url)
        source = competitor_label(url)

        rows = analyze_gaps(
            bayut_text=bayut_text,
            comp_text=comp_text,
            source=source
        )

        results.append({
            "competitor": source,
            "url": url,
            "rows": rows
        })

        time.sleep(0.4)

    return {
        "bayut_url": bayut_url,
        "results": results
    }
