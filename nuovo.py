import requests
import time
import os
from datetime import datetime

API_KEY = os.getenv("TMDB_API_KEY")
BASE = "https://api.themoviedb.org/3"

LANG = "it-IT"
REGION = "IT"

HEADERS = {
    "accept": "application/json"
}

# ---------------------------
# TMDB SAFE REQUEST
# ---------------------------
def tmdb_get(endpoint, params=None):
    try:
        r = requests.get(
            f"{BASE}{endpoint}",
            params=params,
            headers=HEADERS,
            timeout=10
        )
        if r.status_code != 200:
            return None
        return r.json()
    except requests.RequestException:
        return None

# ---------------------------
# FETCH ALL MOVIES
# ---------------------------
def fetch_all():
    results = []

    page = 1
    while page <= 500:
        data = tmdb_get(
            "/discover/movie",
            {
                "api_key": API_KEY,
                "language": LANG,
                "sort_by": "primary_release_date.desc",
                "page": page,
                "include_adult": "false"
            }
        )

        if not data or "results" not in data:
            break

        results.extend(data["results"])

        if page >= data.get("total_pages", 0):
            break

        page += 1

    return results

# ---------------------------
# PEGI SOLO EUROPA
# ---------------------------
def get_pegi_eu(movie_id):
    data = tmdb_get(
        f"/movie/{movie_id}/release_dates",
        {"api_key": API_KEY}
    )

    if not data:
        return None

    for country in data.get("results", []):
        if country["iso_3166_1"] in ("IT", "FR", "DE", "ES"):
            for r in country.get("release_dates", []):
                cert = r.get("certification")
                if cert:
                    return cert

    return None

# ---------------------------
# BUILD SINGLE ENTRY
# ---------------------------
def build_entry(movie):
    movie_id = movie.get("id")
    if not movie_id:
        return None

    detail = tmdb_get(
        f"/movie/{movie_id}",
        {
            "api_key": API_KEY,
            "language": LANG
        }
    )

    if not detail:
        return None

    return {
        "id": movie_id,
        "title": detail.get("title") or detail.get("original_title"),
        "overview": detail.get("overview", ""),
        "poster": f"https://image.tmdb.org/t/p/w500{detail['poster_path']}" if detail.get("poster_path") else "",
        "backdrop": f"https://image.tmdb.org/t/p/w780{detail['backdrop_path']}" if detail.get("backdrop_path") else "",
        "genres": [g["name"] for g in detail.get("genres", [])],
        "release_date": detail.get("release_date"),
        "vote": detail.get("vote_average"),
        "pegi": get_pegi_eu(movie_id),
        "added": int(time.time())
    }

# ---------------------------
# BUILD ALL ENTRIES
# ---------------------------
def build_entries():
    movies = fetch_all()
    entries = []

    for m in movies:
        entry = build_entry(m)
        if entry:
            entries.append(entry)

    return entries

# ---------------------------
# BUILD HTML
# ---------------------------
def build_html(entries):
    entries.sort(key=lambda x: x.get("added", 0), reverse=True)

    cards = []
    for e in entries[:200]:
        cards.append(f"""
        <div class="card">
            <img src="{e['poster']}" />
            <div class="title">{e['title']}</div>
            <div class="pegi">{e['pegi'] or ''}</div>
        </div>
        """)

    return f"""
<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<title>Catalogo Film</title>
<style>
body {{
    margin:0;
    font-family: Arial, sans-serif;
    background: linear-gradient(135deg, #ff512f, #dd2476);
    color: white;
}}
.grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(160px,1fr));
    gap: 15px;
    padding: 20px;
}}
.card {{
    background: rgba(0,0,0,0.4);
    border-radius: 10px;
    overflow: hidden;
    text-align: center;
}}
.card img {{
    width: 100%;
}}
.title {{
    padding: 5px;
    font-size: 14px;
}}
.pegi {{
    font-size: 12px;
    opacity: 0.8;
}}
</style>
</head>
<body>
<h1 style="padding:20px;">🎬 Ultimi aggiunti</h1>
<div class="grid">
{''.join(cards)}
</div>
</body>
</html>
"""

# ---------------------------
# MAIN
# ---------------------------
def main():
    entries = build_entries()
    print(f"Totale entries da salvare: {len(entries)}")

    html = build_html(entries)

    with open("index2.html", "w", encoding="utf-8") as f:
        f.write(html)

# ---------------------------
if __name__ == "__main__":
    main()
