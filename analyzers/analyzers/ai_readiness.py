import re


def ai_readiness_analysis(parsed: dict) -> dict:
    """
    Analyze readiness for:
    - AI Overviews
    - AEO (Answer Engine Optimization)
    - GEO (Generative Engine Optimization)

    Heuristic-based (open-source, no APIs)
    """

    text = parsed.get("raw_text", "")
    h1 = parsed.get("h1", [])
    h2 = parsed.get("h2", [])
    word_count = parsed.get("word_count", 0)

    missing = []
    strengths = []

    # ---- Direct answer signal ----
    # AI prefers short, clear explanations early
    intro_text = text[:1200].lower()
    if not re.search(r"\b(is|are|means|refers to)\b", intro_text):
        missing.append("No clear direct-answer definition near the top")
    else:
        strengths.append("Has a direct-answer style introduction")

    # ---- Question-based structure (AEO) ----
    has_questions = any("?" in h for h in h2) or "faq" in " ".join(h2).lower()
    if not has_questions:
        missing.append("No question-based headings (FAQs / AEO signals)")
    else:
        strengths.append("Uses question-style headings")

    # ---- Structured formatting ----
    if not re.search(r"•|- |\d+\.", text):
        missing.append("Content lacks scannable lists (bullets or numbered steps)")
    else:
        strengths.append("Uses lists for scannability")

    # ---- Entity clarity ----
    entity_keywords = [
        "price", "rent", "cost",
        "metro", "traffic", "commute",
        "schools", "parks", "restaurants",
        "location", "area", "neighborhood",
    ]

    entity_hits = sum(1 for k in entity_keywords if k in text.lower())
    if entity_hits < 3:
        missing.append("Weak entity coverage (costs, commute, amenities, etc.)")
    else:
        strengths.append("Covers key entities clearly")

    # ---- Content depth ----
    if word_count < 1000:
        missing.append("Content may be too shallow for AI summaries")
    else:
        strengths.append("Strong content depth for AI summarization")

    # ---- Freshness / trust ----
    if not re.search(r"\b(2024|2025|updated|last updated)\b", text.lower()):
        missing.append("No freshness signal (date or update mention)")
    else:
        strengths.append("Has freshness or update signal")

    return {
        "ai_strengths": strengths,
        "ai_gaps": missing,
        "ai_score_hint": max(0, 100 - (len(missing) * 12)),
    }
