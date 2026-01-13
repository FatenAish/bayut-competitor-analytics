import re


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def contains_any(text: str, keywords: list[str]) -> bool:
    t = normalize(text)
    return any(k in t for k in keywords)


def update_gaps(bayut_parsed: dict, competitors: list[dict]) -> list[dict]:
    results = []

    bayut_headers = normalize(" ".join(
        bayut_parsed.get("h2", []) + bayut_parsed.get("h3", [])
    ))

    # Semantic standalone sections
    semantic_sections = {
        "FAQs": ["faq", "frequently asked", "questions"],
        "Conclusion": ["conclusion", "final thoughts", "summary"],
        "Comparison with Other Dubai Neighborhoods": [
            "comparison", "compare", "other dubai", "neighborhood"
        ],
    }

    # Content gap sections (only if Bayut already has them)
    content_sections = {
        "Pros of Living in Business Bay": ["pros"],
        "Cons of Living in Business Bay": ["cons"],
    }

    for c in competitors:
        parsed = c["parsed"]
        source = c["url"]

        comp_headers = parsed.get("h2", []) + parsed.get("h3", [])
        comp_text = parsed.get("raw_text", "").lower()

        comp_header_text = normalize(" ".join(comp_headers))

        # ---------- SEMANTIC SECTIONS ----------
        for section, keywords in semantic_sections.items():
            bayut_has = contains_any(bayut_headers, keywords)
            comp_has = contains_any(comp_header_text, keywords)

            if comp_has and not bayut_has:
                if section == "Comparison with Other Dubai Neighborhoods":
                    areas = re.findall(
                        r"(downtown dubai|dubai marina|jlt|difc|business bay)",
                        comp_text,
                        re.I
                    )
                    areas = sorted(set(a.title() for a in areas))
                    what = ", ".join(areas) if areas else "Area-level comparison"
                elif section == "FAQs":
                    questions = re.findall(
                        r"\b(what|where|how|is|are|can)\b.{0,60}\?",
                        comp_text,
                        re.I
                    )
                    what = "; ".join(q.strip() for q in questions[:3])
                else:
                    what = "Dedicated wrap-up / final summary section."

                results.append({
                    "Missing section in Bayut": section,
                    "What competitor has": what,
                    "Source (competitor)": source
                })

        # ---------- CONTENT GAPS ----------
        for section, keywords in content_sections.items():
            bayut_has = contains_any(bayut_headers, keywords)
            comp_has = contains_any(comp_header_text, keywords)

            if bayut_has and comp_has:
                words = re.findall(r"\b[a-z]{6,}\b", comp_text)
                words = sorted(set(words))[:12]

                if words:
                    results.append({
                        "Missing section in Bayut": f"{section} (content gap)",
                        "What competitor has": ", ".join(words),
                        "Source (competitor)": source
                    })

    return results
