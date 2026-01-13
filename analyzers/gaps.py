import re
from difflib import SequenceMatcher
from urllib.parse import urlparse


# =========================
# Semantic detectors
# =========================

SEMANTIC_SECTIONS = {
    "comparison": [
        "comparison", "compare", "vs", "versus",
        "other areas", "other neighborhoods", "other neighbourhoods",
        "alternatives", "nearby areas"
    ],
    "faq": ["faq", "faqs", "frequently asked"],
    "conclusion": ["conclusion", "final thoughts", "summary", "wrap up"]
}


# =========================
# Helpers
# =========================

def _brand(url: str) -> str:
    try:
        host = urlparse(url).netloc.replace("www.", "")
        return host.split(".")[0].replace("-", " ").title()
    except Exception:
        return "Competitor"


def _norm(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def _is_semantic(title: str, key: str) -> bool:
    t = _norm(title)
    return any(k in t for k in SEMANTIC_SECTIONS[key])


def _tokenize(text: str) -> set:
    text = (text or "").lower()
    words = re.findall(r"[a-z]{4,}", text)
    stop = {"this", "that", "with", "from", "have", "will", "your", "about", "also"}
    return set(w for w in words if w not in stop)


# =========================
# Main logic
# =========================

def update_gaps(bayut_parsed: dict, competitors: list[dict]) -> list[dict]:
    rows = []

    bayut_headers = bayut_parsed.get("h2", []) + bayut_parsed.get("h3", [])
    bayut_text = bayut_parsed.get("raw_text", "")

    # ---- Semantic presence in Bayut
    bayut_has = {
        "comparison": any(_is_semantic(h, "comparison") for h in bayut_headers),
        "faq": bool(bayut_parsed.get("faq_questions")),
        "conclusion": any(_is_semantic(h, "conclusion") for h in bayut_headers),
    }

    # ---- Track competitors
    found = {
        "comparison": [],
        "faq": [],
        "conclusion": [],
    }

    # =========================
    # 1) SEMANTIC SECTIONS
    # =========================
    for c in competitors:
        parsed = c["parsed"]
        source = _brand(c["url"])
        headers = parsed.get("h2", []) + parsed.get("h3", []) + parsed.get("h4", [])
        text = parsed.get("raw_text", "")

        if not bayut_has["comparison"] and any(_is_semantic(h, "comparison") for h in headers):
            areas = sorted({
                a for a in ["Downtown Dubai", "Dubai Marina", "JLT", "DIFC", "Jumeirah"]
                if a.lower() in text.lower()
            })
            found["comparison"].append((source, areas))

        if not bayut_has["faq"] and parsed.get("faq_questions"):
            found["faq"].append((source, parsed["faq_questions"][:8]))

        if not bayut_has["conclusion"] and any(_is_semantic(h, "conclusion") for h in headers):
            found["conclusion"].append(source)

    # ---- Emit semantic rows
    if found["comparison"]:
        src, areas = found["comparison"][0]
        rows.append({
            "Missing section in Bayut": "Comparison with Other Areas",
            "What competitors have": f"Area-level comparison ({', '.join(areas)})" if areas else "Area-level comparison",
            "Why it matters": "Decision-support content present on competitors.",
            "Source (competitor)": src
        })

    if found["faq"]:
        src, qs = found["faq"][0]
        rows.append({
            "Missing section in Bayut": "FAQs",
            "What competitors have": "; ".join(qs),
            "Why it matters": "Direct-question coverage difference.",
            "Source (competitor)": src
        })

    if found["conclusion"]:
        rows.append({
            "Missing section in Bayut": "Conclusion",
            "What competitors have": "Dedicated wrap-up / final summary section.",
            "Why it matters": "Structural completeness difference.",
            "Source (competitor)": found["conclusion"][0]
        })

    # =========================
    # 2) CONTENT GAPS (existing headers)
    # =========================
    for c in competitors:
        parsed = c["parsed"]
        source = _brand(c["url"])

        comp_headers = parsed.get("h2", []) + parsed.get("h3", [])
        comp_text = parsed.get("raw_text", "")

        for bh in bayut_headers:
            if any(_similar(bh, ch) > 0.9 for ch in comp_headers):
                missing_terms = sorted(_tokenize(comp_text) - _tokenize(bayut_text))
                if len(missing_terms) >= 5:
                    rows.append({
                        "Missing section in Bayut": f"{bh} (content gap)",
                        "What competitors have": ", ".join(missing_terms[:8]),
                        "Why it matters": "Competitors cover additional details within the same section.",
                        "Source (competitor)": source
                    })

    # ---- De-duplicate
    unique = []
    seen = set()
    for r in rows:
        key = (_norm(r["Missing section in Bayut"]), _norm(r["Source (competitor)"]))
        if key not in seen:
            seen.add(key)
            unique.append(r)

    return unique


def new_post_strategy(bayut_title: str, competitors: list[dict]) -> dict:
    return {"recommended_sections": []}
