import requests
import streamlit as st
from typing import Optional

# =============================
# CONFIG
# =============================
API_BASE = "http://127.0.0.1:8000"
TMDB_IMG = "https://image.tmdb.org/t/p/w500"

st.set_page_config(page_title="Movie Recommender", page_icon="🎬", layout="wide")

# =============================
# STYLES
# =============================
st.markdown(
    """
<style>
.block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 1400px; }
.small-muted { color:#6b7280; font-size: 0.92rem; }
.movie-title { font-size: 0.9rem; line-height: 1.15rem; height: 2.3rem; overflow: hidden; }
.card { border: 1px solid rgba(0,0,0,0.08); border-radius: 16px; padding: 14px; background: rgba(255,255,255,0.7); }
</style>
""",
    unsafe_allow_html=True,
)

# =============================
# SESSION STATE
# =============================
if "view" not in st.session_state:
    st.session_state.view = "home"

if "selected_tmdb_id" not in st.session_state:
    st.session_state.selected_tmdb_id = None


# =============================
# NAVIGATION
# =============================
def goto_home():
    st.session_state.view = "home"
    st.rerun()


def goto_details(tmdb_id):
    st.session_state.view = "details"
    st.session_state.selected_tmdb_id = tmdb_id
    st.rerun()


# =============================
# API HELPER
# =============================
@st.cache_data(ttl=300)
def api_get_json(path: str, params: Optional[dict] = None):

    try:

        r = requests.get(
            f"{API_BASE}{path}",
            params=params,
            timeout=25
        )

        if r.status_code >= 400:
            return None, f"HTTP {r.status_code}"

        return r.json(), None

    except Exception as e:

        return None, str(e)


# =============================
# GRID
# =============================
def poster_grid(cards, cols=6):

    if not cards:
        st.info("No movies found")
        return

    rows = (len(cards) + cols - 1) // cols

    idx = 0

    for r in range(rows):

        colset = st.columns(cols)

        for c in range(cols):

            if idx >= len(cards):
                break

            movie = cards[idx]

            idx += 1

            with colset[c]:

                if movie.get("poster_url"):
                    st.image(movie["poster_url"], use_column_width=True)
                else:
                    st.write("No Poster")

                if st.button("Open", key=str(idx)):

                    goto_details(movie["tmdb_id"])

                st.markdown(
                    f"<div class='movie-title'>{movie.get('title')}</div>",
                    unsafe_allow_html=True
                )


# =============================
# SIDEBAR
# =============================
with st.sidebar:

    st.markdown("## 🎬 Menu")

    if st.button("🏠 Home"):
        goto_home()

    st.markdown("---")

    category = st.selectbox(
        "Category",
        [
            "trending",
            "popular",
            "top_rated",
            "now_playing",
            "upcoming"
        ]
    )

    grid_cols = st.slider("Columns", 4, 8, 6)


# =============================
# HEADER
# =============================
st.title("🎬 Movie Recommender")

st.write("Search movies and get recommendations")

st.divider()


# =============================
# HOME PAGE
# =============================
if st.session_state.view == "home":

    query = st.text_input("Search movie")

    st.divider()

    if query:

        data, err = api_get_json(
            "/tmdb/search",
            {"query": query}
        )

        if err:

            st.error(err)

        else:

            cards = []

            if isinstance(data, dict) and "results" in data:

                for m in data["results"]:

                    poster = None

                    if m.get("poster_path"):
                        poster = TMDB_IMG + m["poster_path"]

                    cards.append(
                        {
                            "tmdb_id": m.get("id"),
                            "title": m.get("title"),
                            "poster_url": poster
                        }
                    )

            poster_grid(cards, grid_cols)

    else:

        data, err = api_get_json(
            "/home",
            {
                "category": category,
                "limit": 24
            }
        )

        if err:

            st.error(err)

        else:

            poster_grid(data, grid_cols)


# =============================
# DETAILS PAGE
# =============================
elif st.session_state.view == "details":

    tmdb_id = st.session_state.selected_tmdb_id

    if not tmdb_id:

        st.warning("No movie selected")

        if st.button("Back"):
            goto_home()

        st.stop()

    if st.button("← Back"):
        goto_home()

    data, err = api_get_json(
        f"/movie/id/{tmdb_id}"
    )

    if err:

        st.error(err)

        st.stop()

    left, right = st.columns([1, 2])

    with left:

        if data.get("poster_url"):
            st.image(data["poster_url"])

    with right:

        st.header(data.get("title"))

        st.write("Release:", data.get("release_date"))

        genres = ", ".join([g["name"] for g in data.get("genres", [])])

        st.write("Genres:", genres)

        st.subheader("Overview")

        st.write(data.get("overview"))

    st.divider()

    st.subheader("Recommendations")

    bundle, err = api_get_json(
        "/movie/search",
        {
            "query": data.get("title"),
            "tfidf_top_n": 12,
            "genre_limit": 12
        }
    )

    if not err and bundle:

        tfidf = []

        for x in bundle.get("tfidf_recommendations", []):

            tmdb = x.get("tmdb", {})

            if tmdb.get("tmdb_id"):

                tfidf.append(
                    {
                        "tmdb_id": tmdb["tmdb_id"],
                        "title": tmdb.get("title"),
                        "poster_url": tmdb.get("poster_url")
                    }
                )

        st.markdown("### Similar Movies")

        poster_grid(tfidf, grid_cols)

        st.markdown("### Same Genre")

        poster_grid(bundle.get("genre_recommendations", []), grid_cols)

    else:

        st.info("No recommendations available")