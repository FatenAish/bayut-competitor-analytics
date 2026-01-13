def seo_analysis(parsed: dict) -> dict:
    """
    Perform basic on-page SEO analysis
    """
    issues = []
    recommendations = []

    title = parsed.get("title", "")
    meta_description = parsed.get("meta_description", "")
    h1 = parsed.get("h1", [])
    h2 = parsed.get("h2", [])
    word_count = parsed.get("word_count", 0)

    # ---- Title ----
    if not title:
        issues.append("Missing title tag")
        recommendations.append("Add a clear, keyword-focused title")
    elif len(title) > 60:
        issues.append("Title is too long")
        recommendations.append("Shorten title to under 60 characters")

    # ---- Meta description ----
    if not meta_description:
        issues.append("Missing meta description")
        recommendations.append("Add a compelling meta description (140–160 chars)")
    elif len(meta_description) > 160:
        issues.append("Meta description is too long")
        recommendations.append("Shorten meta description to under 160 characters")

    # ---- H1 ----
    if len(h1) == 0:
        issues.append("Missing H1")
        recommendations.append("Add a single clear H1")
    elif len(h1) > 1:
        issues.append("Multiple H1s found")
        recommendations.append("Use only one H1")

    # ---- Content depth ----
    if word_count < 800:
        issues.append("Low content depth")
        recommendations.append("Increase content depth to 800+ words")

    # ---- Structure ----
    if len(h2) < 3:
        issues.append("Weak heading structure")
        recommendations.append("Add more descriptive H2 sections")

    return {
        "title_length": len(title),
        "meta_description_length": len(meta_description),
        "h1_count": len(h1),
        "h2_count": len(h2),
        "word_count": word_count,
        "issues": issues,
        "recommendations": recommendations,
    }
