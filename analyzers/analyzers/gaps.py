def _normalize(text: str) -> str:
    return " ".join((text or "").lower().split())


# -------------------------------------------------
# UPDATE MODE: What is missing on Bayut vs competitors
# -------------------------------------------------
def update_gaps(bayut_parsed: dict, competitors: list[dict]) -> list[dict]:
    """
    Compare Bayut headings vs competitor headings
    Return missing sections with sources
    """

    bayut_h = set(
        _normalize(h)
        for h in (bayut_parsed.get("h2", []) + bayut_parsed.get("h3", []))
    )

    competitor_map = {}

    for comp in competitors:
        url = comp["url"]
        parsed = comp["parsed"]

        for h in parsed.get("h2", []) + parsed.get("h3", []):
            key = _normalize(h)
            if not key:
                continue
            competitor_map.setdefault(key, set()).add(url)

    missing = []
    for heading, sources in competitor_map.items():
        if heading not in bayut_h:
            missing.append({
                "missing_section": heading,
                "sources": sorted(list(sources))
            })

    return missing


# -------------------------------------------------
# NEW POST MODE: What to add to beat competitors
# -------------------------------------------------
def new_post_strategy(bayut_title: str, competitors: list[dict]) -> dict:
    """
    Build a strategy for a new Bayut article
    based on competitor coverage
    """

    section_map = {}

    for comp in competitors:
        url = comp["url"]
        parsed = comp["parsed"]

        for h in parsed.get("h2", []) + parsed.get("h3", []):
            key = _normalize(h)
            if not key:
                continue
            section_map.setdefault(key, set()).add(url)

    # Rank sections by how many competitors cover them
    ranked_sections = sorted(
        section_map.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )

    recommendations = []
    for section, sources in ranked_sections:
        recommendations.append({
            "recommended_section": section,
            "competitor_count": len(sources),
            "sources": sorted(list(sources))
        })

    return {
        "bayut_title": bayut_title,
        "recommended_sections": recommendations
    }
