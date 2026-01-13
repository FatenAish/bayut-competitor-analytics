import re
from urllib.parse import urlparse


_IGNORE_PATTERNS = [
    r"subscribe",
    r"newsletter",
    r"looking to buy",
    r"looking to rent",
    r"speak with us",
    r"contact us",
    r"register your interest",
    r"get in touch",
    r"download",
    r"podcast",
    r"latest blogs",
]

# area hints for "Comparison..." blocks
_AREA_HINTS = [
    "Dubai Marina",
    "Downtown Dubai",
    "DIFC",
    "JLT",
    "Jumeirah Lakes Towers",
    "Business Bay",
    "Palm Jumeirah",
    "JBR",
    "Jumeirah Beach Residence",
    "Dubai Hills Estate",
    "Arabian Ranches",
    "Deira",
    "Dubai Creek Harbour",
    "The Valley",
    "Emaar South",
]


def _norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^a-z0-9\s\?\&\:\(\)\-\/]", "", s)
    return s.strip()


def _is_ignored_heading(title: str) -> bool:
    t = (title or "").strip().lower()
    for p in _IGNORE_PATTERNS:
        if re.search(p, t):
            return True
    return False


def _competitor_label(url: str) -> str:
    host = ""
    try:
        host = urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        host = ""
    if "drivenproperties" in host:
        return "Driven Properties"
    if "dubizzle" in host:
        return "Dubizzle"
    if "emaar" in host:
        return "Emaar"
    return host.split(":")[0] if host else "Competitor"


def _get_section_text(parsed: dict, level: int, heading_text: str) -> str:
    # parser stores section_texts keys as "lvl:Heading"
    key = f"{level}:{heading_text}"
    return (parsed.get("section_texts", {}) or {}).get(key, "") or ""


def _extract_areas(text: str) -> str:
    found = []
    t = text or ""
    for a in _AREA_HINTS:
        if re.search(r"\b" + re.escape(a) + r"\b", t, flags=re.I):
            found.append(a)
    # unique preserve order
    out = []
    for x in found:
        if x not in out:
            out.append(x)
    return ", ".join(out)


def _faq_diff(bayut_parsed: dict, comp_parsed: dict) -> str:
    bq = set(_norm(x) for x in (bayut_parsed.get("faq_questions") or []) if x)
    cq_raw = (comp_parsed.get("faq_questions") or [])
    cq = [(x or "").strip() for x in cq_raw if x and (x or "").strip()]
    missing = [x for x in cq if _norm(x) not in bq]
    return "; ".join(missing[:6])


def _keywords(text: str) -> list[str]:
    # basic keyword extraction (kept simple + avoids junk)
    text = (text or "")
    words = re.findall(r"[A-Za-z]{5,}", text)
    words = [w.lower() for w in words]
    stop = {
        "about","above","after","again","against","along","among","around","because","before","being","below","between",
        "could","does","doing","during","each","either","every","first","found","great","here","into","its","itself",
        "many","might","more","most","other","over","some","such","than","that","their","there","these","those","through",
        "under","very","what","where","which","while","would","your","yours",
        "business","bay","dubai",  # remove generic page words
    }
    out = []
    for w in words:
        if w in stop:
            continue
        if len(w) < 5:
            continue
        out.append(w)
    # unique + keep order
    uniq = []
    for w in out:
        if w not in uniq:
            uniq.append(w)
    return uniq[:12]


def update_gaps(bayut_parsed: dict, competitors: list[dict]) -> list[dict]:
    """
    Output rows:
      Missing section in Bayut | What competitor has | Source (competitor)
    Rule:
      - H3 is analyzed alone
      - H4 under H3 are also analyzed alone (not merged into H3)
      - If Bayut has the header, we do content-gap instead of "missing header"
      - For FAQ: show missing questions (competitor vs Bayut)
    """
    rows = []

    bayut_h2 = set(_norm(x) for x in (bayut_parsed.get("h2") or []))
    bayut_h3 = set(_norm(x) for x in (bayut_parsed.get("h3") or []))
    bayut_h4 = set(_norm(x) for x in (bayut_parsed.get("h4") or []))

    # helper to see if Bayut has a heading (any level)
    def bayut_has_heading(text: str) -> bool:
        n = _norm(text)
        return (n in bayut_h2) or (n in bayut_h3) or (n in bayut_h4)

    for comp in competitors:
        comp_url = comp.get("url") or ""
        comp_parsed = comp.get("parsed") or {}
        source = comp_parsed.get("competitor_name") or _competitor_label(comp_url)

        # if competitor isn't readable (blocked / JS), show it explicitly
        comp_words = comp_parsed.get("word_count", 0) or 0
        comp_h_total = len(comp_parsed.get("h2", [])) + len(comp_parsed.get("h3", [])) + len(comp_parsed.get("h4", []))
        if comp_h_total == 0 and comp_words < 300:
            rows.append({
                "Missing section in Bayut": "(Competitor page not readable)",
                "What competitor has": "Could not extract headings/content (JS-rendered or blocked).",
                "Source (competitor)": source
            })
            continue

        # ------------------------------------------------------------
        # 1) Missing sections (H2/H3/H4) — each alone
        # ------------------------------------------------------------
        for lvl_key in ["h2", "h3", "h4"]:
            lvl = int(lvl_key[1])
            for heading in (comp_parsed.get(lvl_key) or []):
                if not heading or _is_ignored_heading(heading):
                    continue

                # FAQ handled separately (more precise)
                if "faq" in heading.lower() or "frequently asked" in heading.lower():
                    continue

                if not bayut_has_heading(heading):
                    what_has = ""

                    # special handling: "Comparison..." should list areas
                    if "comparison" in heading.lower() or "other dubai" in heading.lower():
                        txt = _get_section_text(comp_parsed, lvl, heading)
                        areas = _extract_areas(txt)
                        what_has = areas if areas else "Area-by-area comparison block (neighborhoods listed)."
                    else:
                        txt = _get_section_text(comp_parsed, lvl, heading)
                        what_has = txt[:180] + ("..." if len(txt) > 180 else "")

                    rows.append({
                        "Missing section in Bayut": heading,
                        "What competitor has": what_has or "Section exists on competitor.",_
