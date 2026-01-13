def media_comparison(bayut: dict, competitors: list[dict]) -> list[dict]:
    rows = []

    def media_flags(page):
        return {
            "map": page["parsed"]["has_map"],
            "video": page["parsed"]["video_iframes"] > 0,
            "tables": page["parsed"]["table_count"],
            "images": page["parsed"]["img_count"],
            "alt_missing_pct": (
                round(
                    (page["parsed"]["img_missing_alt"] / page["parsed"]["img_count"]) * 100,
                    1
                ) if page["parsed"]["img_count"] else 0
            ),
            "gallery": page["parsed"]["has_gallery"],
        }

    bayut_m = media_flags(bayut)

    for comp in competitors:
        comp_m = media_flags(comp)

        for key in bayut_m:
            if bayut_m[key] < comp_m[key]:
                rows.append({
                    "Media type": key.replace("_", " ").title(),
                    "Bayut": bayut_m[key],
                    "Competitor": comp_m[key],
                    "Competitor source": comp["url"],
                    "Recommendation": f"Add {key.replace('_', ' ')} (used by competitor)"
                })

    return rows
