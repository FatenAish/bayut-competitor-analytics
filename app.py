import streamlit as st
import pandas as pd

from analyzers.fetcher import fetch_html
from analyzers.parser import parse_html
from analyzers.gaps import update_gaps, new_post_strategy
from exporters.export import export_csv, export_excel, export_json


def normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


st.set_page_config(page_title="Bayut AI Competitor Analytics", layout="wide")
st.title("Bayut AI Competitor Analytics")
st.caption("Content gaps based on competitor structure (H2/H3 + H4 under H3)")

mode = st.radio("Choose analysis mode", ["NEW POST", "UPDATE"], horizontal=True)
timeout = st.slider("Request timeout (seconds)", 5, 60, 20)
st.divider()

st.subheader("Inputs")

if "competitors" not in st.session_state:
    st.session_state["competitors"] = [""]

if mode == "NEW POST":
    bayut_title = st.text_input("Bayut article title", placeholder="Living in Business Bay – Ideal city life or a bit too hectic?")
    bayut_url = ""
else:
    bayut_url = st.text_input("Bayut article URL", placeholder="https://www.bayut.com/mybayut/...")
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
            placeholder="https://example.com/page",
        )
    with col_b:
        if st.button("✖", key=f"remove_{i}"):
            st.session_state["competitors"].pop(i)
            st.rerun()

run = st.button("Run analysis", type="primary")


if run:
    competitor_urls = [normalize_url(u) for u in st.session_state["competitors"] if normalize_url(u)]

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
                errors.append({"URL": url, "Error": result["error"], "Status": result["status"]})
                continue

            parsed = parse_html(result["html"], page_url=result.get("final_url") or url)
            competitors.append({"url": url, "parsed": parsed})

    if errors:
        st.warning("Some competitor URLs could not be fetched:")
        st.dataframe(pd.DataFrame(errors), use_container_width=True)

    if not competitors:
        st.error("No competitor pages could be analyzed.")
        st.stop()

    st.divider()
    st.subheader("Results")

    # diagnostics (so you see if a competitor is blocked/empty)
    st.caption(f"Competitors analyzed: {len(competitors)} / {len(competitor_urls)}")
    diag = []
    for c in competitors:
        p = c["parsed"]
        diag.append({
            "Competitor": p.get("competitor_name") or c["url"],
            "h2": len(p.get("h2", [])),
            "h3": len(p.get("h3", [])),
            "h4": len(p.get("h4", [])),
            "words": p.get("word_count", 0),
        })
    st.dataframe(pd.DataFrame(diag), use_container_width=True)

    if mode == "NEW POST":
        strategy = new_post_strategy(bayut_title, competitors)
        st.markdown("### What competitors cover (sections to consider)")
        st.dataframe(pd.DataFrame(strategy["recommended_sections"]), use_container_width=True)

        payload = {"mode": "NEW POST", "bayut_title": bayut_title, "strategy": strategy}
        sheets = {"Recommended_Sections": strategy["recommended_sections"]}

    else:
        bayut_result = fetch_html(normalize_url(bayut_url), timeout=timeout)
        if not bayut_result["ok"]:
            st.error("Bayut URL could not be fetched.")
            st.stop()

        bayut_parsed = parse_html(bayut_result["html"], page_url=bayut_result.get("final_url") or bayut_url)

        st.markdown("### Competitor sections missing in Bayut")
        missing_rows = update_gaps(bayut_parsed, competitors)
        st.dataframe(pd.DataFrame(missing_rows), use_container_width=True)

        payload = {
            "mode": "UPDATE",
            "bayut_url": bayut_url,
            "missing_sections": missing_rows,
        }
        sheets = {"Missing_Sections": missing_rows}

    st.divider()
    st.subheader("Download results")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button(
            "Download CSV",
            export_csv(list(sheets.values())[0]),
            file_name="analysis.csv",
            mime="text/csv",
        )
    with c2:
        st.download_button(
            "Download Excel",
            export_excel(sheets),
            file_name="analysis.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    with c3:
        st.download_button(
            "Download JSON",
            export_json(payload),
            file_name="analysis.json",
            mime="application/json",
        )
