import re

# -----------------------------
# Helpers
# -----------------------------
_JUNK_SECTION_PHRASES = [
    "newsletter", "inbox", "speak with us", "contact", "register your interest",
    "looking to rent", "looking to buy", "book a viewing", "enquire", "enquiry",
    "call us", "sign up", "subscribe", "latest blogs", "podcasts",
]

def _norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _is_junk(title: str) -> bool:
    t = _norm(title)
    return any(p in t for p in _JUNK_SECTION_PHRASES)

def _section_text(parsed: dict, section_norm: str) -> str:
    sec = (parsed.get("sections") or {}).get(section_norm) or {}
    text = (sec.get("text") or "") + " " + " ".join(sec.get("bullets") or [])
    return text.strip()

def _tokenize(text: str) -> list[str]:
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9\s-]", " ", text)
    parts = [p.strip() for p in text.split() if p.strip()]
    out = []
    for w in parts:
        if len(w) < 4:
            continue
        out.append(w)
    return out

def _missing_terms(comp_text: str, bayut_text: str, limit: int = 6) -> list[str]:
    c = set(_tokenize(comp_text))
    b = set(_tokenize(bayut_text))
    miss = [x for x in c if x not in b]
    miss = sorted(miss, key=lambda x: (-len(x), x))
    return miss[:limit]

def _build_parent_map(order: list[str], sections: dict) -> dict:
    """
    parent_map[child_norm] = parent_norm (nearest previous heading with smaller level)
    """
    parent_map = {}
    stack = []  # list of (norm, level)
    for norm in order:
        sec = sections.get(norm) or {}
        lvl = sec.get("level", 9)

        while stack and stack[-1][1] >= lvl:
            stack.pop()

        parent_map[norm] = stack[-1][0] if stack else None
        stack.append((norm, lvl))

    return parent_map

def _children_map(parent_map: dict) -> dict:
    ch = {}
    for child, parent in parent_map.items():
        if not parent:
            continue
        ch.setdefault(parent, []).append(child)
    return ch


# -----------------------------
# REQUIRED FUNCTIONS (used by app.py)
# -----------------------------
def update_gaps(bayut_parsed: dict, competitors: list[dict]) -> list[dict]:
    """
    Neutral output:
    - Missing sections (collapse child headings under missing parent)
    - FAQ missing questions (specific)
    - Content gaps when same header exists
    """
    rows = []

    bayut_sections = bayut_parsed.get("sections") or {}
    bayut_norm_set = set(bayut_sections.keys())

    # =============== 1) Missing sections (headers) with COLLAPSE ===============
    for c in competitors:
        cp = c.get("parsed") or {}
        source = cp.get("source_name") or c.get("url") or "Competitor"

        comp_sections = cp.get("sections") or {}
        order = cp.get("section_order") or list(comp_sections.keys())

        parent_map = _build_parent_map(order, comp_sections)
        children_map = _children_map(parent_map)

        # precompute missing flags
        is_missing = {}
        for norm in order:
            sec = comp_sections.get(norm) or {}
            title = sec.get("title") or norm
            if not title or _is_junk(title):
                is_missing[norm] = False
                continue
            is_missing[norm] = (norm not in bayut_norm_set)

        for norm in order:
            if not is_missing.get(norm):
                continue

            # If parent is also missing -> DO NOT list this child row
            parent = parent_map.get(norm)
            if parent and is_missing.get(parent):
                continue

            sec = comp_sections.get(norm) or {}
            title = sec.get("title") or norm
            if not title or _is_junk(title):
                continue

            # Gather missing children titles (collapsed under parent row)
            child_titles = []
            for child in children_map.get(norm, []):
                if is_missing.get(child):
                    csec = comp_sections.get(child) or {}
                    ctitle = (csec.get("title") or child).strip()
                    if ctitle and not _is_junk(ctitle):
                        child_titles.append(ctitle)

            comp_has = "Section exists on competitor."
            if child_titles:
                comp_has = "Includes subsections: " + ", ".join(child_titles)

            rows.append({
                "Missing section in Bayut": title,
                "What competitors have": comp_has,
                "Why it matters": "Content coverage difference (competitor includes it, Bayut doesn't).",
                "Source (competitor)": source
            })

    # =============== 2) FAQ missing QUESTIONS (not generic) ===============
    bayut_faq = set([q.lower().strip() for q in (bayut_parsed.get("faq_questions") or []) if q])

    for c in competitors:
        cp = c.get("parsed") or {}
        source = cp.get("source_name") or c.get("url") or "Competitor"
        comp_faq = [q for q in (cp.get("faq_questions") or []) if q and len(q) <= 160]

        missing_q = [q for q in comp_faq if q.lower().strip() not in bayut_faq]
        if missing_q:
            rows.append({
                "Missing section in Bayut": "FAQs (missing questions)",
                "What competitors have": "Questions present on competitor but not in Bayut: " + "; ".join(missing_q[:10]),
                "Why it matters": "FAQ coverage difference.",
                "Source (competitor)": source
            })

    # =============== 3) Content gaps under SAME header ===============
    for c in competitors:
        cp = c.get("parsed") or {}
        source = cp.get("source_name") or c.get("url") or "Competitor"

        comp_sections = cp.get("sections") or {}
        for sec_norm, sec in comp_sections.items():
            title = (sec.get("title") or sec_norm).strip()
            if not title or _is_junk(title):
                continue

            if sec_norm in bayut_norm_set:
                comp_text = _section_text(cp, sec_norm)
                bay_text = _section_text(bayut_parsed, sec_norm)

                miss_terms = _missing_terms(comp_text, bay_text, limit=6)
                if len(miss_terms) >= 4:
                    rows.append({
                        "Missing section in Bayut": f"{title} (content gap)",
                        "What competitors have": "Competitor mentions extra topics/terms: " + ", ".join(miss_terms),
                        "Why it matters": "Detail coverage difference within the same section.",
                        "Source (competitor)": source
                    })

    # De-dup
    dedup = []
    seen = set()
    for r in rows:
        key = (_norm(r["Missing section in Bayut"]), _norm(r["Source (competitor)"]))
        if key in seen:
            continue
        seen.add(key)
        dedup.append(r)

    # Priority sort
    def score(r):
        t = _norm(r["Missing section in Bayut"])
        if "comparison" in t:
            return 0
        if "faqs" in t:
            return 1
        if "conclusion" in t:
            return 2
        if "content gap" in t:
            return 3
        return 4

    dedup.sort(key=score)
    return dedup


def new_post_strategy(bayut_title: str, competitors: list[dict]) -> dict:
    # leave as-is for now (simple)
    rec = []
    seen = set()
    for c in competitors:
        cp = c.get("parsed") or {}
        source = cp.get("source_name") or c.get("url") or "Competitor"
        for sec_norm, sec in (cp.get("sections") or {}).items():
            title = (sec.get("title") or sec_norm).strip()
            if not title or _is_junk(title):
                continue
            k = _norm(title)
            if k in seen:
                continue
            seen.add(k)
            rec.append({
                "Section": title,
                "Source (competitor)": source
            })

    return {
        "bayut_title": bayut_title,
        "recommended_sections": rec
    }
