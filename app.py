import streamlit as st

# ==================================================
# PAGE CONFIG
# ==================================================
st.set_page_config(
    page_title="Bayut AI Competitor Analysis",
    layout="wide"
)

# ==================================================
# GLOBAL STYLES
# ==================================================
st.markdown(
    """
    <style>
    body {
        background-color: #ffffff;
    }

    .center {
        text-align: center;
    }

    .subtitle {
        color: #6b7280;
        font-size: 16px;
        margin-top: -8px;
        margin-bottom: 50px;
    }

    /* MODE CARDS */
    .mode-wrapper {
        display: flex;
        justify-content: center;
        gap: 32px;
        margin-top: 20px;
        margin-bottom: 60px;
    }

    .mode-card {
        width: 280px;
        padding: 28px 24px;
        border-radius: 18px;
        border: 1px solid #e5e7eb;
        background: #ffffff;
        box-shadow: 0 10px 25px rgba(0,0,0,0.04);
        text-align: center;
        transition: all 0.25s ease;
        cursor: pointer;
    }

    .mode-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 18px 40px rgba(0,0,0,0.08);
        border-color: #d1d5db;
    }

    .mode-icon {
        font-size: 28px;
        margin-bottom: 10px;
    }

    .mode-title {
        font-size: 18px;
        font-weight: 700;
        margin-bottom: 6px;
    }

    .mode-desc {
        font-size: 14px;
        color: #6b7280;
    }

    .section {
        max-width: 720px;
        margin: auto;
        margin-top: 20px;
    }

    .stTextInput > div > div > input {
        border-radius: 14px;
        height: 48px;
    }

    .primary-btn button {
        width: 100%;
        height: 48px;
        border-radius: 999px;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ==================================================
# SESSION STATE
# ==================================================
if "mode" not in st.session_state:
    st.session_state.mode = None

if "competitor_urls" not in st.session_state:
    st.session_state.competitor_urls = []

# ==================================================
# HEADER
# ==================================================
st.markdown("<h1 class='center'>Bayut AI Competitor Analysis</h1>", unsafe_allow_html=True)
st.markdown(
    "<p class='center subtitle'>SEO & editorial analysis against the market standard</p>",
    unsafe_allow_html=True
)

# ==================================================
# MODE SELECTION (TRUE CENTER)
# ==================================================
st.markdown("<h3 class='center'>Choose your mode</h3>", unsafe_allow_html=True)

mode_clicked = st.markdown(
    """
    <div style="
        display:flex;
        justify-content:center;
        gap:32px;
        margin-top:30px;
        margin-bottom:60px;
    ">
        <form method="post">
            <button name="mode" value="update"
                style="
                    padding:18px 28px;
                    border-radius:18px;
                    border:1px solid #e5e7eb;
                    background:white;
                    font-size:16px;
                    font-weight:600;
                    cursor:pointer;
                    box-shadow:0 10px 25px rgba(0,0,0,0.06);
                ">
                ✏️ Update Existing Article
            </button>
        </form>

        <form method="post">
            <button name="mode" value="new"
                style="
                    padding:18px 28px;
                    border-radius:18px;
                    border:1px solid #e5e7eb;
                    background:white;
                    font-size:16px;
                    font-weight:600;
                    cursor:pointer;
                    box-shadow:0 10px 25px rgba(0,0,0,0.06);
                ">
                🆕 Plan New Article
            </button>
        </form>
    </div>
    """,
    unsafe_allow_html=True
)

# Capture mode selection safely
if st.experimental_get_query_params().get("mode"):
    st.session_state.mode = st.experimental_get_query_params()["mode"][0]


# ==================================================
# STOP UNTIL MODE SELECTED
# ==================================================
if st.session_state.mode is None:
    st.stop()

# ==================================================
# MODE CONTENT
# ==================================================
st.markdown("<div class='section'>", unsafe_allow_html=True)

if st.session_state.mode == "update":
    st.markdown("### Update existing Bayut article")
    bayut_url = st.text_input(
        "Bayut article URL",
        placeholder="https://www.bayut.com/mybayut/..."
    )
else:
    st.markdown("### Plan a new article from title")
    article_title = st.text_input(
        "Article title",
        placeholder="Pros and Cons of Living in Business Bay"
    )

# ==================================================
# COMPETITORS
# ==================================================
st.markdown("### Competitors")

new_competitor = st.text_input(
    "Competitor URL",
    placeholder="https://example.com/blog/..."
)

col1, col2 = st.columns([1, 3])

with col1:
    if st.button("➕ Add"):
        if new_competitor:
            st.session_state.competitor_urls.append(new_competitor)

with col2:
    if st.button("Clear"):
        st.session_state.competitor_urls = []

if st.session_state.competitor_urls:
    for i, url in enumerate(st.session_state.competitor_urls, start=1):
        st.write(f"{i}. {url}")
else:
    st.markdown("<p style='color:#9ca3af;'>No competitors added yet</p>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# ==================================================
# ACTION
# ==================================================
st.markdown("<div class='section primary-btn'>", unsafe_allow_html=True)
if st.button("Run analysis"):
    st.success("Design locked ✅ Ready for agents")
st.markdown("</div>", unsafe_allow_html=True)
