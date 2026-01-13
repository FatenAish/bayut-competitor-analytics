import streamlit as st
import pandas as pd

from analyzers.fetcher import fetch_html
from analyzers.parser import parse_html
from analyzers.seo import seo_analysis
from analyzers.schema import schema_analysis
from analyzers.ai_readiness import ai_readiness_analysis
from analyzers.gaps import update_gaps, new_post_strategy
from analyzers.compliance import compliance_analysis
from analyzers.media import media_comparison
from exporters.export import export_csv, export_excel, export_json


# --------------------------------------------------
# HELPERS
# --------------------------------------------------
def normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="Bayut AI Competitor Analytics",
    layout="wide"
)

st.title("Bayut AI Competitor Analytics")
st.caption("Content • SEO • Media • Schema • AI Visibility (competitor-based)")

mode = st.radio(
    "Choose analysis mode",
    ["NEW POST", "UPDATE"],
    horizontal=True
)

timeout = st.slider("Request timeout (seconds)", 5, 60, 20)

st.divider()

# --------------------------------------------------
# INPUTS
# --------------------------------------------------
st.subheader("Inputs")

if "competitors" not in st.session_state:
    st.session_state["competitors"] = [""]

if mode == "NEW POST":
    bayut_title = st.text_input(
        "Bayut article title",
        placeholder="Living in Business Bay – Ideal city life or a bit too hectic?"
    )
    bayut_url = ""
else:
    bayut_url = st.text_input(
        "Bayut article URL",
        placeholder="https://www.bayut.com/mybayut/..."
    )
    bayut_title = ""

c1, c2 = st.columns(2)
with c1:
    if st.button("➕ Add competitor"):
        st.session_state["competitors"].append("")
with c2:
    if st.button("🧹 Clear competitors"):
        st.session_state["competitors"] = [""]

st.write("Competitor URLs")
for i in range(len(st.session_state["competitors"])):
    col_a, col_b = st.columns([12, 1])
    with col_a:
        st.session_state["competitors"][i] = st.text_input(
            f"Competitor #{i+1}",
            value=st.session_state["competitors"][i],
            key=f"comp_{i}",
            placeholder="https://example.com/page"
        )
    with col_b:
        if st.button("✖", key=f"remove_{i}"):
            st.session_state["competitors"].pop(i)
            st.rerun()

run = st.button("Run analysis", type="primary")

