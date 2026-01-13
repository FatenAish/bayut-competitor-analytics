import streamlit as st
import pandas as pd

from analyzers.fetcher import fetch_html
from analyzers.parser import parse_html
from analyzers.seo import seo_analysis
from analyzers.schema import schema_analysis
from analyzers.ai_readiness import ai_readiness_analysis
from analyzers.gaps import update_gaps, new_post_strategy
from exporters.export import export_csv, export_excel, export_json


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
st.caption("SEO • Schema • AI Overview • AEO • GEO — with sources")

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
        "Bayut Title (only)",
        placeholder="Living in Business Bay – Ideal city life or a bit too hectic?"
    )
    bayut_url = ""
else:
    bayut_url = st.text_input(
        "Bayut URL",
        placeholder="https://www.bayut.com/mybayut/..."
    )
    bayut_title = ""

c1, c2 = st.columns([1, 1])
with c1:
    if st.button("➕ Add competitor"):
        st.session_state["competitors"].append("")
with c2:
    if st.button("🧹 Clear competitors"):
        st.session_state["competitors"] = [""]

st.write("Competitor URLs:")
for i in range(len(st.session_state["competitors"])):
    col_a, col_b = st.columns([12, 1])
    with col_a:
        st.session_state["competitors"][i] = st.text_input(
            f"Competitor #{i+1}",
            value=st.session_state["competitors"][i],
            placeholder="https://example.com/page",
            key=f"comp_{i}"
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

            parsed = parse_html(result["html"])

            competitors.append({
                "url": url,
                "parsed": parsed,
                "seo": seo_analysis(parsed),
                "schema": schema_analysis(parsed),
                "ai": ai_readiness_analysis(parsed),
            })

    if errors:
        st.warning("Some competitor URLs could not be fetched:")
        st.dataframe(pd.DataFrame(errors), use_container_width=True)

    if not competitors:
        st.error("No competitor pages could be analyzed.")
        st.stop()

    st.divider()
    st.subheader("Results")

    # ---------------- NEW POST ----------------
    if mode == "NEW POST":
        strategy = new_post_strategy(bayut_title, competitors)

        st.markdown("### New Post Strategy (What to add to beat competitors)")
        df_sections = pd.DataFrame(strategy["recommended_sections"])
        st.dataframe(df_sections, use_container_width=True)

        st.markdown("### AI Overview / AEO / GEO gaps (from competitors)")
        ai_rows = []
        for c in competitors:
            for gap in c["ai"]["ai_gaps"]:
                ai_rows.append({
                    "Gap": gap,
                    "Source": c["url"]
                })

        df_ai = pd.DataFrame(ai_rows)
        st.dataframe(df_ai, use_container_width=True)

        payload = {
            "mode": "NEW POST",
            "bayut_title": bayut_title,
            "strategy": strategy,
            "ai_gaps": ai_rows
        }

        sheets = {
            "New_Post_Strategy": strategy["recommended_sections"],
            "AI_Gaps": ai_rows
        }

    # ---------------- UPDATE ----------------
    else:
        bayut_result = fetch_html(normalize_url(bayut_url), timeout=timeout)
        if not bayut_result["ok"]:
            st.error("Bayut URL could not be fetched.")
            st.stop()

        bayut_parsed = parse_html(bayut_result["html"])

        missing = update_gaps(bayut_parsed, competitors)

        st.markdown("### Missing content vs competitors")
        df_missing = pd.DataFrame(missing)
        st.dataframe(df_missing, use_container_width=True)

        st.markdown("### SEO Analysis (Bayut)")
        st.json(seo_analysis(bayut_parsed))

        st.markdown("### Schema Analysis (Bayut)")
        st.json(schema_analysis(bayut_parsed))

        st.markdown("### AI Overview / AEO / GEO gaps (Bayut)")
        st.json(ai_readiness_analysis(bayut_parsed))

        payload = {
            "mode": "UPDATE",
            "bayut_url": bayut_url,
            "missing_content": missing,
            "seo": seo_analysis(bayut_parsed),
            "schema": schema_analysis(bayut_parsed),
            "ai": ai_readiness_analysis(bayut_parsed)
        }

        sheets = {
            "Missing_Content": missing
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
            export_csv(sheets[list(sheets.keys())[0]]),
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
