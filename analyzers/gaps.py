import re
from urllib.parse import urlparse
from typing import List, Dict, Any


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


def _get_section_text(parsed: Dict[str, Any], level: int, heading_text: str) -> str:
    key = f"{level}:{heading_text}"
    return (parsed.get("section_texts", {}) or {}).get(key, "") or ""


def _extract_areas(text: str) -> str:
    found = []
    t = text or ""
    for a in _AREA_HINTS:
        if re.search(r"\b" + re.escape(a) + r"\b", t, flags=re.I):
            found.append(a)
    out = []
    for x in found:
        if x not in out:
            out.append(x)
    return ", ".join(out)


def _faq_diff(bayut_parsed: Dict[str, Any], comp_parsed: Dict[str, Any]) -> str:
    bq = set(_norm(x) for x in (bayut_parsed.get("faq_questions") or []) if x)
    cq_raw = (comp_parsed.get("faq_questions") or [])
    cq = [(x or "").strip() for x in cq_raw if x and (x or "").strip()]
    missing = [x for x in cq if _norm(x) not in bq]
    return "; ".join(missing[:8])


def _keywords(text: str) -> List[str]:
    text = text or ""
    words = re.findall(r"[A-Za-z]{5,}", text)
    words = [w.lower() for w in words]
    stop = {
        "about","above","after","again","against","along","among","around","because","before","being","below","between",
        "could","does","doing","during","each","either","every","first","found","great","here","into","its","itself",
        "many","might","more","most","other","over","some","such","than","that","their","there","these","those","through",
        "under","very","what","where","which","while","would","your","yours",
        "business","bay","dubai",
    }
    out = []
    for w in words:
        if w in stop:
            continue
        if len(w) < 5:
            continue
        out.append(w)
    uniq = []
    for w in out:
        if w not in uniq:
            uniq.append(w)
    return uniq[:12]


def update_gaps(bayut_parsed: Dict[str, Any], competitors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Output rows (neutral):
      Missing section in Bayut | What competitor has | Source (competitor)

    Rules:
      - H3 is analyzed alone
      - H4 is also analyzed alone (not merged into H3)
      - If Bayut has the header -> show (content gap) instead of “missing section”
      - FAQ row = missing questions (competitor vs Bayut), even if Bayut has FAQ header
      - Works per competitor: competitor1 rows + competitor2 rows + competitor3 rows in same table
    """
    rows = []

    bayut_h2 = set(_norm(x) for x in (bayut_parsed.get("h2") or []))
    bayut_h3 = set(_norm(x) for x in (bayut_parsed.get("h3") or []))
    bayut_h4 = set(_norm(x) for x in (bayut_parsed.get("h4") or []))

    def bayut_has_heading(text: str) -> bool:
        n = _norm(text)
        return (n in bayut_h2) or (n in bayut_h3) or (n in bayut_h4)

    for comp in competitors:
        comp_url = comp.get("url") or ""
        comp_parsed = comp.get("parsed") or {}
        source = comp_parsed.get("competitor_name") or _competitor_label(comp_url)

        comp_words = comp_parsed.get("word_count", 0) or 0
        comp_h_total = len(comp_parsed.get("h2", [])) + len(comp_parsed.get("h3", [])) + len(comp_parsed.get("h4", []))
        if comp_h_total == 0 and comp_words < 300:
            rows.append({
                "Missing section in Bayut": "(Competitor page not readable)",
                "What competitor has": "Could not extract headings/content (JS-rendered or blocked).",
                "Source (competitor)": source
            })
            continue

        # 1) Missing sections: H2/H3/H4
        for lvl_key in ["h2", "h3", "h4"]:
            lvl = int(lvl_key[1])
            for heading in (comp_parsed.get(lvl_key) or []):
                if not heading or _is_ignored_heading(heading):
                    continue

                # handle FAQ separately
                hlow = heading.lower()
                if "faq" in hlow or "frequently asked" in hlow:
                    continue

                if not bayut_has_heading(heading):
                    txt = _get_section_text(comp_parsed, lvl, heading)

                    if "comparison" in hlow or "other dubai" in hlow:
                        areas = _extract_areas(txt)
                        what_has = areas if areas else "Area-by-area comparison block (neighborhoods listed)."
                    else:
                        what_has = (txt[:180] + ("..." if len(txt) > 180 else "")) if txt else "Section exists on competitor."

                    rows.append({
                        "Missing section in Bayut": heading,
                        "What competitor has": what_has,
                        "Source (competitor)": source
                    })

        # 2) FAQ missing questions
        faq_missing = _faq_diff(bayut_parsed, comp_parsed)
        if faq_missing:
            rows.append({
                "Missing section in Bayut": "FAQs",
                "What competitor has": faq_missing,
                "Source (competitor)": source
            })

        # 3) Content gaps for shared H2/H3 (not headers)
        for lvl_key in ["h2", "h3"]:
            lvl = int(lvl_key[1])
            for heading in (comp_parsed.get(lvl_key) or []):
                if not heading or _is_ignored_heading(heading):
                    continue
                if not bayut_has_heading(heading):
                    continue

                comp_txt = _get_section_text(comp_parsed, lvl, heading)
                bayut_txt = _get_section_text(bayut_parsed, lvl, heading)

                if len(comp_txt) < 80:
                    continue

                comp_k = set(_keywords(comp_txt))
                bayut_k = set(_keywords(bayut_txt))
                diff = [w for w in comp_k if w not in bayut_k]

                if len(diff) >= 5:
                    rows.append({
                        "Missing section in Bayut": f"{heading} (content gap)",
                        "What competitor has": ", ".join(diff[:10]),
                        "Source (competitor)": source
                    })

    # de-dup exact duplicates
    seen = set()
    out = []
    for r in rows:
        key = (r["Missing section in Bayut"], r["What competitor has"], r["Source (competitor)"])
        if key in seen:
            continue
        seen.add(key)
        out.append(r)

    return out


def new_post_strategy(bayut_title: str, competitors: List[Dict[str, Any]]) -> Dict[str, Any]:
    pool = []
    for c in competitors:
        p = c.get("parsed") or {}
        source = p.get("competitor_name") or _competitor_label(c.get("url") or "")
        for k in ["h2", "h3", "h4"]:
            for h in (p.get(k) or []):
                if not h or _is_ignored_heading(h):
                    continue
                pool.append((h, source))

    by_title = {}
    for title, src in pool:
        t = title.strip()
        if t not in by_title:
            by_title[t] = []
        if src not in by_title[t]:
            by_title[t].append(src)

    recommended_sections = []
    for t, srcs in by_title.items():
        recommended_sections.append({"Section": t, "Seen on": ", ".join(srcs)})

    return {"recommended_sections": recommended_sections}
