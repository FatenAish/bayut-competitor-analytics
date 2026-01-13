import re

# -----------------------------
# Helpers
# -----------------------------
_JUNK_SECTION_PHRASES = [
    "newsletter", "inbox", "speak with us", "contact", "register your interest",
    "looking to rent", "looking to buy", "book a viewing", "enquire", "enquiry",
    "call us", "sign up", "subscribe", "latest blogs", "podcasts", "today",
]

def _norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _is_junk(title: str) -> bool:
    t = _norm(title)
    return any(p in t for p in _JUNK_SECTION_PHRASES)

def _tokenize_keywords(text: str) -> list[str]:
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9\s-]", " ", text)
    parts = [p.strip() for p in text.split() if p.strip()]
    # keep “useful” tokens
    out = []
    for w in parts:
        if len(w) < 4:
            continue
        if w in {"this", "that", "with", "from", "your", "have", "were", "will"}:
            continue
        out.append(w)
    return out

def _top_missing_terms(comp_text: str, bayut_text: str, limit: int = 6) -> list[str]:
    c = set(_tokenize_keywords(comp_text))
    b = set(_tokenize_keywords(bayut_text))
    missing = [x for x in c if x not in b]
    # prioritize “topic-like” terms
    missing = sorted(missing, key=lambda x: (-len(x), x))
    return missing[:limit]

def _special_reco(title: str):
    t = _norm(title)
    if "comparison" in t and ("neighborhood" in t or "neighbourhood" in t or "areas" in t):
        return (
            "Add a comparison block with Downtown Dubai, Dubai Marina, JLT (1 short paragraph each).",
            "Adds high-intent comparison content (SEO/AEO) and helps users decide faster."
        )
    if "faq" in t:
        return (
            "Add an FAQ block (5–8 questions) covering cost, commute, metro, rentals, lifestyle, best buildings.",
            "Improves AEO/AI extraction and increases chances of being quoted in AI answers."
        )
    if "conclusion" in t:
        return (
            "Add a short conclusion: who Business Bay is best for + 3 bullet takeaways + next-step internal links.",
            "Improves readability and strengthens AI summary extraction + user clarity."
        )
    return (None, None)

def _section_text(parsed: dict, section_norm: str) -> str:
    sec = (parsed.get("sections") or {}).get(section_norm) or {}
    text = (sec.get("text") or "") + " " + " ".join(sec.get("bullets") or [])
    return text.strip()

