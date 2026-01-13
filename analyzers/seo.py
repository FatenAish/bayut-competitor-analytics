def seo_analysis(parsed: dict) -> dict:
    issues = []
    recommendations = []

    title = parsed.get("title", "")
    meta_desc = parsed.get("meta_description", "")
    h1_count = len(parsed.get("h1", []))
    h2_count = len(parsed.get("h2", []))
    word_count = parsed.get("word_count", 0)

    if not title:
        issues.append("Missing title tag")
        recommendations.append("Add an SEO-friendly title including the main keyword.")
    elif len(title) > 60:
        issues.append("Title too long")
        recommendations.append("Shorten the title to under 60 characters.")

    if not meta_desc:
        issues.append("Missing meta description")
        recommendations.append("Add a 140–160 character meta description.")
    elif len(meta_desc) > 160:
        issues.append("Meta description too long")
        recommendations.append("Shorten meta description to under 160 characters.")

    if h1_count == 0:
        issues.append("Missing H1")
        recommendations.append("Add a single H1 heading.")
    elif h1_count > 1:
        issues.append("Multiple H1s")
        recommendations.append("Use only one H1.")

    if word_count < 800:
        issues.append("Thin content")
        recommendations.append("Increase content depth to at least 800 words.")

    if h2_count < 3:
        issues.append("Weak content structure")
        recommendations.append("Add more H2 sections (pros/cons, costs, location, etc.).")

    return {
        "issues": issues,
        "recommendations": recommendations,
        "word_count": word_count,
        "h1_count": h1_count,
        "h2_count": h2_count,
    }
