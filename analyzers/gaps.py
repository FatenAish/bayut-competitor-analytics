import re
from collections import defaultdict


# -------------------------------
# helpers
# -------------------------------
def _normalize(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


def _has_section(headers, keyword):
    keyword = _normalize(keyword)
    return any(keyword in _normalize(h) for h in headers)


def _extract_faq_questions(parsed):
    questions = []
    for h in parsed.get("h3", []) + parsed.get("h4", []):
        if "?" in h:
            questions.append(h.strip())
    return questions


def _extract_areas(text):
    areas = [
        "business bay",
        "downtown dubai",
        "dubai marina",
        "jlt",
        "difc",
        "dubai creek harbour",
        "dubai hills estate",
    ]
    found = []
    for a in areas:
        if a in text:
            found.append(a.title())
    return found


# -------------------------------
# MAIN LOGIC
# -------------------------------
def update_gaps(bayut_parsed, competitors):
    """
    Returns:
    [
      {
        Missing section in Bayut,
        What competitors have,
        Why it matters,
        Source (competitor)
      }
    ]
    """

    # ---------------------------------
    # Bayut signals
    # ---------------------------------
    bayut_h3 = bayut_parsed.get("h3", [])
    bayut_h4 = bayut_parsed.get("h4", [])
    bayut_text = bayut_parsed.get("raw_text", "").lower()

    bayut_has = {
        "comparison": _has_section(bayut_h3, "comparison"),
        "faq": _has_section(bayut_h3, "faq"),
        "conclusion": _has_section(bayut_h3, "conclusion"),
        "pros": _has_section(bayut_h3, "pros"),
        "cons": _has_section(bayut_h3, "cons"),
    }

    # ---------------------------------
    # Aggregate competitor signals FIRST
    # ---------------------------------
    agg = {
        "comparison": {"areas": set(), "sources": set()},
        "faq": {"questions": set(), "sources": set()},
        "conclusion": {"sources": set()},
        "pros_gap": {"terms": set(), "sources": set()},
        "cons_gap": {"terms": set(), "sources": set()},
    }

    for c in competitors:
        parsed = c["parsed"]
        source = c["url"]

        h3 = parsed.get("h3", [])
        h4 = parsed.get("h4", [])
        text = parsed.get("raw_text", "").lower()

        # ---- Comparison (H3 only)
        if _has_section(h3, "comparison"):
            agg["comparison"]["sources"].add(source)
            for area in _extract_areas(text):
                agg["comparison"]["areas"].add(area)

        # ---- FAQ (questions)
        qs = _extract_faq_questions(parsed)
        if qs:
            agg["faq"]["sources"].add(source)
            for q in qs:
                agg["faq"]["questions"].add(q)

        # ---- Conclusion
        if _has_section(h3, "conclusion"):
            agg["conclusion"]["sources"].add(source)

        # ---- Pros content gap (H4 under Pros H3)
        if _has_section(h3, "pros"):
            for h in h4:
                if "pros" not in _normalize(h):
                    agg["pros_gap"]["terms"].add(h)
                    agg["pros_gap"]["sources"].add(source)

        # ---- Cons content gap (H4 under Cons H3)
        if _has_section(h3, "cons"):
            for h in h4:
                if "cons" not in _normalize(h):
                    agg["cons_gap"]["terms"].add(h)
                    agg["cons_gap"]["sources"].add(source)

    # ---------------------------------
    # FINAL OUTPUT (neutral, clean)
    # ---------------------------------
    rows = []

    # ---- Comparison
    if agg["comparison"]["areas"] and not bayut_has["comparison"]:
        rows.append({
            "Missing section in Bayut": "Comparison with Other Dubai Neighborhoods",
            "What competitors have": ", ".join(sorted(agg["comparison"]["areas"])),
            "Why it matters": "Area-level comparison present on competitors.",
            "Source (competitor)": ", ".join(sorted(agg["comparison"]["sources"])),
        })

    # ---- FAQ
    if agg["faq"]["questions"] and not bayut_has["faq"]:
        rows.append({
            "Missing section in Bayut": "FAQs",
            "What competitors have": "; ".join(sorted(list(agg["faq"]["questions"]))[:6]),
            "Why it matters": "Direct-question coverage difference.",
            "Source (competitor)": ", ".join(sorted(agg["faq"]["sources"])),
        })

    # ---- Conclusion
    if agg["conclusion"]["sources"] and not bayut_has["conclusion"]:
        rows.append({
            "Missing section in Bayut": "Conclusion",
            "What competitors have": "Dedicated wrap-up / final summary section.",
            "Why it matters": "Structural completeness difference.",
            "Source (competitor)": ", ".join(sorted(agg["conclusion"]["sources"])),
        })

    # ---- Pros content gap
    if bayut_has["pros"] and agg["pros_gap"]["terms"]:
        rows.append({
            "Missing section in Bayut": "Pros of Living in Business Bay (content gap)",
            "What competitors have": ", ".join(sorted(list(agg["pros_gap"]["terms"]))[:8]),
            "Why it matters": "Detail coverage difference within the same section.",
            "Source (competitor)": ", ".join(sorted(agg["pros_gap"]["sources"])),
        })

    # ---- Cons content gap
    if bayut_has["cons"] and agg["cons_gap"]["terms"]:
        rows.append({
            "Missing section in Bayut": "Cons of Living in Business Bay (content gap)",
            "What competitors have": ", ".join(sorted(list(agg["cons_gap"]["terms"]))[:8]),
            "Why it matters": "Detail coverage difference within the same section.",
            "Source (competitor)": ", ".join(sorted(agg["cons_gap"]["sources"])),
        })

    return rows
