"""
Balanced Movie Recommender UI - Clean & Modern
"""

import requests
import streamlit as st

# ── Config ─────────────────────────────────────────────────────────────────────
API_BASE = "http://localhost:8000"

st.set_page_config(
    page_title="CineMatch",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Custom CSS (Light Touch) ───────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        font-size: 2.8rem;
        font-weight: 700;
        color: #e8c547;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #aaaaaa;
        margin-bottom: 2rem;
    }
    .movie-card {
        background-color: #1e1e2e;
        border-radius: 12px;
        padding: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        transition: transform 0.2s;
    }
    .movie-card:hover {
        transform: translateY(-5px);
    }
    .stButton>button {
        height: 52px;
        font-size: 1.1rem;
    }
</style>
""", unsafe_allow_html=True)

# ── API Helper ─────────────────────────────────────────────────────────────────
def api_call(path: str, params: dict = None):
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=60)
        if r.status_code == 200:
            return r.json()
        st.error(f"API Error: {r.status_code}")
    except requests.exceptions.ConnectionError:
        st.error("❌ Backend not running. Start FastAPI on http://localhost:8000")
    except requests.exceptions.Timeout:
        st.error("⏱️ Timeout - Try fewer recommendations or disable posters")
    except Exception as e:
        st.error(f"Error: {e}")
    return None


def get_poster(url):
    return url if url else "https://via.placeholder.com/200x300/2a2a2a/aaaaaa?text=No+Poster"


#  Header 
st.markdown('<h1 class="main-header">CineMatch</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Discover your next favorite movie</p>', unsafe_allow_html=True)

#  Tabs
tab1, tab2, tab3 = st.tabs(["🎯 Recommendations", "🔍 Search", "🎞 Movie Lookup"])


#  TAB 1: RECOMMENDATIONS

with tab1:
    col1, col2 = st.columns([5, 2])
    with col1:
        title = st.text_input("Enter a movie you enjoyed", placeholder="Inception, Interstellar, The Dark Knight", key="rec_input")
    with col2:
        go = st.button("Get Recommendations", type="primary", use_container_width=True)

    c1, c2, c3 = st.columns([2, 2, 3])
    with c1:
        top_n = st.slider("How many recommendations?", 5, 20, 10)
    with c2:
        enrich = st.toggle("Show Posters", value=True)
    with c3:
        mode = st.radio("Mode", ["Bundle (Best)", "TF-IDF Only"], horizontal=True)

    if go and title.strip():
        with st.spinner("Finding similar movies..."):
            if mode == "Bundle (Best)":
                data = api_call("/recommend/bundle", {"title": title.strip(), "top_n": top_n})
                if data:
                    if data.get("movie_details"):
                        d = data["movie_details"]
                        st.subheader(f"🎬 {d.get('title')} ({d.get('year')})")
                        col_a, col_b = st.columns([2, 5])
                        with col_a:
                            st.image(get_poster(d.get("poster_url")), width=180)
                        with col_b:
                            st.write(f"⭐ **{d.get('imdb_rating')}** | {d.get('runtime')}")
                            st.write(f"**Genre:** {d.get('genre')}")
                            st.write(d.get("plot", ""))
                        st.divider()

                    recs = data.get("tfidf_recommendations", [])
                    if recs:
                        st.subheader(f"Recommended because you liked **{title}**")
                        cols = st.columns(5)
                        for i, rec in enumerate(recs):
                            omdb = rec.get("omdb") or {}
                            with cols[i % 5]:
                                st.image(get_poster(omdb.get("poster_url")), use_container_width=True)
                                st.markdown(f"**{omdb.get('title') or rec['title']}**")
                                st.caption(f"Score: {rec['score']:.3f} • {omdb.get('year','')}")
            else:
                recs = api_call("/recommend/tfidf", {
                    "title": title.strip(), "top_n": top_n, "enrich": enrich
                })
                if recs:
                    st.subheader(f"Similar to **{title}**")
                    cols = st.columns(5)
                    for i, rec in enumerate(recs):
                        omdb = rec.get("omdb") or {}
                        with cols[i % 5]:
                            if enrich:
                                st.image(get_poster(omdb.get("poster_url")), use_container_width=True)
                            st.markdown(f"**{omdb.get('title') or rec['title']}**")
                            st.caption(f"Score: {rec['score']:.3f}")


#  TAB 2: SEARCH

with tab2:
    col1, col2 = st.columns([5, 2])
    with col1:
        query = st.text_input("Search any movie or series", placeholder="The Batman", key="search_input")
    with col2:
        search_btn = st.button("Search", use_container_width=True)

    if search_btn and query.strip():
        with st.spinner("Searching..."):
            results = api_call("/search", {"query": query.strip(), "page": 1})
            if results:
                cols = st.columns(4)
                for i, item in enumerate(results):
                    with cols[i % 4]:
                        st.image(get_poster(item.get("poster_url")), use_container_width=True)
                        st.write(f"**{item.get('title')}**")
                        st.caption(f"{item.get('year')} • {item.get('type')}")


#  TAB 3: MOVIE LOOKUP

with tab3:
    lookup_mode = st.radio("Lookup by", ["Title", "IMDb ID"], horizontal=True)
    
    col1, col2 = st.columns([5, 2])
    with col1:
        value = st.text_input(
            "Enter Title or IMDb ID", 
            placeholder="Oppenheimer" if lookup_mode == "Title" else "tt15398776"
        )
    with col2:
        lookup_btn = st.button("Get Details", use_container_width=True)

    if lookup_btn and value.strip():
        with st.spinner("Fetching movie info..."):
            if lookup_mode == "Title":
                data = api_call(f"/movie/title/{value.strip()}")
            else:
                data = api_call(f"/movie/imdb/{value.strip()}")
            
            if data:
                st.image(get_poster(data.get("poster_url")), width=220)
                st.subheader(f"{data.get('title')} ({data.get('year')})")
                st.write(f"⭐ **{data.get('imdb_rating')}**   |   {data.get('runtime')}   |   {data.get('genre')}")
                st.write(f"**Director:** {data.get('director')}")
                st.write(f"**Cast:** {data.get('actors')}")
                st.write("**Plot:**")
                st.write(data.get("plot", "No plot available."))