# -----------------------------
# REQUIRED FUNCTIONS (used by app.py)
# -----------------------------
def update_gaps(bayut_parsed: dict, competitors: list[dict]) -> list[dict]:
    """
    Output rows for the table:
      - Missing headers in Bayut
      - FAQ missing questions
      - Content gaps under same header
    """
    rows = []

    bayut_sections = bayut_parsed.get("sections") or {}
    bayut_norm_set = set(bayut_sections.keys())

    # 1) Missing sections (headers)
    for c in competitors:
        cp = c.get("parsed") or {}
        source = (cp.get("source_name") or c.get("url") or "Competitor")
        comp_sections = cp.get("sections") or {}

        for sec_norm, sec in comp_sections.items():
            title = sec.get("title") or sec_norm
            if not title or _is_junk(title):
                continue

            # missing header completely
            if sec_norm not in bayut_norm_set:
                reco, why = _special_reco(title)
                if not reco:
                    # generic: suggest top themes from competitor section
                    comp_text = _section_text(cp, sec_norm)
                    themes = _top_missing_terms(comp_text, "", limit=5)
                    if themes:
                        reco = f"Add a short section titled '{title}' covering: " + ", ".join(themes) + "."
                    else:
                        reco = f"Add a short section titled '{title}' (2–4 short paragraphs + bullets)."
                    why = "Competitors cover this topic; adding it improves completeness and AI summarization."

                rows.append({
                    "Missing section in Bayut": title,
                    "What to add (recommendation)": reco,
                    "Why it matters": why,
                    "Source (competitor)": source
                })

    # 2) FAQ gap (missing QUESTIONS)
    bayut_faq = set([q.lower().strip() for q in (bayut_parsed.get("faq_questions") or [])])
    faq_missing_by_source = []

    for c in competitors:
        cp = c.get("parsed") or {}
        source = cp.get("source_name") or c.get("url") or "Competitor"
        comp_faq = [q for q in (cp.get("faq_questions") or []) if q and len(q) <= 140]
        comp_set = set([q.lower().strip() for q in comp_faq])

        missing = [q for q in comp_faq if q.lower().strip() not in bayut_faq]
        if missing:
            faq_missing_by_source.append((source, missing[:8]))

    if faq_missing_by_source:
        # make 1 row per competitor to keep it clear
        for source, missing_qs in faq_missing_by_source:
            rows.append({
                "Missing section in Bayut": "FAQs (missing questions)",
                "What to add (recommendation)": "Add these FAQ questions: " + "; ".join(missing_qs),
                "Why it matters": "FAQ questions are direct-answer targets (AEO/AI Overview) and improve snippet visibility.",
                "Source (competitor)": source
            })

    # 3) Content gaps under SAME header
    # If competitor has same section title but Bayut section is thinner / missing key terms
    for c in competitors:
        cp = c.get("parsed") or {}
        source = cp.get("source_name") or c.get("url") or "Competitor"
        comp_sections = cp.get("sections") or {}

        for sec_norm, sec in comp_sections.items():
            title = sec.get("title") or sec_norm
            if not title or _is_junk(title):
                continue

            if sec_norm in bayut_norm_set:
                comp_text = _section_text(cp, sec_norm)
                bay_text = _section_text(bayut_parsed, sec_norm)

                missing_terms = _top_missing_terms(comp_text, bay_text, limit=6)

                # only flag if meaningful gap
                if len(missing_terms) >= 4:
                    rows.append({
                        "Missing section in Bayut": f"{title} (content gap)",
                        "What to add (recommendation)": "Add missing points: " + ", ".join(missing_terms) + ".",
                        "Why it matters": "Same section exists, but competitors include extra details that AI and users expect.",
                        "Source (competitor)": source
                    })

    # De-duplicate (same section + same source)
    dedup = []
    seen = set()
    for r in rows:
        key = (_norm(r["Missing section in Bayut"]), _norm(r["Source (competitor)"]))
        if key in seen:
            continue
        seen.add(key)
        dedup.append(r)

    # Priority ordering
    def score(r):
        t = _norm(r["Missing section in Bayut"])
        if "comparison" in t:
            return 0
        if "faq" in t:
            return 1
        if "conclusion" in t:
            return 2
        if "content gap" in t:
            return 3
        return 4

    dedup.sort(key=score)
    return dedup


def new_post_strategy(bayut_title: str, competitors: list[dict]) -> dict:
    """
    Keep it simple for now: recommend key sections based on competitor headings + FAQ presence.
    """
    recommended = []
    seen = set()

    for c in competitors:
        cp = c.get("parsed") or {}
        source = cp.get("source_name") or c.get("url") or "Competitor"
        comp_sections = cp.get("sections") or {}

        for sec_norm, sec in comp_sections.items():
            title = sec.get("title") or sec_norm
            if not title or _is_junk(title):
                continue
            k = _norm(title)
            if k in seen:
                continue
            seen.add(k)

            reco, why = _special_reco(title)
            if not reco:
                reco = f"Include a section titled '{title}' (short + bullets)."
                why = "Competitors include it; it helps cover user intent and improves AI summaries."

            recommended.append({
                "Section to include": title,
                "What to add (recommendation)": reco,
                "Why it matters": why,
                "Source (competitor)": source
            })

    # If competitors have FAQ signals, recommend FAQ explicitly
    any_faq = any((c.get("parsed") or {}).get("faq_count", 0) > 0 for c in competitors)
    if any_faq and "faqs" not in seen:
        recommended.append({
            "Section to include": "FAQs",
            "What to add (recommendation)": "Add 5–8 FAQs (cost, rent, commute, metro, lifestyle, best buildings).",
            "Why it matters": "Direct-answer format for AEO/AI Overview + improves snippet coverage.",
            "Source (competitor)": "Multiple"
        })

    return {
        "bayut_title": bayut_title,
        "recommended_sections": recommended
    }
