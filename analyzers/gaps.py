import re
from collections import defaultdict


# -----------------------------
# helpers
# -----------------------------
def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _is_semantic(header: str, keyword: str) -> bool:
    h = _norm(header)
    return keyword in h


def _extract_headers(parsed: dict):
    return parsed.get("h2", []) + parsed.get("h3", [])


def _has_section(headers, keyword):
    return any(_is_semantic(h, keyword) for h in headers)


def _extract_faq_questions(parsed: dict):
    questions = []
    for h in parsed.get("h3", []) + parsed.get("h4", []):
        if h.strip().endswith("?"):
            questions.append(h.strip())
    return questions


# -----------------------------
# UPDATE MODE
# -----------------------------
def update_gaps(bayut_parsed: dict, competitors: list[dict]) -> list[dict]:
    """
    Compare Bayut vs ALL competitors.
    - Missing sections → shown once, aggregated
    - Content gaps → only when header exists in Bayut
    """

    bayut_headers = _extract_headers(bayut_parsed)
    bayut_text = bayut_parsed.get("raw_text", "").lower()

    bayut_has = {
        "faq": _has_section(bayut_headers, "faq"),
        "comparison": _has_section(bayut_headers, "comparison"),
        "conclusion": _has_section(bayut_headers, "conclusion"),
        "pros": _has_section(bayut_headers, "pros"),
        "cons": _has_section(bayut_headers, "cons"),
    }

    found = {
        "faq": {"sources": set(), "details": set()},
        "comparison": {"sources": set(), "details": set()},
        "conclusion": {"sources": set()},
        "pros_gap": {"sources": set(), "details": set()},
        "cons_gap": {"sources": set(), "details": set()},
    }

    for c in competitors:
        parsed = c["parsed"]
        source = c["url"]
        headers = _extract_headers(parsed)
        text = parsed.get("raw_text", "").lower()

        # ---------------- FAQ ----------------
        if not bayut_has["faq"]:
            qs = _extract_faq_questions(parsed)
            if qs:
                found["faq"]["sources"].add(source)
                for q in qs[:10]:
                    found["faq"]["details"].add(q)

        # ---------------- COMPARISON ----------------
        if not bayut_has["comparison"]:
            if _has_section(headers, "comparison"):
                found["comparison"]["sources"].add(source)
                for area in [
                    "downtown dubai",
                    "dubai marina",
                    "jlt",
                    "difc",
                    "business bay",
                ]:
                    if area in text:
                        found["comparison"]["details"].add(area.title())

        # ---------------- CONCLUSION ----------------
        if not bayut_has["conclusion"]:
            if _has_section(headers, "conclusion"):
                found["conclusion"]["sources"].add(source)

        # ---------------- PROS CONTENT GAP ----------------
        if bayut_has["pros"] and _has_section(headers, "pros"):
            competitor_terms = set(re.findall(r"\b[a-z]{6,}\b", text))
            bayut_terms = set(re.findall(r"\b[a-z]{6,}\b", bayut_text))
            diff = competitor_terms - bayut_terms
            if diff:
                found["pros_gap"]["sources"].add(source)
                for w in list(diff)[:12]:
                    found["pros_gap"]["details"].add(w)

        # ---------------- CONS CONTENT GAP ----------------
        if bayut_has["cons"] and _has_section(headers, "cons"):
            competitor_terms = set(re.findall(r"\b[a-z]{6,}\b", text))
            bayut_terms = set(re.findall(r"\b[a-z]{6,}\b", bayut_text))
            diff = competitor_terms - bayut_terms
            if diff:
                found["cons_gap"]["sources"].add(source)
                for w in list(diff)[:12]:
                    found["cons_gap"]["details"].add(w)

    # ---------------- OUTPUT ----------------
    rows = []

    if found["comparison"]["sources"]:
        rows.append({
            "Missing section in Bayut": "Comparison with Other Dubai Neighborhoods",
            "What competitors have": ", ".join(sorted(found["comparison"]["details"])),
            "Why it matters": "Area-level comparison present on competitors.",
            "Source (competitor)": ", ".join(sorted(found["comparison"]["sources"])),
        })

    if found["faq"]["sources"]:
        rows.append({
            "Missing section in Bayut": "FAQs",
            "What competitors have": "; ".join(sorted(found["faq"]["details"])),
            "Why it matters": "Direct-question coverage difference.",
            "Source (competitor)": ", ".join(sorted(found["faq"]["sources"])),
        })

    if found["conclusion"]["sources"]:
        rows.append({
            "Missing section in Bayut": "Conclusion",
            "What competitors have": "Dedicated wrap-up / final summary section.",
            "Why it matters": "Structural completeness difference.",
            "Source (competitor)": ", ".join(sorted(found["conclusion"]["sources"])),
        })

    if found["pros_gap"]["sources"]:
        rows.append({
            "Missing section in Bayut": "Pros of Living in Business Bay (content gap)",
            "What competitors have": ", ".join(sorted(found["pros_gap"]["details"])),
            "Why it matters": "Detail coverage difference within the same section.",
            "Source (competitor)": ", ".join(sorted(found["pros_gap"]["sources"])),
        })

    if found["cons_gap"]["sources"]:
        rows.append({
            "Missing section in Bayut": "Cons of Living in Business Bay (content gap)",
            "What competitors have": ", ".join(sorted(found["cons_gap"]["details"])),
            "Why it matters": "Detail coverage difference within the same section.",
            "Source (competitor)": ", ".join(sorted(found["cons_gap"]["sources"])),
        })

    return rows


# -----------------------------
# NEW POST MODE
# -----------------------------
def new_post_strategy(title: str, competitors: list[dict]) -> dict:
    """
    Used ONLY for NEW POST mode.
    Lists structural sections competitors use.
    """

    sections = defaultdict(set)

    for c in competitors:
        parsed = c["parsed"]
        for h in _extract_headers(parsed):
            sections[h.strip()].add(c["url"])

    output = []
    for h, sources in sections.items():
        output.append({
            "Section title": h,
            "Appears on competitors": ", ".join(sorted(sources))
        })

    return {"recommended_sections": output}
