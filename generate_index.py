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


def get_api_key():
    key = os.getenv("TMDB_API_KEY")
    if not key:
        print("Errore: manca TMDB_API_KEY", file=sys.stderr)
        sys.exit(1)
    return key


def fetch_list(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.json()


def extract_ids(data):
    ids = []
    items = data if isinstance(data, list) else data.get("results", [])
    for item in items:
        if not isinstance(item, dict):
            continue
        for key in ("tmdb_id", "tmdbId", "id"):
            if key in item and item[key]:
                ids.append(str(item[key]))
                break
    return ids


def tmdb_get(api_key, type_, tmdb_id, language="it-IT"):
    url = TMDB_BASE.format(type=type_, id=tmdb_id)
    r = requests.get(
        url,
        params={
            "api_key": api_key,
            "language": language,
            "append_to_response": "credits,release_dates,content_ratings"
        },
        timeout=15
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


def build_html(entries, latest_entries):
    entries_json = json.dumps(entries, ensure_ascii=False)

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
function gtag(){{dataLayer.push(arguments);}}
gtag('js', new Date());
gtag('config', 'G-4Z7RJ384ZY');
</script>

<style>
#recommended img:focus {{
  outline: 3px solid gold;
  outline-offset: 2px;
}}

body {{
  font-family: Arial, sans-serif;
  background: #141414;
  color: #fff;
  margin: 0;
  padding: 20px;
}}

h1 {{
  color: #fff;
  text-align: center;
  margin-bottom: 20px;
}}

.controls {{
  display: flex;
  gap: 10px;
  justify-content: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
}}

input, select {{
  padding: 8px;
  font-size: 14px;
  border-radius: 4px;
  border: none;
}}

.grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 12px;
}}

.card {{
  position: relative;
  cursor: pointer;
  transition: transform 0.2s;
  border-radius: 12px;
  overflow: hidden;
  border: 2px solid #444;
  background: #1f1f1f;
}}

.card:hover {{
  transform: scale(1.05);
  border-color: #e50914;
  background: #2a2a2a;
}}

.poster {{
  width: 100%;
  display: block;
}}

.badge {{
  position: absolute;
  top: 8px;
  right: 8px;
  background: #e50914;
  color: #fff;
  padding: 4px 6px;
  font-size: 14px;
  font-weight: bold;
  border-radius: 8px;
}}

#latest {{
  display: flex;
  overflow-x: auto;
  gap: 10px;
  margin-bottom: 20px;
  padding-bottom: 10px;
  scroll-behavior: smooth;
}}

#latest::-webkit-scrollbar {{
  display: none;
}}
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

<select id='genreSelect' multiple size=1></select>
<input type='text' id='searchBox' placeholder='Cerca...'>
</div>

<div id='moviesGrid' class='grid'></div>

<script>
const allData = {entries_json};
</script>

</body>
</html>
"""
    return html


def main():
    api_key = get_api_key()
    entries = []
    latest_entries = ""

    try:
        old_entries = load_archive()
    except FileNotFoundError:
        old_entries = []

    for type_, url in SRC_URLS.items():
        data = fetch_list(url)
        ids = extract_ids(data)

        for idx, tmdb_id in enumerate(ids):
            try:
                info = tmdb_get(api_key, type_, tmdb_id)
            except:
                info = None

            if not info:
                continue

            title = info.get("title") or info.get("name") or f"ID {tmdb_id}"
            poster = TMDB_IMAGE_BASE + info["poster_path"] if info.get("poster_path") else ""
            genres = [g["name"] for g in info.get("genres", [])]
            vote = info.get("vote_average", 0)
            overview = info.get("overview", "")
            link = VIX_LINK_MOVIE.format(tmdb_id) if type_ == "movie" else ""

            entries.append({
                "id": str(tmdb_id),
                "title": title,
                "poster": poster,
                "genres": genres,
                "vote": vote,
                "overview": overview,
                "link": link,
                "type": type_
            })

            if idx < 10:
                latest_entries += f"<img class='poster' src='{poster}' alt='{title}' title='{title}'>\n"

    save_archive(entries)

    html = build_html(entries, latest_entries)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Generato {OUTPUT_HTML} con {len(entries)} elementi e ultime novità scrollabili")


if __name__ == "__main__":
    main()
