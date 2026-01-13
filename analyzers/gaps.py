from typing import List, Dict, Any


def normalize_header(h: str) -> str:
    return " ".join((h or "").lower().strip().split())


def update_gaps(bayut_parsed: Dict[str, Any], competitors: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    bayut_headers = {
        normalize_header(h)
        for h in (bayut_parsed.get("h2", []) + bayut_parsed.get("h3", []))
        if normalize_header(h)
    }

    missing_map: Dict[str, List[str]] = {}

    for c in competitors:
        comp_headers = {
            normalize_header(h)
            for h in (c["parsed"].get("h2", []) + c["parsed"].get("h3", []))
            if normalize_header(h)
        }

        for h in (comp_headers - bayut_headers):
            missing_map.setdefault(h.title(), []).append(c["url"])

    return [
        {
            "Missing section title": k,
            "Sources": ", ".join(sorted(set(v)))
        }
        for k, v in missing_map.items()
    ]


def new_post_strategy(bayut_title: str, competitors: List[Dict[str, Any]]) -> Dict[str, Any]:
    headers: Dict[str, List[str]] = {}

    for c in competitors:
        for h in (c["parsed"].get("h2", []) + c["parsed"].get("h3", [])):
            key = normalize_header(h)
            if not key:
                continue
            headers.setdefault(key.title(), []).append(c["url"])

    return {
        "recommended_sections": [
            {
                "Recommended section title": k,
                "Sources": ", ".join(sorted(set(v)))
            }
            for k, v in headers.items()
        ]
    }
