
import os
import pickle
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Tuple

import httpx
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

# OMDB config
OMDB_API_KEY: Optional[str] = os.getenv("OMDB_API_KEY")
OMDB_BASE_URL = "https://www.omdbapi.com/"  

#Pickle paths 
BASE_DIR          = os.path.dirname(os.path.abspath(__file__))
DF_PATH           = os.path.join(BASE_DIR, "df.pkl")
INDICES_PATH      = os.path.join(BASE_DIR, "indices.pkl")
TFIDF_MATRIX_PATH = os.path.join(BASE_DIR, "tfidf_metrix.pkl")
TFIDF_PATH        = os.path.join(BASE_DIR, "tfidf.pkl")

# Global state 
df:           Optional[pd.DataFrame]   = None
indices_obj:  Any                      = None
tfidf_matrix: Any                      = None
tfidf_obj:    Any                      = None
TITLE_TO_IDX: Optional[Dict[str, int]] = None


# Lifespan 
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load pickled model artefacts once at startup."""
    global df, indices_obj, tfidf_matrix, tfidf_obj, TITLE_TO_IDX

    with open(DF_PATH, "rb") as f:
        df = pickle.load(f)
    with open(INDICES_PATH, "rb") as f:
        indices_obj = pickle.load(f)
    with open(TFIDF_MATRIX_PATH, "rb") as f:
        tfidf_matrix = pickle.load(f)
    with open(TFIDF_PATH, "rb") as f:
        tfidf_obj = pickle.load(f)

    if df is None or "title" not in df.columns:
        raise RuntimeError("df.pkl must contain a DataFrame with a 'title' column")

    TITLE_TO_IDX = build_title_to_idx_map(indices_obj)
    yield 


# ── App
app = FastAPI(title="Movie Recommender API", version="1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class OMDBMovieCard(BaseModel):
    """Lightweight card returned by search (`s` param)."""
    imdb_id:    str
    title:      str
    year:       Optional[str] = None
    poster_url: Optional[str] = None
    type:       Optional[str] = None  


class OMDBMovieDetails(BaseModel):
    """Full detail record returned by title / IMDb-ID lookup."""
    imdb_id:     str
    title:       str
    year:        Optional[str] = None
    rated:       Optional[str] = None
    released:    Optional[str] = None
    runtime:     Optional[str] = None
    genre:       Optional[str] = None  
    director:    Optional[str] = None
    actors:      Optional[str] = None
    plot:        Optional[str] = None
    language:    Optional[str] = None
    country:     Optional[str] = None
    awards:      Optional[str] = None
    poster_url:  Optional[str] = None
    imdb_rating: Optional[str] = None
    imdb_votes:  Optional[str] = None
    box_office:  Optional[str] = None
    type:        Optional[str] = None


class TFIDFRecItem(BaseModel):
    title: str
    score: float
    omdb:  Optional[OMDBMovieCard] = None


class SearchBundleResponse(BaseModel):
    query:                 str
    movie_details:         Optional[OMDBMovieDetails]
    tfidf_recommendations: List[TFIDFRecItem]


# Low-level OMDB helper 
def _poster(url: Optional[str]) -> Optional[str]:
    """OMDB already returns full poster URLs; just discard the 'N/A' sentinel."""
    if not url or url.strip().upper() == "N/A":
        return None
    return url


async def omdb_get(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send a GET to the single OMDB endpoint with `apikey` injected.
    Raises HTTPException on network errors, non-200 status, or
    OMDB's own {"Response":"False"} error envelope.
    """
    if not OMDB_API_KEY:
        raise HTTPException(status_code=500, detail="OMDB_API_KEY is not set")

    q = dict(params)
    q["apikey"] = OMDB_API_KEY          # OMDB uses 'apikey', not 'api_key'

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(OMDB_BASE_URL, params=q)
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502,
            detail=f"OMDB network error: {type(e).__name__}: {repr(e)}",
        )

    if r.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"OMDB returned HTTP {r.status_code}: {r.text}",
        )

    data = r.json()

    # OMDB signals failures inside a 200 response
    if data.get("Response") == "False":
        raise HTTPException(
            status_code=404,
            detail=f"OMDB error: {data.get('Error', 'Unknown error')}",
        )

    return data


