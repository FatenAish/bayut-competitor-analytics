import re
from collections import defaultdict
from urllib.parse import urlparse


# ---------------------------
# Helpers
# ---------------------------

COMPETITOR_NAME_MAP = {
    "drivenproperties.com": "Driven Properties",
    "www.drivenproperties.com": "Driven Properties",
    "propertyfinder.ae": "Property Finder",
    "www.propertyfinder.ae": "Property Finder",
    "properties.emaar.com": "Emaar",
    "www.properties.emaar.com": "Emaar",
    "bayut.com": "Bayut",
    "www.bayut.com": "Bayut",
}


STOP_HEADINGS = {
    "newsletter", "subscribe", "register", "register your interest",
    "contact", "contact us", "speak with us today", "speak with us",
    "looking to rent", "looking to buy", "buy", "rent",
    "the latest blogs", "podcasts", "follow us", "share",
    "privacy policy", "terms", "cookie policy", "download our app",
    "related", "related articles", "read more"
}


def _competitor_name(url: str) -> str:
    host = urlparse(url).netloc.lower().strip()
    if host in COMPETITOR_NAME_MAP:
        return COMPETITOR_NAME_MAP[host]
    # fallback: take second-level name
    parts = [p for p in host.split(".") if p]
    if len(parts) >= 2:
        return parts[-2].capitalize()
    return host or "Competitor"


def _norm(s: str) -> str:
    s = re.sub(r"\s+", " ", (s or "")).strip()
    s = re.sub(r"[:\-–—]+\s*$", "", s).strip()
    return s


def _is_noise_heading(h: str) -> bool:
    if not h:
        return True
    t = _norm(h)
    low = t.lower()
    if len(t) < 6:
        return True
    if low in STOP_HEADINGS:
        return True
    if any(x in low for x in ["subscribe", "newsletter", "register", "contact", "download", "follow", "share"]):
        return True
    return False


def _headings(parsed: dict) -> list[str]:
    # primary section headings are H2, fallback to H3
    hs = (parsed.get("h2") or []) + (parsed.get("h3") or [])
    out = []
    for h in hs:
        t = _norm(h)
        if _is_noise_heading(t):
            continue
        out.append(t)
    # unique keep order
    seen = set()
    uniq = []
    for x in out:
        k = x.lower()
        if k not in seen:
            seen.add(k)
            uniq.append(x)
    return uniq


# ---------------------------
# Section detectors
# ---------------------------

NEIGHBORHOODS = [
    "Downtown Dubai", "Dubai Marina", "JLT", "Jumeirah Lakes Towers", "DIFC",
    "Business Bay", "Dubai Creek Harbour", "Jumeirah", "Al Quoz"
]


def _has_comparison(parsed: dict) -> bool:
    hs = " ".join(_headings(parsed)).lower()
    return any(k in hs for k in ["comparison", "compare", "vs", "versus", "other dubai", "other neighborhoods", "other neighbourhoods"])


def _has_conclusion(parsed: dict) -> bool:
    hs = " ".join(_headings(parsed)).lower()
    return any(k in hs for k in ["conclusion", "final thoughts", "wrap up", "summary"])


def _faq_strength(parsed: dict) -> int:
    # 0 = none, else approx number of question-like headings
    if not parsed.get("has_faq_signal"):
        return 0
    return int(parsed.get("question_like_count") or 0)


def _has_map(parsed: dict) -> bool:
    return bool(parsed.get("has_map"))


def _has_nearby_areas(parsed: dict) -> bool:
    hs = " ".join(_headings(parsed)).lower()
    return any(k in hs for k in ["nearby", "near by", "near", "communities", "alternatives", "around", "close to", "nearby areas"])


def _extract_neighborhood_examples(parsed: dict) -> list[str]:
    text = (parsed.get("raw_text") or "")
    found = []
    for n in NEIGHBORHOODS:
        if re.search(rf"\b{re.escape(n)}\b", text, flags=re.IGNORECASE):
            if n not in found and n != "Business Bay":
                found.append(n)
    # keep it short
    # Prefer the 3 most useful ones
    prefer = ["Downtown Dubai", "Dubai Marina", "JLT"]
    ordered = [x for x in prefer if x in found] + [x for x in found if x not in prefer]
    return ordered[:3] if ordered else ["Downtown Dubai", "Dubai Marina", "JLT"]


# ---------------------------
# Main: UPDATE mode gaps table
# ---------------------------

