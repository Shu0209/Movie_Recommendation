"""
CineMatch — Redesigned Streamlit UI (Fixed)
"""

import requests
import streamlit as st

# ── Config ─────────────────────────────────────────────────────────────────────
API_BASE = "https://movie-recommendation-1gns.onrender.com"

st.set_page_config(
    page_title="CineMatch",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">

<style>
/* Base */
html, body, [data-testid="stAppViewContainer"] {
    background-color: #080810 !important;
    color: #d8d8e8;
    font-family: 'DM Sans', sans-serif;
}
[data-testid="stMain"] { background-color: #080810 !important; }
[data-testid="block-container"] { padding: 2rem 3rem; }

/* Hero */
.hero-wrap {
    display: flex;
    align-items: baseline;
    gap: 14px;
    margin-bottom: 0.2rem;
}
.hero-title {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 4.2rem;
    letter-spacing: 0.06em;
    color: #ffffff;
    line-height: 1;
}
.hero-dot { color: #e8c547; font-size: 4rem; }
.hero-sub {
    font-size: 0.82rem;
    font-weight: 300;
    letter-spacing: 0.22em;
    color: #666688;
    text-transform: uppercase;
}

/* Tabs */
[data-testid="stTabs"] > div:first-child {
    border-bottom: 1px solid #1e1e30;
    margin-bottom: 2rem;
}
[data-testid="stTabs"] button {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.18em !important;
    text-transform: uppercase !important;
    color: #555570 !important;
    padding: 0.8rem 1.6rem !important;
    border-bottom: 2px solid transparent !important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: #e8c547 !important;
    border-bottom: 2px solid #e8c547 !important;
}

/* Inputs */
[data-testid="stTextInput"] input {
    background-color: #0e0e1c !important;
    border: 1px solid #1e1e30 !important;
    border-radius: 4px !important;
    color: #d8d8e8 !important;
    padding: 0.75rem 1rem !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: #e8c547 !important;
    box-shadow: 0 0 0 2px rgba(232, 197, 71, 0.2) !important;
}

/* Buttons */
.stButton > button {
    background: #e8c547 !important;
    color: #080810 !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase;
    padding: 0.75rem !important;
    border-radius: 4px !important;
}
.stButton > button:hover {
    background: #f0d060 !important;
    transform: translateY(-1px);
}

/* Movie Cards */
.movie-card {
    background: #0e0e1c;
    border: 1px solid #1a1a2e;
    border-radius: 6px;
    overflow: hidden;
    transition: all 0.25s;
    height: 100%;
}
.movie-card:hover {
    border-color: #e8c547;
    transform: translateY(-4px);
}
.movie-card img {
    width: 100%;
    aspect-ratio: 2/3;
    object-fit: cover;
}
.movie-card-body { padding: 12px; }
.movie-card-title {
    font-weight: 600;
    font-size: 0.9rem;
    margin: 0 0 6px 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.movie-card-meta {
    font-size: 0.78rem;
    color: #666688;
    display: flex;
    justify-content: space-between;
}
.movie-card-score { color: #e8c547; font-weight: 600; }

/* Result Rows */
.result-row {
    display: flex;
    gap: 16px;
    padding: 14px;
    background: #0e0e1c;
    border: 1px solid #1a1a2e;
    border-radius: 6px;
    margin-bottom: 12px;
}
.result-row:hover { border-color: #e8c54760; }
.result-row img { width: 60px; border-radius: 4px; flex-shrink: 0; }

/* Other */
.section-label {
    font-size: 0.73rem;
    font-weight: 600;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #e8c547;
    margin: 1.5rem 0 0.8rem 0;
}
hr { border-color: #1e1e30 !important; }
</style>
""", unsafe_allow_html=True)

# ── API Helper ─────────────────────────────────────────────────────────────
def api(path: str, params: dict = None):
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=60)
        if r.status_code == 200:
            return r.json()
        st.error(f"API Error: {r.status_code}")
        return None
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to backend. Make sure FastAPI is running on http://localhost:8000")
        return None
    except Exception as e:
        st.error(f"Error: {e}")
        return None

PLACEHOLDER = "https://via.placeholder.com/200x300/0e0e1c/555577?text=No+Poster"

def poster(url):
    return url if url and url != "N/A" else PLACEHOLDER

# ── Hero ───────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-wrap">
    <span class="hero-title">CineMatch</span>
    <span class="hero-dot">·</span>
</div>
<div class="hero-sub">Powered by OMDB &nbsp;✦&nbsp; TF-IDF</div>
""", unsafe_allow_html=True)

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_rec, tab_search, tab_lookup = st.tabs(["Recommendations", "Search", "Lookup"])

# ====================== RECOMMENDATIONS ======================
with tab_rec:
    st.markdown('<div class="section-label">Find Similar Movies</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([6, 1], gap="small")
    with col1:
        rec_title = st.text_input("Enter movie title", 
                                  placeholder="Inception, Parasite, Dune...", 
                                  key="rec_input")
    with col2:
        rec_go = st.button("Search", type="primary", key="rec_btn")

    if rec_go and rec_title.strip():
        with st.spinner("Fetching recommendations..."):
            data = api("/recommend/bundle", {"title": rec_title.strip(), "top_n": 12})

        if data:
            movie = data.get("movie_details", {})
            if movie:
                st.success(f"**{movie.get('title')}** ({movie.get('year', '')})")
                if movie.get("plot"):
                    st.caption(movie["plot"][:280] + "...")

            recs = data.get("tfidf_recommendations", [])
            if recs:
                st.markdown(f'<div class="section-label">Because you liked <b>{rec_title}</b></div>', 
                           unsafe_allow_html=True)
                
                cols = st.columns(4, gap="small")
                for i, rec in enumerate(recs[:12]):
                    omdb = rec.get("omdb") or {}
                    title = omdb.get("title") or rec.get("title", "Unknown")
                    with cols[i % 4]:
                        st.markdown(f"""
                        <div class="movie-card">
                            <img src="{poster(omdb.get('poster_url'))}" alt="{title}">
                            <div class="movie-card-body">
                                <div class="movie-card-title">{title}</div>
                                <div class="movie-card-meta">
                                    <span>{omdb.get('year', '')}</span>
                                    <span class="movie-card-score">↑ {rec.get('score', 0):.2f}</span>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("No recommendations found.")
    else:
        st.info("Enter a movie title to get recommendations.")

# ====================== SEARCH ======================
with tab_search:
    st.markdown('<div class="section-label">Search Movies & Series</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([6, 1], gap="small")
    with col1:
        query = st.text_input("Search", 
                              placeholder="The Matrix, Breaking Bad...", 
                              key="search_input")
    with col2:
        search_go = st.button("Search", type="primary", key="search_btn")

    if search_go and query.strip():
        with st.spinner("Searching OMDB..."):
            results = api("/search", {"query": query.strip(), "page": 1})

        if results:
            for item in results:
                imdb_id = item.get("imdb_id", "")
                st.markdown(f"""
                <div class="result-row">
                    <img src="{poster(item.get('poster_url'))}" alt="{item.get('title')}">
                    <div>
                        <div style="font-weight:600; font-size:0.98rem;">{item.get('title', 'Unknown')}</div>
                        <div style="color:#666688; font-size:0.82rem;">
                            {item.get('year', '')} • {item.get('type','movie').capitalize()}
                            {f'• <a href="https://www.imdb.com/title/{imdb_id}" target="_blank" style="color:#e8c547">IMDb</a>' if imdb_id else ''}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("No results found.")
    else:
        st.info("Search for movies, series, or episodes.")

# ====================== LOOKUP ======================
with tab_lookup:
    st.markdown('<div class="section-label">Movie Detail Lookup</div>', unsafe_allow_html=True)
    
    mode = st.radio("Lookup by", ["Title", "IMDb ID"], horizontal=True, key="lookup_mode")
    
    col1, col2 = st.columns([6, 1], gap="small")
    with col1:
        val = st.text_input("Enter value", 
                            placeholder="The Godfather" if mode == "Title" else "tt0068646", 
                            key="lookup_input")
    with col2:
        lookup_go = st.button("Lookup", type="primary", key="lookup_btn")

    if lookup_go and val.strip():
        with st.spinner("Fetching movie details..."):
            if mode == "Title":
                data = api(f"/movie/title/{val.strip()}")
            else:
                data = api(f"/movie/imdb/{val.strip()}")

        if data:
            col_p, col_d = st.columns([1, 2], gap="large")
            with col_p:
                st.image(poster(data.get("poster_url")), use_column_width=True)
            
            with col_d:
                st.subheader(data.get("title", "Movie"))
                st.caption(f"{data.get('year')} • {data.get('runtime')} • {data.get('genre')}")
                st.write(data.get("plot", "No plot available."))
                
                st.metric("IMDb Rating", data.get("imdb_rating", "N/A"))
                st.write(f"**Director:** {data.get('director', '—')}")
                st.write(f"**Cast:** {data.get('actors', '—')}")
    else:
        st.info("Enter a title or IMDb ID to see full details.")

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<p style='text-align:center; color:#444466; font-size:0.8rem;'>"
    "CineMatch • OMDB + TF-IDF</p>",
    unsafe_allow_html=True
)