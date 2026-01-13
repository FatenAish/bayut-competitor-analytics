from typing import List, Dict, Any


def _get_parsed(page: Dict[str, Any]) -> Dict[str, Any]:
    return page.get("parsed", {}) or {}


def _metrics(page: Dict[str, Any]) -> Dict[str, Any]:
    p = _get_parsed(page)
    return {
        "word_count": int(p.get("word_count", 0) or 0),
        "h1_count": len(p.get("h1", []) or []),
        "h2_count": len(p.get("h2", []) or []),
        "h3_count": len(p.get("h3", []) or []),
        "has_faq": bool(p.get("has_faq_signal", False)),
        "table_count": int(p.get("table_count", 0) or 0),
        "image_count": int(p.get("image_count", 0) or 0),
        "video_count": int(p.get("video_count", 0) or 0),
        "has_map": bool(p.get("has_map_signal", False)),
    }


def compliance_analysis(bayut: Dict[str, Any], competitors: List[Dict[str, Any]], title: str) -> List[Dict[str, str]]:
    bay = _metrics(bayut)

    # best competitor = highest word count
    best = None
    best_m = None
    for c in competitors:
        m = _metrics(c)
        if best_m is None or m["word_count"] > best_m["word_count"]:
            best, best_m = c, m

    if best is None:
        return []

    def row(check: str, b, c, rec: str) -> Dict[str, str]:
        return {"Check": check, "Bayut": str(b), "Best competitor": str(c), "Recommendation": rec}

    rows = [
        row("Word count", bay["word_count"], best_m["word_count"],
            "Increase depth only where competitors have meaningful sections (comparison, prices, FAQs, transport)."),
        row("H1 count", bay["h1_count"], best_m["h1_count"],
            "Keep exactly 1 H1."),
        row("H2 count", bay["h2_count"], best_m["h2_count"],
            "Add missing H2 sections competitors use (not CTAs/newsletters)."),
        row("H3 count", bay["h3_count"], best_m["h3_count"],
            "Use H3 for sub-points inside key sections (e.g., Downtown/Marina/JLT under comparisons)."),
        row("FAQ present", bay["has_faq"], best_m["has_faq"],
            "Add a short FAQ block if competitors have it (helps AEO)."),
        row("Tables", bay["table_count"], best_m["table_count"],
            "Add 1 simple table if competitor uses one (rent ranges, pros/cons, commute)."),
        row("Images", bay["image_count"], best_m["image_count"],
            "Match competitor’s visual support (few strong images > many)."),
        row("Video present", bay["video_count"], best_m["video_count"],
            "Optional: add a short video only if competitors use it AND it helps explain the area."),
        row("Map embed", bay["has_map"], best_m["has_map"],
            "If competitor embeds a map, add one map section (location + key landmarks)."),
    ]

    return rows
