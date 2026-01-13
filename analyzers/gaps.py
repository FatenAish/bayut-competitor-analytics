def normalize_header(h: str) -> str:
    return " ".join(h.lower().strip().split())


def update_gaps(bayut_parsed: dict, competitors: list[dict]) -> list[dict]:
    bayut_headers = {
        normalize_header(h)
        for h in (bayut_parsed.get("h2", []) + bayut_parsed.get("h3", []))
    }

    rows = []

    for c in competitors:
        comp_headers = {
            normalize_header(h)
            for h in (c["parsed"].get("h2", []) + c["parsed"].get("h3", []))
        }

        missing = comp_headers - bayut_headers

        for h in missing:
            rows.append({
                "Missing section title": h.title(),
                "Source": c["url"]
            })

    # remove duplicates (same title from multiple competitors)
    unique = {}
    for r in rows:
        key = r["Missing section title"]
        unique.setdefault(key, []).append(r["Source"])

    return [
        {
            "Missing section title": k,
            "Sources": ", ".join(sorted(set(v)))
        }
        for k, v in unique.items()
    ]


def new_post_strategy(bayut_title: str, competitors: list[dict]) -> dict:
    headers = {}

    for c in competitors:
        for h in c["parsed"].get("h2", []) + c["parsed"].get("h3", []):
            key = normalize_header(h)
            headers.setdefault(key, []).append(c["url"])

    return {
        "recommended_sections": [
            {
                "Recommended section title": k.title(),
                "Sources": ", ".join(sorted(set(v)))
            }
            for k, v in headers.items()
        ]
    }
