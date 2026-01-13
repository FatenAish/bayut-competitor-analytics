import re


def _normalize(text: str) -> str:
    return (text or "").lower().strip()


def _infer_keywords_from_title(title: str) -> dict:
    """
    Infer focus + long-tail keywords from the title
    """
    t = _normalize(title)
    words = [w for w in re.findall(r"\b\w+\b", t) if len(w) > 3]

    focus_kw = " ".join(words[:3]) if len(words) >= 3 else t

    long_tails = set()
    if "pros" in t or "cons" in t:
        long_tails.add(f"pros and cons of {focus_kw}")
    if "living" in t:
        long_tails.add(f"living in {focus_kw}")
    if "business bay" in t:
        long_tails.update({
            "business bay rent",
            "business bay lifestyle",
            "business bay vs dubai marina",
            "business bay vs downtown dubai",
            "business bay vs jlt",
        })

    return {
        "focus_kw": focus_kw,
        "long_tail_kws": list(long_tails)
    }


def compliance_analysis(bayut: dict, competitors: list[dict], title: str) -> list[dict]:
    """
    Returns rows suitable for a comparison table
    """
    kw_data = _infer_keywords_from_title(title)
    focus_kw = kw_data["focus_kw"]
    long_tails = kw_data["long_tail_kws"]

    results = []

    def check(page: dict):
        text = page["parsed"]["raw_text"].lower()
        h2 = " ".join(page["parsed"]["h2"]).lower()

        return {
            "word_count": page["parsed"]["word_count"],
            "h2_count": len(page["parsed"]["h2"]),
            "has_summary": any(k in text[:500] for k in ["summary", "in short", "quick"]),
            "has_faq": page["parsed"]["has_faq_signal"],
            "has_comparison": any(v in h2 for v in ["vs", "comparison", "compare"]),
            "has_tables": page["parsed"]["table_count"] > 0,
            "internal_links": page["parsed"]["internal_links"],
            "freshness": any(y in text for y in ["2024", "2025", "updated"]),
            "focus_kw_usage": focus_kw in text,
            "long_tail_usage": sum(1 for lt in long_tails if lt in text),
        }

    bayut_metrics = check(bayut)

    best_comp = max(
        (check(c) for c in competitors),
        key=lambda x: (
            x["long_tail_usage"],
            x["has_comparison"],
            x["has_tables"],
            x["word_count"]
        )
    )

    for factor in [
        "word_count",
        "h2_count",
        "has_summary",
        "has_faq",
        "has_comparison",
        "has_tables",
        "internal_links",
        "freshness",
        "focus_kw_usage",
        "long_tail_usage",
    ]:
        results.append({
            "Factor": factor.replace("_", " ").title(),
            "Bayut": bayut_metrics[factor],
            "Best competitor": best_comp[factor],
            "Gap": (
                "Yes" if bayut_metrics[factor] < best_comp[factor]
                else "No"
            ),
            "Recommendation": (
                f"Improve {factor.replace('_', ' ')} to match competitors"
                if bayut_metrics[factor] < best_comp[factor]
                else "OK"
            )
        })

    return results
