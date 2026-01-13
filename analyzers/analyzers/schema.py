def schema_analysis(parsed: dict) -> dict:
    """
    Analyze structured data (schema / JSON-LD)
    """
    existing = parsed.get("schema_types", []) or []

    issues = []
    recommendations = []

    if not existing:
        issues.append("No structured data (schema) found")
        recommendations.append("Add JSON-LD schema to improve eligibility for rich results")

    # Recommended schema for editorial / guides
    if "Article" not in existing and "BlogPosting" not in existing:
        recommendations.append("Add Article or BlogPosting schema")

    if "FAQPage" not in existing:
        recommendations.append("Add FAQPage schema for Q&A sections")

    if "BreadcrumbList" not in existing:
        recommendations.append("Add BreadcrumbList schema for better SERP display")

    return {
        "existing_schema": existing,
        "schema_count": len(existing),
        "issues": issues,
        "recommendations": recommendations,
    }