# OMDB response parsers 
def _parse_details(data: Dict[str, Any]) -> OMDBMovieDetails:
    return OMDBMovieDetails(
        imdb_id     = data.get("imdbID", ""),
        title       = data.get("Title", ""),
        year        = data.get("Year"),
        rated       = data.get("Rated"),
        released    = data.get("Released"),
        runtime     = data.get("Runtime"),
        genre       = data.get("Genre"),
        director    = data.get("Director"),
        actors      = data.get("Actors"),
        plot        = data.get("Plot"),
        language    = data.get("Language"),
        country     = data.get("Country"),
        awards      = data.get("Awards"),
        poster_url  = _poster(data.get("Poster")),
        imdb_rating = data.get("imdbRating"),
        imdb_votes  = data.get("imdbVotes"),
        box_office  = data.get("BoxOffice"),
        type        = data.get("Type"),
    )


def _parse_card(item: Dict[str, Any]) -> OMDBMovieCard:
    return OMDBMovieCard(
        imdb_id    = item.get("imdbID", ""),
        title      = item.get("Title", ""),
        year       = item.get("Year"),
        poster_url = _poster(item.get("Poster")),
        type       = item.get("Type"),
    )


# OMDB query wrappers 
async def omdb_by_title(title: str, plot: str = "full") -> OMDBMovieDetails:
    """Best-match lookup by title (`t` param)."""
    data = await omdb_get({"t": title, "type": "movie", "plot": plot})
    return _parse_details(data)


async def omdb_by_imdb_id(imdb_id: str, plot: str = "full") -> OMDBMovieDetails:
    """Exact lookup by IMDb ID (`i` param)."""
    data = await omdb_get({"i": imdb_id, "plot": plot})
    return _parse_details(data)


async def omdb_search(
    query: str, page: int = 1, media_type: str = "movie"
) -> Dict[str, Any]:
    """
    Title keyword search (`s` param).
    Raw response: {"Search": [...], "totalResults": "N", "Response": "True"}
    """
    return await omdb_get({"s": query, "type": media_type, "page": page})


async def omdb_search_first(query: str) -> Optional[OMDBMovieCard]:
    """Return the first search hit as a lightweight card, or None on failure."""
    try:
        data = await omdb_search(query, page=1)
        hits = data.get("Search", [])
        return _parse_card(hits[0]) if hits else None
    except HTTPException:
        return None


# TF-IDF helpers
def build_title_to_idx_map(indices: Any) -> Dict[str, int]:
    title_to_idx: Dict[str, int] = {}
    try:
        for k, v in indices.items():  
            title_to_idx[_norm_title(k)] = int(v)
    except Exception:
        raise RuntimeError(
            "indices.pkl must be a dict or pandas Series (supporting .items())"
        )
    return title_to_idx


def _norm_title(t: str) -> str:
    return str(t).strip().lower()


def get_local_idx_by_title(title: str) -> int:
    global TITLE_TO_IDX
    if TITLE_TO_IDX is None:
        raise HTTPException(status_code=500, detail="TF-IDF index map not initialized")
    key = _norm_title(title)
    if key in TITLE_TO_IDX:
        return int(TITLE_TO_IDX[key])
    raise HTTPException(
        status_code=404,
        detail=f"Title not found in local dataset: '{title}'",
    )