def update_gaps(bayut_parsed: dict, competitors: list[dict]) -> list[dict]:
    """
    Returns rows exactly like you approved:
    - Missing section in Bayut
    - What to add (recommendation)
    - Why it matters
    - Source (competitor)
    """
    # Bayut presence/strength
    bayut_has_comp = _has_comparison(bayut_parsed)
    bayut_has_conc = _has_conclusion(bayut_parsed)
    bayut_faq = _faq_strength(bayut_parsed)
    bayut_has_map = _has_map(bayut_parsed)
    bayut_has_nearby = _has_nearby_areas(bayut_parsed)

    # Competitor presence/strength + sources
    comp_sources = defaultdict(set)

    comp_has_comp = False
    comp_has_conc = False
    comp_has_map = False
    comp_has_nearby = False

    max_faq = 0
    best_faq_sources = set()

    comp_example_neigh = []

    for c in competitors:
        p = c["parsed"]
        name = _competitor_name(c["url"])

        if _has_comparison(p):
            comp_has_comp = True
            comp_sources["Comparison with Other Dubai Neighborhoods"].add(name)
            comp_example_neigh = comp_example_neigh or _extract_neighborhood_examples(p)

        if _has_conclusion(p):
            comp_has_conc = True
            comp_sources["Conclusion"].add(name)

        faq_n = _faq_strength(p)
        if faq_n > 0:
            if faq_n > max_faq:
                max_faq = faq_n
                best_faq_sources = {name}
            elif faq_n == max_faq:
                best_faq_sources.add(name)

        if _has_map(p):
            comp_has_map = True
            comp_sources["Map / Location visuals"].add(name)

        if _has_nearby_areas(p):
            comp_has_nearby = True
            comp_sources["Nearby Communities / Alternatives"].add(name)

    rows = []

    # 1) Comparison
    if comp_has_comp and not bayut_has_comp:
        neigh = ", ".join(comp_example_neigh or ["Downtown Dubai", "Dubai Marina", "JLT"])
        rows.append({
            "Missing section in Bayut": "Comparison with Other Dubai Neighborhoods",
            "What to add (recommendation)": f"Add a comparison block with {neigh} (1 short paragraph each: similarities + differences + who it suits).",
            "Why it matters": "Adds high-intent comparison content (SEO/AEO) and helps users decide faster.",
            "Source (competitor)": " / ".join(sorted(comp_sources["Comparison with Other Dubai Neighborhoods"])) or "Competitors"
        })

    # 2) Conclusion
    if comp_has_conc and not bayut_has_conc:
        rows.append({
            "Missing section in Bayut": "Conclusion",
            "What to add (recommendation)": "Add a short conclusion: who Business Bay is best for + 3 bullet takeaways + quick next-step suggestions.",
            "Why it matters": "Improves readability and strengthens AI summary extraction + user clarity.",
            "Source (competitor)": " / ".join(sorted(comp_sources["Conclusion"])) or "Competitors"
        })

    # 3) FAQs (missing OR weaker)
    if max_faq > 0 and (bayut_faq == 0 or bayut_faq < max_faq):
        target = max(6, min(10, max_faq + 2))
        source_names = " / ".join(sorted(best_faq_sources)) if best_faq_sources else "Competitors"
        rows.append({
            "Missing section in Bayut": "FAQs",
            "What to add (recommendation)": f"Add/expand FAQs to {target} items with direct answers (commute, parking, noise, family-friendly, rent range, best towers, metro access).",
            "Why it matters": "Captures long-tail queries + boosts AEO and supports FAQ schema eligibility.",
            "Source (competitor)": source_names
        })

    # 4) Map
    if comp_has_map and not bayut_has_map:
        rows.append({
            "Missing section in Bayut": "Map / Location visuals",
            "What to add (recommendation)": "Add a small map embed + ‘key landmarks in minutes’ bullets (metro, Downtown, DIFC, Dubai Mall).",
            "Why it matters": "Adds geo clarity + improves engagement and trust signals.",
            "Source (competitor)": " / ".join(sorted(comp_sources["Map / Location visuals"])) or "Competitors"
        })

    # 5) Nearby/Alternatives
    if comp_has_nearby and not bayut_has_nearby:
        rows.append({
            "Missing section in Bayut": "Nearby Communities / Alternatives",
            "What to add (recommendation)": "Add nearby/alternative areas: Downtown, DIFC, Al Quoz, Jumeirah (when to pick each).",
            "Why it matters": "Improves topical coverage and matches ‘alternative areas’ search intent.",
            "Source (competitor)": " / ".join(sorted(comp_sources["Nearby Communities / Alternatives"])) or "Competitors"
        })

    return rows


# ---------------------------
# NEW POST mode (simple, same style)
# ---------------------------

def new_post_strategy(bayut_title: str, competitors: list[dict]) -> dict:
    # Suggest the same core sections based on what competitors include
    # (Bayut has only title in NEW POST mode)
    fake_bayut = {"h2": [], "h3": [], "raw_text": "", "has_map": False, "has_faq_signal": False, "question_like_count": 0}
    recs = update_gaps(fake_bayut, competitors)

    # In NEW POST, rename column to “Section to include”
    out = []
    for r in recs:
        out.append({
            "Section to include": r["Missing section in Bayut"],
            "What to add": r["What to add (recommendation)"],
            "Why it matters": r["Why it matters"],
            "Source (competitor)": r["Source (competitor)"],
        })

    return {"recommended_sections": out}
