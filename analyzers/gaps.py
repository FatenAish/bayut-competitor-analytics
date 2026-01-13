def _norm(text: str) -> str:
    return " ".join((text or "").lower().split())


# ------------------------------------------------
# UPDATE MODE: compare Bayut vs competitors
# ------------------------------------------------
def update_gaps(bayut_parsed: dict, competitors: list[dict]) -> list[dict]:
    """
    Return sections competitors have that Bayut is missing
    with source URLs
    """

    bayut_sections = set(
        _norm(h)
        for h in (bayut_parsed.get("h2", []) + bayut_parsed.get("h3", []))
        if _norm(h)
    )

    competitor_sections = {}

    for comp in competitors:
        url = comp["url"]
        parsed = comp["parsed"]

        for h in parsed.get("h2", []) + parsed.get("h3", []):
            key = _norm(h)
            if not key:
                continue
            competitor_sections.setdefault(key, set()).add(url)

    missing = []
    for section, sources in competitor_sections.items():
        if section not in bayut_sections:
            missing.append({
                "missing_section": section,
                "sources": sorted(list(sources))
            })

    return missing


# ------------------------------------------------
# NEW POST MODE: what to include to beat competitors
# ------------------------------------------------
def new_post_strategy(bayut_title: str, competitors: list[dict]) -> dict:
    """
    Build recommended sections for a new Bayut article
    """

    section_map = {}

    for comp in competitors:
        url = comp["url"]
        parsed = comp["parsed"]

        for h in parsed.get("h2", []) + parsed.get("h3", []):
            key = _norm(h)
            if not key:
                continue
            section_map.setdefault(key, set()).add(url)

    ranked = sorted(
        section_map.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )

    recommendations = []
    for section, sources in ranked:
        recommendations.append({
            "recommended_section": section,
            "covered_by_competitors": len(sources),
            "sources": sorted(list(sources))
        })

    return {
        "bayut_title": bayut_title,
        "recommended_sections": recommendations
    }
