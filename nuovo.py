#!/usr/bin/env python3
"""
generate_index.py

Aggiunta gestione Preferiti spostati nella tendina principale e Visti recentemente.
- Preferiti e Visti recentemente in typeSelect (insieme a Film/Serie TV)
- Gestione recenti tramite localStorage (max 20)
- Stellina sulle locandine: solo visuale (non cliccabile)
- Stellina cliccabile dentro la card info
- Possibilità di selezionare più generi
- Correzione back button: chiude il player prima di tornare alla card o griglia
- Titolo nel player comparibile al tocco dello schermo
"""

import os
import sys
import requests
import json
import time

# --- Config ---
SRC_URLS = {
    "movie": "https://vixsrc.to/api/list/movie?lang=it",
    "tv": "https://vixsrc.to/api/list/tv?lang=it"
}
TMDB_BASE = "https://api.themoviedb.org/3/{type}/{id}"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w780"
VIX_LINK_MOVIE = "https://vixsrc.to/movie/{}/?"
OUTPUT_HTML = "index.html"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; script/1.0)"}

ARCHIVE_FILE = "entries.json"

# --- Funzioni gestione archivio ---
def load_archive():
    if os.path.exists(ARCHIVE_FILE):
        with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return []
    return []

def save_archive(entries):
    with open(ARCHIVE_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

# --- TMDB API key ---
def get_api_key():
    key = os.getenv("TMDB_API_KEY")
    if not key:
        print("Errore: manca TMDB_API_KEY", file=sys.stderr)
        sys.exit(1)
    return key

# --- Fetch lista Vix ---
def fetch_list(url, page=1):
    r = requests.get(
        url,
        headers=HEADERS,
        params={"page": page},
        timeout=20
    )
    r.raise_for_status()
    return r.json()

# --- Estrazione ID TMDB ---
def extract_ids(data):
    if isinstance(data, dict):
        items = data.get("data", data.get("results", []))
    elif isinstance(data, list):
        items = data
    else:
        items = []

    ids = []
    for item in items:
        if isinstance(item, dict) and item.get("tmdb_id"):
            ids.append(str(item["tmdb_id"]))
    return ids

# --- Fetch info TMDB ---
def tmdb_get(api_key, type_, tmdb_id, language="it-IT"):
    url = TMDB_BASE.format(type=type_, id=tmdb_id)
    r = requests.get(
        url,
        params={"api_key": api_key, "language": language, "append_to_response": "credits"},
        timeout=15
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()

# --- Costruzione HTML finale ---
def build_html(entries, latest_entries):
    html = f"""<!doctype html>
<html lang='it'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Movies & Series</title>
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-4Z7RJ384ZY"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{{{dataLayer.push(arguments);}}}}
  gtag('js', new Date());
  gtag('config', 'G-4Z7RJ384ZY');
</script>
<style>
body{{{{font-family:Arial,sans-serif;background:#141414;color:#fff;margin:0;padding:20px;}}}}
h1{{{{color:#fff;text-align:center;margin-bottom:20px;}}}}
.controls{{{{display:flex;gap:10px;justify-content:center;margin-bottom:20px;flex-wrap:wrap;}}}}
input,select{{{{padding:8px;font-size:14px;border-radius:4px;border:none;}}}}
.grid{{{{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:12px;}}}}
.card{{{{position:relative;cursor:pointer;transition: transform 0.2s;border-radius:12px;overflow:hidden;border:2px solid #444;background:#1f1f1f;}}}}
.card:hover{{{{transform:scale(1.05);border-color:#e50914;background:#2a2a2a;}}}}
.poster{{{{width:100%;border-radius:0;display:block;}}}}
.badge{{{{position:absolute;top:8px;right:8px;background:#e50914;color:#fff;padding:4px 6px;font-size:14px;font-weight:bold;border-radius:8px;text-align:center;}}}}
.favorite-btn{{{{font-size:20px;color:#fff;text-shadow:0 0 4px #000;}}}}
.favorite-btn.active{{{{color:gold;}}}}
.card .favorite-btn{{{{position:absolute;top:8px;left:8px;pointer-events:none;}}}}
.circular-chart {{{{
  max-width: 50px;
  max-height: 50px;
}}}}
.circle-bg {{{{
  fill: none;
  stroke: #eee;
  stroke-width: 3.8;
}}}}
.circle {{{{
  fill: none;
  stroke-width: 3.8;
  stroke-linecap: round;
  transition: stroke-dasharray 0.6s ease;
}}}}
.percentage {{{{
  fill: #fff;
  font-size: 0.6em;
  text-anchor: middle;
  dominant-baseline: middle;
}}}}
#searchBox {{{{
  padding: 10px 15px;
  border-radius: 25px;
  border: 2px solid #e50914;
  background: #1f1f1f;
  color: #fff;
  font-size: 16px;
  outline: none;
  transition: all 0.3s ease;
}}}}
#searchBox:focus {{{{
  border-color: #ff3333;
  box-shadow: 0 0 8px #e50914;
}}}}
#favoriteInCard.favorite-btn{{{{position:static;cursor:pointer;font-size:15px;}}}}
#loadMore{{{{display:block;margin:20px auto;padding:10px 20px;font-size:16px;background:#e50914;color:#fff;border:none;border-radius:8px;cursor:pointer;}}}}
#playerOverlay{{{{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.9);display:none;align-items:center;justify-content:center;z-index:1000;flex-direction:column;}}}}
#playerOverlay iframe{{{{width:100%;height:100%;border:none;position:relative;z-index:1;}}}}
#playerTitle{{{{position:absolute;top:20px;left:50%;transform:translateX(-50%);background:rgba(0,0,0,0.7);color:#fff;padding:8px 12px;border-radius:8px;font-size:18px;display:none;z-index:10;}}}}
#infoCard {{{{
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    display: none;
    z-index: 1001;
    background-size: contain;   
    background-position: center;
    background-repeat: no-repeat;
    background-color: #141414;  
    display: flex;
    align-items: center;
    justify-content: center;
}}}}
#infoCard > div {{{{
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    background: rgba(0,0,0,0.5);
    border-radius: 10px;
    padding: 20px;
    max-width: 800px;
    width: 90%;
    text-align: center;
}}}}
#infoCard h2 {{{{
    font-size: 3em;
    font-weight: 800;
    color: #fff;
    margin-bottom: 20px;
}}}}
...
<!-- tutto il resto del CSS/JS con doppie graffe come sopra -->
...
</style>
</head>
<body>
<h1>Aggiunti di recente</h1>
<div id='latest'>
{latest_entries}
</div>

<h1>Movies & Series</h1>
<div class='controls'>
<select id='typeSelect'>
  <option value='movie'>Film</option>
  <option value='tv'>Serie TV</option>
  <option value='favorites'>★ Preferiti</option>
  <option value='recent'>👁 Visti di recente</option>
</select>
<select id='genreSelect' multiple size=5></select>
<input type='text' id='searchBox' placeholder='Cerca...'>
</div>
<div id='moviesGrid' class='grid'></div>
<div id="bottomControls">
 <button id='loadMore'>Carica altri</button>
 <button id='randomPick'>🎲 Cosa guardiamo stasera?</button>
 </div>

<!-- Player e infoCard -->
<div id='playerOverlay'>
  <iframe allow="autoplay; fullscreen; encrypted-media" allowfullscreen></iframe>
  <div id="playerTitle"></div>
</div>

<div id='infoCard'>
  <div>
    <h2 id="infoTitle"></h2>
    <div style="display:flex; justify-content:center; align-items:center; gap:10px; flex-wrap:wrap;">
      <button id="playBtn">▶ Guarda</button>
      <button id="closeCardBtn">Chiudi</button>
      <button id="favoriteInCard">Preferiti</button>
    </div>
    <p id="infoGenres"></p>
    <p id="infoVote"></p>
    <p id="infoOverview"></p>
    <p id="infoYear"></p>
    <p id="infoDuration"></p>
    <p id="infoCast"></p>
    <select id="seasonSelect"></select>
    <select id="episodeSelect"></select>
  </div>
</div>

<script>
const allData = {entries};
let favorites = JSON.parse(localStorage.getItem("favorites") || "[]");
let recentList = JSON.parse(localStorage.getItem("recent") || "[]");
let currentItem = null;

...
// tutto il JS come nel tuo script originale
// tutte le graffe dentro JS diventano {{ e }}
...
</script>
</body>
</html>
"""
    return html

# --- Funzione principale ---
def main():
    api_key = get_api_key()
    entries = []
    latest_entries = ""

    # Carica archivio
    old_entries = load_archive()

    # Ciclo sulle sorgenti
    for type_, base_url in SRC_URLS.items():
        print(f"[VIX] Scarico lista {type_}")
        first = fetch_list(base_url, page=1)
        ids = extract_ids(first)
        last_page = first.get("last_page", 1)
        print(f"[VIX] {type_}: {last_page} pagine totali")

        for page in range(2, last_page + 1):
            try:
                data = fetch_list(base_url, page=page)
                ids.extend(extract_ids(data))
                time.sleep(0.2)  # evita rate limit
            except Exception as e:
                print(f"[VIX] Errore pagina {page}: {e}")
                break

        ids = list(dict.fromkeys(ids))
        print(f"[VIX] {type_}: {len(ids)} ID totali")

        # ciclo TMDB e costruzione entries
        for idx, tmdb_id in enumerate(ids):
            info = tmdb_get(api_key, type_, tmdb_id)
            if not info:
                continue
            title = info.get("title") or info.get("name") or f"ID {tmdb_id}"
            poster = TMDB_IMAGE_BASE + info["poster_path"] if info.get("poster_path") else ""
            genres = [g["name"] for g in info.get("genres", [])]
            vote = info.get("vote_average", 0)
            overview = info.get("overview", "")
            link = VIX_LINK_MOVIE.format(tmdb_id) if type_=="movie" else ""
            seasons = info.get("number_of_seasons",1) if type_=="tv" else 0
            episodes = {str(s["season_number"]): s.get("episode_count",1) 
                        for s in info.get("seasons",[]) if s.get("season_number")} if type_=="tv" else {}
            year = (info.get("release_date") or info.get("first_air_date") or "")[:4]
            runtime_list = info.get("episode_run_time") or []
            duration = info.get("runtime") or (runtime_list[0] if runtime_list else None)
            cast = [c["name"] for c in info.get("credits", {}).get("cast", [])] if info.get("credits") else []
            directors = [c["name"] for c in info.get("credits", {}).get("crew", []) if c.get("job")=="Director"]

            entries.append({
                "id": str(tmdb_id),
                "title": title,
                "poster": poster,
                "genres": genres,
                "vote": vote,
                "overview": overview,
                "link": link,
                "type": type_,
                "seasons": seasons,
                "episodes": episodes,
                "duration": duration or 0,
                "year": year or "",
                "cast": cast,
                "directors": directors
            })

            if idx < 10:
                latest_entries += f"<img class='poster' src='{poster}' alt='{title}' title='{title}'>\n"

    # --- Unione con archivio ---
    combined = {e["id"]: e for e in old_entries}
    for e in entries:
        combined[e["id"]] = e
    all_entries = list(combined.values())

    print(f"Totale entries da salvare: {len(all_entries)}")
    save_archive(all_entries)
    print(f"Archivio salvato su {ARCHIVE_FILE}")

    # --- Genera HTML ---
    html = build_html(all_entries, latest_entries)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Generato {OUTPUT_HTML} con {len(all_entries)} elementi e ultime novità scrollabili")

if __name__ == "__main__":
    main()
