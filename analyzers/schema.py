def schema_analysis(parsed: dict) -> dict:
    existing = parsed.get("schema_types", [])

    issues = []
    recommendations = []

    if not existing:
        issues.append("No structured data (schema) detected")
        recommendations.append("Add JSON-LD schema to improve eligibility for rich results.")

    if "Article" not in existing and "BlogPosting" not in existing:
        recommendations.append("Add Article or BlogPosting schema.")

    if "FAQPage" not in existing:
        recommendations.append("Add FAQPage schema for Q&A and AEO.")

    if "BreadcrumbList" not in existing:
        recommendations.append("Add BreadcrumbList schema for better SERP display.")

    return {
        "existing_schema": existing,
        "schema_count": len(existing),
        "issues": issues,
        "recommendations": recommendations,
    }
