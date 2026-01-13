import re


def ai_readiness_analysis(parsed: dict) -> dict:
    """
    Heuristic analysis for:
    - AI Overviews
    - AEO (Answer Engine Optimization)
    - GEO (Generative Engine Optimization)
    """

    text = (parsed.get("raw_text") or "").lower()
    h2 = parsed.get("h2", [])
    word_count = parsed.get("word_count", 0)

    strengths = []
    gaps = []

    # --- Direct answer signal ---
    if re.search(r"\b(is|are|means|refers to)\b", text[:1200]):
        strengths.append("Has a direct-answer style introduction")
    else:
        gaps.append("Add a clear 2–3 sentence definition near the top")

    # --- Question-based structure (AEO) ---
    if any("?" in h for h in h2) or "faq" in " ".join(h2).lower():
        strengths.append("Uses question-style headings (FAQ / AEO friendly)")
    else:
        gaps.append("Add FAQ or question-based headings")

    # --- Scannability ---
    if re.search(r"•|- |\d+\.", text):
        strengths.append("Uses lists or bullet points")
    else:
        gaps.append("Add bullet points or numbered lists")

    # --- Entity coverage ---
    entity_keywords = [
        "rent", "price", "cost",
        "metro", "traffic", "commute",
        "schools", "parks", "restaurants",
        "location", "area", "neighborhood"
    ]

    entity_hits = sum(1 for k in entity_keywords if k in text)
    if entity_hits >= 3:
        strengths.append("Covers important local entities")
    else:
        gaps.append("Add sections on cost, commute, amenities, and lifestyle")

    # --- Content depth ---
    if word_count >= 1000:
        strengths.append("Strong content depth for AI summarization")
    else:
        gaps.append("Increase content depth (1000+ words recommended)")

    # --- Freshness / trust ---
    if re.search(r"\b(2024|2025|updated|last updated)\b", text):
        strengths.append("Shows freshness or update signal")
    else:
        gaps.append("Add a visible 'last updated' date")

    score_hint = max(0, 100 - len(gaps) * 12)

    return {
        "ai_strengths": strengths,
        "ai_gaps": gaps,
        "ai_score_hint": score_hint,
    }
