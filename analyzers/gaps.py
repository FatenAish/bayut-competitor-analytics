from typing import List, Dict, Any

NOISE_PHRASES = [
    "newsletter", "inbox", "subscribe", "register", "contact", "follow",
    "looking to rent", "looking to buy", "latest blogs", "podcasts",
    "real estate insights", "privacy policy", "terms", "cookie",
    "sign up", "sign-up", "call us", "whatsapp", "get in touch",
    "related", "you may also like"
]


def normalize_header(h: str) -> str:
    return " ".join((h or "").strip().split())


def is_noise_header(h: str) -> bool:
    t = (h or "").strip().lower()
    if not t:
        return True
    if len(t) <= 2:
        return True
    for p in NOISE_PHRASES:
        if p in t:
            return True
    return False


def _headers_in_order(parsed: Dict[str, Any]) -> List[str]:
    hs = []
    for h in (parsed.get("h2", []) + parsed.get("h3", [])):
        h = normalize_header(h)
        if not is_noise_header(h):
            hs.append(h)
    return hs


def update_gaps(bayut_parsed: Dict[str, Any], competitors: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    bayut_headers = {h.lower() for h in _headers_in_order(bayut_parsed)}

    missing_map: Dict[str, List[str]] = {}
    examples_map: Dict[str, List[str]] = {}

    for c in competitors:
        ordered = _headers_in_order(c["parsed"])
        comp_set = {h.lower() for h in ordered}

        missing = comp_set - bayut_headers

        for idx, h in enumerate(ordered):
            hl = h.lower()
            if hl in missing:
                missing_map.setdefault(h, []).append(c["url"])

                if "comparison" in hl and "neighborhood" in hl:
                    children = []
                    for j in range(idx + 1, min(idx + 6, len(ordered))):
                        child = ordered[j]
                        if child.lower() in missing and len(child) <= 40:
                            children.append(child)
                    if children:
                        examples_map.setdefault(h, []).extend(children)

    rows = []
    for k, v in missing_map.items():
        sources = ", ".join(sorted(set(v)))
        ex = ""
        for ek, ev in examples_map.items():
            if ek.lower() == str(k).lower():
                ex = ", ".join(sorted(set(ev)))
                break

        row = {"Missing section title": str(k).strip().title(), "Sources": sources}
        if ex:
            row["Examples inside it"] = ex
        rows.append(row)

    rows.sort(key=lambda r: r["Missing section title"])
    return rows


def new_post_strategy(bayut_title: str, competitors: List[Dict[str, Any]]) -> Dict[str, Any]:
    headers: Dict[str, List[str]] = {}

    for c in competitors:
        for h in _headers_in_order(c["parsed"]):
            headers.setdefault(h.title(), []).append(c["url"])

    return {
        "recommended_sections": [
            {"Recommended section title": k, "Sources": ", ".join(sorted(set(v)))}
            for k, v in headers.items()
        ]
    }
