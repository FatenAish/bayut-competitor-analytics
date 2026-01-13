import re
from collections import defaultdict


# --------------------------------------------------
# HELPERS
# --------------------------------------------------
def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def contains_any(text: str, keywords: list[str]) -> bool:
    t = normalize(text)
    return any(k in t for k in keywords)


# --------------------------------------------------
# MAIN GAP ANALYSIS
# --------------------------------------------------
def update_gaps(bayut_parsed: dict, competitors: list[dict]) -> list[dict]:
    results = []

    bayut_h2 = [normalize(h) for h in bayut_parsed.get("h2", [])]
    bayut_h3 = [normalize(h) for h in bayut_parsed.get("h3", [])]

    # --------------------------------------------------
    # SEMANTIC SECTIONS (ALWAYS STANDALONE)
    # --------------------------------------------------
    semantic_sections = {
        "FAQs": {
            "keywords": ["faq", "frequently asked", "questions"],
            "summary": set(),
            "sources": set()
        },
        "Conclusion": {
            "keywords": ["conclusion", "final thoughts", "summary"],
            "summary": set(),
            "sources": set()
        },
        "Comparison with Other Dubai Neighborhoods": {
            "keywords": ["comparison", "compare", "other dubai", "neighborhood"],
            "areas": set(),
            "sources": set()
        }
    }

    # --------------------------------------------------
    # CONTENT GAP SECTIONS (ONLY IF BAYUT HAS HEADER)
    # --------------------------------------------------
    content_gap_sections = {
        "Pros of Living in Business Bay": {
            "keywords": ["pros"],
            "terms": set(),
            "sources": set()
        },
        "Cons of Living in Business Bay": {
            "keywords": ["cons"],
            "terms": set(),
            "sources": set()
        }
    }

    # --------------------------------------------------
    # SCAN COMPETITORS
    # --------------------------------------------------
    for c in competitors:
        parsed = c["parsed"]
        source = c["url"]

        h2 = parsed.get("h2", [])
        h3 = parsed.get("h3", [])
        text = parsed.get("raw_text", "")

        # ---------- SEMANTIC ----------
        for name, cfg in semantic_sections.items():
            for h in h2 + h3:
                if contains_any(h, cfg["keywords"]):
                    cfg["sources"].add(source)

                    # FAQ → collect question intent
                    if name == "FAQs":
                        questions = re.findall(r"\b(what|where|how|is|are|can)\b.{0,60}\?", text, re.I)
                        for q in questions[:5]:
                            cfg["summary"].add(q.strip())

                    # Conclusion → just presence
                    if name == "Conclusion":
                        cfg["summary"].add("Dedicated wrap-up / final summary section.")

                    # Comparison → collect areas
                    if name == "Comparison with Other Dubai Neighborhoods":
                        areas = re.findall(
                            r"(downtown dubai|dubai marina|jlt|difc|business bay)",
                            text,
                            re.I
                        )
                        for a in areas:
                            cfg["areas"].add(a.title())

        # ---------- CONTENT GAP ----------
        for name, cfg in content_gap_sections.items():
            if any(k in " ".join(bayut_h2 + bayut_h3) for k in cfg["keywords"]):
                words = re.findall(r"\b[a-z]{6,}\b", text.lower())
                for w in words[:30]:
                    cfg["terms"].add(w)
                cfg["sources"].add(source)

    # --------------------------------------------------
    # BUILD OUTPUT — SEMANTIC FIRST
    # --------------------------------------------------
    for name, cfg in semantic_sections.items():
        if not any(k in " ".join(bayut_h2 + bayut_h3) for k in cfg["keywords"]) and cfg["sources"]:
            if name == "Comparison with Other Dubai Neighborhoods":
                what = ", ".join(sorted(cfg["areas"])) or "Area-level comparison across Dubai neighborhoods"
            else:
                what = "; ".join(list(cfg["summary"])[:2])

            results.append({
                "Missing section in Bayut": name,
                "What competitors have": what,
                "Why it matters": "Structural or semantic coverage difference compared to competitors.",
                "Source (competitors)": ", ".join(sorted(cfg["sources"]))
            })

    # --------------------------------------------------
    # BUILD OUTPUT — CONTENT GAPS
    # --------------------------------------------------
    for name, cfg in content_gap_sections.items():
        if cfg["sources"]:
            results.append({
                "Missing section in Bayut": f"{name} (content gap)",
                "What competitors have": ", ".join(sorted(cfg["terms"])[:12]),
                "Why it matters": "Detail coverage difference within the same section.",
                "Source (competitors)": ", ".join(sorted(cfg["sources"]))
            })

    return results