# --------------------------------------------------
# RUN ANALYSIS
# --------------------------------------------------
if run:
    competitor_urls = [
        normalize_url(u) for u in st.session_state["competitors"] if normalize_url(u)
    ]

    if mode == "NEW POST" and not bayut_title.strip():
        st.error("Please enter a Bayut title.")
        st.stop()

    if mode == "UPDATE" and not normalize_url(bayut_url):
        st.error("Please enter a Bayut URL.")
        st.stop()

    if not competitor_urls:
        st.error("Please add at least one competitor URL.")
        st.stop()

    competitors = []
    errors = []

    with st.spinner("Fetching competitor pages…"):
        for url in competitor_urls:
            result = fetch_html(url, timeout=timeout)
            if not result["ok"]:
                errors.append({
                    "URL": url,
                    "Error": result["error"],
                    "Status": result["status"]
                })
                continue

            # IMPORTANT: parse_html only accepts (html: str) in your parser.py
            parsed = parse_html(result["html"])

            competitors.append({
                "url": url,
                "parsed": parsed
            })

    if errors:
        st.warning("Some competitor URLs could not be fetched:")
        st.dataframe(pd.DataFrame(errors), use_container_width=True)

    if not competitors:
        st.error("No competitor pages could be analyzed.")
        st.stop()

    st.divider()
    st.subheader("Results")

    # ==================================================
    # NEW POST MODE
    # ==================================================
    if mode == "NEW POST":
        strategy = new_post_strategy(bayut_title, competitors)

        st.markdown("### What competitors cover (sections to include)")
        st.dataframe(
            pd.DataFrame(strategy["recommended_sections"]),
            use_container_width=True
        )

        payload = {
            "mode": "NEW POST",
            "bayut_title": bayut_title,
            "strategy": strategy
        }

        sheets = {
            "Recommended_Sections": strategy["recommended_sections"]
        }

    # ==================================================
    # UPDATE MODE
    # ==================================================
    else:
        bayut_result = fetch_html(normalize_url(bayut_url), timeout=timeout)
        if not bayut_result["ok"]:
            st.error("Bayut URL could not be fetched.")
            st.stop()

        # IMPORTANT: parse_html only accepts (html: str) in your parser.py
        bayut_parsed = parse_html(bayut_result["html"])

        bayut_data = {
            "url": bayut_url,
            "parsed": bayut_parsed
        }

        # ---------------- HEADERS / CONTENT GAPS ----------------
        missing_headers = update_gaps(bayut_parsed, competitors)

        st.markdown("### Competitor sections missing in Bayut")
        st.dataframe(
            pd.DataFrame(missing_headers),
            use_container_width=True
        )

        # ---------------- SEO COMPLIANCE ----------------
        st.markdown("### SEO Compliance (Bayut vs best competitor)")
        compliance_rows = compliance_analysis(
            bayut=bayut_data,
            competitors=competitors,
            title=bayut_parsed.get("title", "")
        )
        st.dataframe(
            pd.DataFrame(compliance_rows),
            use_container_width=True
        )

        # ---------------- MEDIA COMPARISON ----------------
        st.markdown("### Media comparison (visual assets)")
        media_rows = media_comparison(
            bayut=bayut_data,
            competitors=competitors
        )

        if media_rows:
            st.dataframe(
                pd.DataFrame(media_rows),
                use_container_width=True
            )
        else:
            st.info("Bayut matches or exceeds competitors in media usage.")

        # ---------------- SCHEMA ----------------
        st.markdown("### Schema usage (Bayut vs competitors)")
        schema_rows = []

        schema_rows.append({
            "Page": "Bayut",
            "Schema types": ", ".join(bayut_parsed.get("schema_types", [])) or "None"
        })

        for c in competitors:
            schema_rows.append({
                "Page": c["url"],
                "Schema types": ", ".join(c["parsed"].get("schema_types", [])) or "None"
            })

        st.dataframe(pd.DataFrame(schema_rows), use_container_width=True)

        # ---------------- AI VISIBILITY ----------------
        st.markdown("### AI visibility (AI Overview / AEO / GEO) — what to add")
        ai = ai_readiness_analysis(bayut_parsed)

        ai_rows = []
        for gap in ai.get("ai_gaps", []):
            ai_rows.append({
                "Missing for AI visibility": gap,
                "What to add": "Add short direct answer + FAQ + clear comparisons + stats/figures where relevant."
            })

        if ai_rows:
            st.dataframe(pd.DataFrame(ai_rows), use_container_width=True)
        else:
            st.success("No major AI visibility gaps detected by current rules (we will tighten this later).")

        # ---------------- FINAL RECOMMENDATIONS ----------------
        st.markdown("### Final recommendations (priority)")
        final_recs = []

        for row in compliance_rows:
            if (row.get("Gap") or "").strip().lower() == "yes":
                rec = row.get("Recommendation")
                if rec:
                    final_recs.append(rec)

        # media_rows might not have "Recommendation" key, so only take if exists
        for row in media_rows:
            rec = row.get("Recommendation")
            if rec:
                final_recs.append(rec)

        for row in ai_rows:
            rec = row.get("Missing for AI visibility")
            if rec:
                final_recs.append(rec)

        final_recs = list(dict.fromkeys(final_recs))[:10]

        for i, rec in enumerate(final_recs, 1):
            st.markdown(f"**{i}.** {rec}")

        payload = {
            "mode": "UPDATE",
            "bayut_url": bayut_url,
            "missing_headers": missing_headers,
            "seo_compliance": compliance_rows,
            "media": media_rows,
            "schema": schema_rows,
            "ai": ai_rows,
            "final_recommendations": final_recs
        }

        sheets = {
            "Missing_Headers": missing_headers,
            "SEO_Compliance": compliance_rows,
            "Media": media_rows,
            "Schema": schema_rows,
            "AI_Visibility": ai_rows,
            "Recommendations": [{"Recommendation": r} for r in final_recs]
        }

    # --------------------------------------------------
    # DOWNLOADS
    # --------------------------------------------------
    st.divider()
    st.subheader("Download results")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button(
            "Download CSV",
            export_csv(list(sheets.values())[0]),
            file_name="analysis.csv",
            mime="text/csv"
        )

    with c2:
        st.download_button(
            "Download Excel",
            export_excel(sheets),
            file_name="analysis.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    with c3:
        st.download_button(
            "Download JSON",
            export_json(payload),
            file_name="analysis.json",
            mime="application/json"
        )
