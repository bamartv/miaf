import json
import os
import requests
from datetime import datetime

TMDB_API_KEY = os.environ.get("TMDB_API_KEY")

ENTRIES_FILE = "entries.json"
OUTPUT_HTML = "index.html"

SRC_URL = "https://api.themoviedb.org/3/discover/{type}"
DETAIL_URL = "https://api.themoviedb.org/3/{type}/{id}"
RELEASE_URL = "https://api.themoviedb.org/3/{type}/{id}/release_dates"
RATING_URL = "https://api.themoviedb.org/3/{type}/{id}/content_ratings"

HEADERS = {"accept": "application/json"}

# =========================
# UTILS
# =========================

def tmdb_get(url, params=None):
    params = params or {}
    params["api_key"] = TMDB_API_KEY
    r = requests.get(url, headers=HEADERS, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

def load_old_entries():
    if not os.path.exists(ENTRIES_FILE):
        return {}
    with open(ENTRIES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {e["id"]: e for e in data}

def save_entries(entries):
    with open(ENTRIES_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)

# =========================
# PEGI EUROPEO
# =========================

def get_pegi(type_, tmdb_id):
    try:
        if type_ == "movie":
            data = tmdb_get(RELEASE_URL.format(type=type_, id=tmdb_id))
            for r in data.get("results", []):
                if r["iso_3166_1"] in ("IT", "FR", "DE", "ES", "GB"):
                    for rel in r.get("release_dates", []):
                        if rel.get("certification"):
                            return rel["certification"]
        else:
            data = tmdb_get(RATING_URL.format(type=type_, id=tmdb_id))
            for r in data.get("results", []):
                if r["iso_3166_1"] in ("IT", "FR", "DE", "ES", "GB"):
                    return r.get("rating")
    except:
        pass
    return ""

# =========================
# FETCH TMDB
# =========================

def fetch_all(type_):
    page = 1
    all_items = []

    while True:
        data = tmdb_get(
            SRC_URL.format(type=type_),
            params={
                "page": page,
                "sort_by": "primary_release_date.desc",
                "language": "it-IT",
            },
        )

        if not data.get("results"):
            break

        all_items.extend(data["results"])

        if page >= data.get("total_pages", page):
            break
        page += 1

    return all_items

# =========================
# BUILD ENTRIES
# =========================

def build_entries():
    old_entries = load_old_entries()
    new_entries = {}

    for type_ in ("movie", "tv"):
        items = fetch_all(type_)

        for it in items:
            tmdb_id = it["id"]
            key = f"{type_}_{tmdb_id}"

            if key in old_entries:
                new_entries[key] = old_entries[key]
                continue

            detail = tmdb_get(
                DETAIL_URL.format(type=type_, id=tmdb_id),
                params={"language": "it-IT"},
            )

            poster = (
                f"https://image.tmdb.org/t/p/w500{detail.get('poster_path')}"
                if detail.get("poster_path")
                else ""
            )

            entry = {
                "id": key,
                "tmdb_id": tmdb_id,
                "type": type_,
                "title": detail.get("title") or detail.get("name") or "",
                "overview": detail.get("overview") or "",
                "poster": poster,
                "year": (detail.get("release_date") or detail.get("first_air_date") or "")[:4],
                "runtime": detail.get("runtime") or (
                    detail.get("episode_run_time")[0]
                    if detail.get("episode_run_time")
                    else ""
                ),
                "genres": [g["name"] for g in detail.get("genres", [])],
                "vote": detail.get("vote_average", 0),
                "age": get_pegi(type_, tmdb_id),
                "added": datetime.utcnow().isoformat(),
            }

            new_entries[key] = entry

    # merge
    merged = {**old_entries, **new_entries}
    return list(merged.values())

# =========================
# BUILD HTML
# =========================

def build_html(entries):
    entries.sort(key=lambda x: x["added"], reverse=True)
    latest = entries[:30]

    def card(item):
        age = f"<div class='badge'>{item['age']}</div>" if item.get("age") else ""
        return f"""
        <div class="card" onclick='openInfo({json.dumps(item)})'>
          <img src="{item['poster']}">
          {age}
        </div>
        """

    latest_html = "".join(card(i) for i in latest)

    return f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<title>TV Home</title>

<style>
body {{
  margin:0;
  font-family: Arial, sans-serif;
  color:#fff;
  background: linear-gradient(180deg,#1e3c72,#2a5298,#0f2027);
}}

.topbar {{
  position:sticky;
  top:0;
  display:flex;
  gap:10px;
  padding:12px 20px;
  background:rgba(10,20,40,.9);
}}

.topbar input, .topbar select, .topbar button {{
  padding:8px 14px;
  border-radius:10px;
  border:none;
  background:#243b6b;
  color:#fff;
}}

.hero {{
  height:45vh;
  padding:40px;
  display:flex;
  flex-direction:column;
  justify-content:flex-end;
  background:
    linear-gradient(to right,rgba(10,20,40,.9),rgba(10,20,40,.3)),
    url('{latest[0]["poster"]}');
  background-size:cover;
}}

.section {{
  padding-left:40px;
  margin-top:30px;
}}

.row {{
  display:flex;
  gap:16px;
  overflow-x:auto;
}}

.card {{
  min-width:180px;
  height:270px;
  border-radius:14px;
  overflow:hidden;
  position:relative;
  cursor:pointer;
}}

.card img {{
  width:100%;
  height:100%;
  object-fit:cover;
}}

.badge {{
  position:absolute;
  bottom:8px;
  left:8px;
  background:rgba(0,0,0,.75);
  padding:4px 8px;
  border-radius:6px;
  font-size:12px;
}}
</style>
</head>

<body>

<div class="topbar">
  <input id="searchBox" placeholder="Cerca...">
  <select id="genreSelect"><option>Tutti</option></select>
  <button id="randomPick">🎲 Random</button>
</div>

<div class="hero">
  <h1>{latest[0]["title"]}</h1>
  <p>{latest[0]["overview"]}</p>
</div>

<div class="section">
  <h2>Ultimi aggiunti</h2>
  <div class="row">{latest_html}</div>
</div>

<script>
const allData = {json.dumps(entries)};
function openInfo(item) {{
  alert(item.title);
}}
</script>

</body>
</html>
"""

# =========================
# MAIN
# =========================

def main():
    entries = build_entries()
    print("Totale entries da salvare:", len(entries))
    save_entries(entries)

    html = build_html(entries)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

if __name__ == "__main__":
    main()
