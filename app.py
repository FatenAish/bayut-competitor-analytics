import streamlit as st
import pandas as pd

from analyzers.gaps import analyze_article


st.set_page_config(page_title="Bayut Competitor Gap Analysis", layout="wide")

st.title("Bayut Competitor Editorial Gap Analysis")
st.caption("Outputs ONLY editorial gaps (short tables) — exactly like the approved examples.")

with st.form("form"):
    bayut_url = st.text_input(
        "Bayut article URL",
        value="",
        placeholder="https://www.bayut.com/mybayut/..."
    )

    competitor_raw = st.text_area(
        "Competitor URLs (one per line, max 5)",
        value="",
        height=120,
        placeholder="https://...\nhttps://..."
    )

    run = st.form_submit_button("Run")

if run:
    bayut_url = bayut_url.strip()
    competitors = [u.strip() for u in competitor_raw.splitlines() if u.strip()]

    if not bayut_url:
        st.error("Please enter the Bayut article URL.")
        st.stop()

    if not competitors:
        st.error("Please add at least one competitor URL.")
        st.stop()

    if len(competitors) > 5:
        st.warning("Only the first 5 competitor URLs will be analyzed.")
        competitors = competitors[:5]

    with st.spinner("Analyzing competitors…"):
        result = analyze_article(bayut_url, competitors)

    st.success("Analysis complete.")

    for comp in result["results"]:
        st.markdown("---")
        st.subheader(comp["competitor"])
        st.caption(comp["url"])

        rows = comp.get("rows", [])

        if not rows:
            st.info("No major editorial gaps detected for this competitor.")
            continue

        df = pd.DataFrame(rows)

        # enforce columns + order
        df = df[["Missing header", "What the header contains", "Source"]]

        st.dataframe(df, use_container_width=True, hide_index=True)
