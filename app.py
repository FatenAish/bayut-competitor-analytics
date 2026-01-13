import streamlit as st
import pandas as pd

# 🔴 IMPORTANT: this is the ONLY import
from analyzers.gaps import analyze_article


# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="Bayut Competitor Gap Analysis",
    layout="wide"
)

st.title("Bayut Competitor Editorial Gap Analysis")
st.caption("Semantic gap detection based on editorial intent — not HTML structure.")

# =====================================================
# INPUTS
# =====================================================
with st.form("gap_form"):
    bayut_url = st.text_input(
        "Bayut article URL",
        placeholder="https://www.bayut.com/mybayut/..."
    )

    competitor_urls_raw = st.text_area(
        "Competitor URLs (one per line, max 5)",
        placeholder=(
            "https://www.drivenproperties.com/...\n"
            "https://www.propertyfinder.ae/...\n"
        ),
        height=120
    )

    submitted = st.form_submit_button("Run analysis")


# =====================================================
# RUN ANALYSIS
# =====================================================
if submitted:
    if not bayut_url.strip():
        st.error("Please enter a Bayut article URL.")
        st.stop()

    competitor_urls = [
        u.strip() for u in competitor_urls_raw.splitlines()
        if u.strip()
    ]

    if not competitor_urls:
        st.error("Please add at least one competitor URL.")
        st.stop()

    if len(competitor_urls) > 5:
        st.warning("Only the first 5 competitor URLs will be analyzed.")
        competitor_urls = competitor_urls[:5]

    with st.spinner("Analyzing competitors…"):
        result = analyze_article(
            bayut_url=bayut_url,
            competitor_urls=competitor_urls
        )

    st.success("Analysis complete.")

    # =================================================
    # OUTPUT (ONE TABLE PER COMPETITOR — AS AGREED)
    # =================================================
    for comp in result["results"]:
        st.markdown("---")
        st.subheader(comp["competitor"])
        st.caption(comp["url"])

        rows = comp.get("rows", [])

        if not rows:
            st.info("No significant editorial gaps detected for this competitor.")
            continue

        df = pd.DataFrame(rows)

        # HARD SAFETY: enforce correct columns only
        df = df[[
            "Missing header",
            "What the header contains",
            "Source"
        ]]

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )
