from typing import Dict, Any, List


def _p(page: Dict[str, Any]) -> Dict[str, Any]:
    return page.get("parsed", {}) or {}


def media_flags(page: Dict[str, Any]) -> Dict[str, Any]:
    p = _p(page)
    return {
        "images": int(p.get("image_count", 0) or 0),
        "videos": int(p.get("video_count", 0) or 0),
        "iframes": int(p.get("iframe_count", 0) or 0),
        "tables": int(p.get("table_count", 0) or 0),
        "map": bool(p.get("has_map_signal", False)),  # ✅ correct key
        "og_image": bool((p.get("og_image") or "").strip()),
    }


def media_comparison(bayut: Dict[str, Any], competitors: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    bay = media_flags(bayut)

    rows = []
    for c in competitors:
        m = media_flags(c)
        rows.append({
            "Competitor": c.get("url", ""),
            "Images": str(m["images"]),
            "Video": "Yes" if m["videos"] > 0 else "No",
            "Map": "Yes" if m["map"] else "No",
            "Tables": str(m["tables"]),
            "OG image": "Yes" if m["og_image"] else "No",
            "What competitor has (vs Bayut)": ", ".join([
                "Map" if (m["map"] and not bay["map"]) else "",
                "Video" if (m["videos"] > 0 and bay["videos"] == 0) else "",
                "More images" if (m["images"] > bay["images"]) else "",
                "Tables" if (m["tables"] > 0 and bay["tables"] == 0) else "",
            ]).replace(",,", ",").strip(" ,")
        })
    return rows