def tfidf_recommend_title(
    query_title: str, top_n: int = 10
) -> List[Tuple[str, float]]:
    global df, tfidf_matrix
    if df is None or tfidf_matrix is None:
        raise HTTPException(status_code=500, detail="TF-IDF resources not loaded")

    idx    = get_local_idx_by_title(query_title)
    qv     = tfidf_matrix[idx]
    scores = (tfidf_matrix @ qv.T).toarray().ravel()
    order  = np.argsort(-scores)

    out: List[Tuple[str, float]] = []
    for i in order:
        if int(i) == int(idx):
            continue
        try:
            title_i = str(df.iloc[int(i)]["title"])
        except Exception:
            continue
        out.append((title_i, float(scores[int(i)])))
        if len(out) >= top_n:
            break
    return out


# Routes

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/movie/title/{title}", response_model=OMDBMovieDetails)
async def movie_by_title(
    title: str,
    plot: str = Query("full", pattern="^(short|full)$"),
):
    """
    Full movie details from OMDB by title.
    Example: GET /movie/title/Inception
    """
    return await omdb_by_title(title, plot=plot)


@app.get("/movie/imdb/{imdb_id}", response_model=OMDBMovieDetails)
async def movie_by_imdb_id(
    imdb_id: str,
    plot: str = Query("full", pattern="^(short|full)$"),
):
    """
    Full movie details from OMDB by IMDb ID.
    Example: GET /movie/imdb/tt1375666
    """
    return await omdb_by_imdb_id(imdb_id, plot=plot)


@app.get("/search", response_model=List[OMDBMovieCard])
async def search_movies(
    query: str = Query(..., min_length=1, description="Search term"),
    page:  int = Query(1, ge=1, le=100, description="Page number (10 results / page)"),
    type:  str = Query("movie", pattern="^(movie|series|episode)$"),
):
    """
    Keyword search via OMDB.  Returns up to 10 cards per page.
    Example: GET /search?query=batman&page=1
    """
    data = await omdb_search(query=query, page=page, media_type=type)
    hits = data.get("Search", [])
    return [_parse_card(h) for h in hits]


@app.get("/recommend/tfidf", response_model=List[TFIDFRecItem])
async def recommend_tfidf(
    title:  str  = Query(..., min_length=1, description="Movie title in local dataset"),
    top_n:  int  = Query(10, ge=1, le=50),
    enrich: bool = Query(
        False,
        description=(
            "Attach OMDB poster/year to each result. "
            "Makes one OMDB search request per recommendation — slower."
        ),
    ),
):
    """
    Content-based TF-IDF recommendations from the local model.
    Example: GET /recommend/tfidf?title=Inception&top_n=10&enrich=true
    """
    recs = tfidf_recommend_title(title, top_n=top_n)
    out: List[TFIDFRecItem] = []
    for rec_title, score in recs:
        card = await omdb_search_first(rec_title) if enrich else None
        out.append(TFIDFRecItem(title=rec_title, score=round(score, 4), omdb=card))
    return out


@app.get("/recommend/bundle", response_model=SearchBundleResponse)
async def recommend_bundle(
    title: str = Query(..., min_length=1, description="Movie title"),
    top_n: int = Query(10, ge=1, le=30),
    plot:  str = Query("short", pattern="^(short|full)$"),
):
    """
    All-in-one endpoint:
      1. Fetches OMDB details for the requested title.
      2. Runs TF-IDF recommendations from the local model.
      3. Enriches each recommendation with an OMDB card (poster + year).

    OMDB lookup is best-effort — recommendations are still returned even if
    the title is not found on OMDB.

    Example: GET /recommend/bundle?title=Inception&top_n=10
    """
    # Step 1 — OMDB details (non-fatal if title not found)
    details: Optional[OMDBMovieDetails] = None
    try:
        details = await omdb_by_title(title, plot=plot)
    except HTTPException:
        pass

    # Step 2 — TF-IDF recommendations enriched with OMDB cards
    recs = tfidf_recommend_title(title, top_n=top_n)
    items: List[TFIDFRecItem] = []
    for rec_title, score in recs:
        card = await omdb_search_first(rec_title)
        items.append(TFIDFRecItem(title=rec_title, score=round(score, 4), omdb=card))

    return SearchBundleResponse(
        query=title,
        movie_details=details,
        tfidf_recommendations=items,
    )