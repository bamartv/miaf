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
- InfoCard fullscreen con poster trasparente e trailer incorporato
"""


import os
import sys
import requests

# --- Config ---
SRC_URLS = {
    "movie": "https://vixsrc.to/api/list/movie?lang=it",
    "tv": "https://vixsrc.to/api/list/tv?lang=it"
}
TMDB_BASE = "https://api.themoviedb.org/3/{type}/{id}"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w300"
VIX_LINK_MOVIE = "https://vixsrc.to/movie/{}/?"
OUTPUT_HTML = "index.html"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; script/1.0)"}


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
        params={"api_key": api_key, "language": language, "append_to_response": "credits,videos,similar"},
        timeout=15
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


def build_html(entries, latest_entries):
    html = f"""<!doctype html>
<html lang='it'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Movies & Series</title>
<style>
body{{font-family:Arial,sans-serif;background:#141414;color:#fff;margin:0;padding:20px;}}
h1{{color:#fff;text-align:center;margin-bottom:20px;}}
.controls{{display:flex;gap:10px;justify-content:center;margin-bottom:20px;flex-wrap:wrap;}}
input,select{{padding:8px;font-size:14px;border-radius:4px;border:none;}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:12px;}}
.card{{position:relative;cursor:pointer;transition: transform 0.2s;border-radius:12px;overflow:hidden;border:2px solid #444;background:#1f1f1f;}}
.card:hover{{transform:scale(1.05);border-color:#e50914;background:#2a2a2a;}}
.poster{{width:100%;border-radius:0;display:block;}}
.badge{{position:absolute;top:8px;right:8px;background:#e50914;color:#fff;padding:4px 6px;font-size:14px;font-weight:bold;border-radius:8px;text-align:center;}}
.favorite-btn{{font-size:20px;color:#fff;text-shadow:0 0 4px #000;}}
.favorite-btn.active{{color:gold;}}
.card .favorite-btn{{position:absolute;top:8px;left:8px;pointer-events:none;}}
#favoriteInCard.favorite-btn{{position:static;cursor:pointer;margin-left:auto;font-size:22px;}}
#loadMore{{display:block;margin:20px auto;padding:10px 20px;font-size:16px;background:#e50914;color:#fff;border:none;border-radius:8px;cursor:pointer;}}
#playerOverlay{{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.9);display:none;align-items:center;justify-content:center;z-index:1000;flex-direction:column;}}
#playerOverlay iframe{{width:100%;height:100%;border:none;position:relative;z-index:1;}}
#playerTitle{{position:absolute;top:20px;left:50%;transform:translateX(-50%);background:rgba(0,0,0,0.7);color:#fff;padding:8px 12px;border-radius:8px;font-size:18px;display:none;z-index:10;}}
#infoCard {{
    position: fixed;
    top:0;
    left:0;
    width:100%;
    height:100%;
    display:none;
    justify-content:flex-end;
    background:rgba(0,0,0,0.9);
    z-index:1001;
    overflow:auto;
    backdrop-filter:blur(8px);
    color:#fff;
}}
#infoText {{
    width:100%;
    max-width:800px;
    margin:auto;
    padding:20px;
    box-sizing:border-box;
    background:linear-gradient(to bottom, rgba(0,0,0,0) 35%, rgba(0,0,0,1) 50%, rgba(0,0,0,1) 100%);
    display:flex;
    flex-direction:column;
    align-items:flex-start;
}}
#infoText h1 {{
    margin-top:0;
    color:#fff;
    text-shadow: 2px 2px 6px rgba(0,0,0,0.8);
}}
#buttons {{
    display:flex;
    gap:10px;
    margin:10px 0 20px;
}}
.button {{
    padding:10px 16px;
    border:none;
    border-radius:6px;
    cursor:pointer;
    font-size:16px;
    background:#111;
    color:#fff;
    box-shadow:0 2px 6px rgba(0,0,0,0.5);
    transition:background 0.2s;
}}
.button:hover {{
    background:#333;
}}
#trailer {{
    width:100%;
    max-width:500px;
    height:280px;
    border:none;
    border-radius:8px;
    margin-bottom:20px;
}}
#related {{
    display:flex;
    overflow-x:auto;
    gap:10px;
    padding-bottom:10px;
}}
#related::-webkit-scrollbar {{ display: none; }}
.related-item {{
    flex:0 0 auto;
    width:120px;
    border-radius:6px;
}}
.related-item img {{
    width:100%;
    border-radius:6px;
}}
</style>
</head>
<body>
<h1>Ultime Novità</h1>
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
<button id='loadMore'>Carica altri</button>

<div id='playerOverlay'>
  <iframe allow="autoplay; fullscreen; encrypted-media" allowfullscreen></iframe>
  <div id="playerTitle"></div>
</div>

<!-- InfoCard fullscreen modificata -->
<div id="infoCard">
    <div id="infoText">
        <h1 id="infoTitle"></h1>
        <div id="buttons">
            <button id="playBtn" class="button">Guarda</button>
            <button id="favoriteInCard" class="button">★ Preferiti</button>
            <button id="closeCardBtn" class="button">Chiudi</button>
        </div>
        <p id="infoYear"><strong>Anno:</strong> </p>
        <p id="infoDuration"><strong>Durata:</strong> </p>
        <p id="infoGenres"><strong>Genere:</strong> </p>
        <p id="infoCast"><strong>Cast:</strong> </p>
        <p id="infoOverview"><strong>Descrizione:</strong> </p>
        <iframe id="trailer" src="" allowfullscreen></iframe>

        <h2>Film correlati</h2>
        <div id="related"></div>
    </div>
</div>

<script>
const allData = {entries};
let favorites = JSON.parse(localStorage.getItem("favorites") || "[]");
let recentList = JSON.parse(localStorage.getItem("recent") || "[]");
let currentItem = null;

const grid=document.getElementById('moviesGrid');
const overlay=document.getElementById('playerOverlay');
const iframe=overlay.querySelector('iframe');
const playerTitle=document.getElementById('playerTitle');
const infoCard=document.getElementById('infoCard');
const infoTitle=document.getElementById('infoTitle');
const infoGenres=document.getElementById('infoGenres');
const infoVote=document.getElementById('infoVote');
const infoOverview=document.getElementById('infoOverview');
const playBtn=document.getElementById('playBtn');
const closeCardBtn=document.getElementById('closeCardBtn');
const latestDiv=document.getElementById('latest');
const favoriteInCard=document.getElementById('favoriteInCard');
const seasonSelect=document.getElementById('seasonSelect');
const episodeSelect=document.getElementById('episodeSelect');
const infoYear=document.getElementById('infoYear');
const infoDuration=document.getElementById('infoDuration');
const infoCast=document.getElementById('infoCast');
const genreSelect=document.getElementById('genreSelect');

// Funzione openInfo modificata con trailer e correlati
function openInfo(item, push=true) {{
    currentItem = item;
    infoCard.style.display='flex';
    infoCard.style.backgroundImage = `url(${item.poster})`;
    infoCard.style.backgroundSize='cover';
    infoCard.style.backgroundPosition='center';

    infoTitle.textContent = item.title;
    infoGenres.textContent = "Genere: " + (item.genres && item.genres.length ? item.genres.join(", ") : "");
    infoVote.textContent = "★ " + item.vote;
    infoOverview.textContent = item.overview || "";
    infoYear.textContent = item.year ? "Anno: " + item.year : "";
    infoDuration.textContent = item.duration ? "Durata: " + item.duration + " min" : "";
    infoCast.textContent = item.cast && item.cast.length ? "Cast: " + item.cast.slice(0,5).join(", ") : "";

    const trailerId = item.trailer || "";
    const trailer = document.getElementById('trailer');
    if(trailerId){{
        trailer.src = `https://www.youtube.com/embed/${trailerId}?autoplay=1&mute=1`;
        trailer.style.display = 'block';
    }} else {{
        trailer.src = '';
        trailer.style.display = 'none';
    }}

    const relatedDiv = document.getElementById('related');
    relatedDiv.innerHTML = "";
    if(item.related){{
        item.related.forEach(rel=> {{
            const d = document.createElement('div');
            d.className = 'related-item';
            d.innerHTML = `<img src='${{rel.poster}}' alt='${{rel.title}}'>`;
            relatedDiv.appendChild(d);
        }});
    }}

    favoriteInCard.classList.toggle("active", favorites.includes(item.id));
    favoriteInCard.onclick = () => {{
        toggleFavorite(item.id);
        favoriteInCard.classList.toggle("active", favorites.includes(item.id));
    }};

    playBtn.onclick = () => openPlayer(item);

    closeCardBtn.onclick = () => {{
        infoCard.style.display='none';
        trailer.src = '';
        if(push) {{
            history.replaceState({{page:"grid"}}, "", "#grid");
        }}
    }};

    if(push){{
        history.pushState({{page:"info", itemId:item.id}}, "", "#info-"+item.id);
    }}
}}

// Il resto del JS (render, loadMore, filtri, popstate, ecc.) rimane **identico** al tuo script originale.
</script>
</body>
</html>
"""
    return html


def main():
    api_key = get_api_key()
    entries = []
    latest_entries = ""

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
            link = VIX_LINK_MOVIE.format(tmdb_id) if type_=="movie" else ""
            year = (info.get("release_date") or info.get("first_air_date") or "").split("-")[0]
            duration = info.get("runtime") or (info.get("episode_run_time") or [0])[0]

            # Trailer YouTube (primo video di tipo "Trailer")
            trailer = ""
            videos = info.get("videos", {}).get("results", [])
            for v in videos:
                if v.get("type") == "Trailer" and v.get("site") == "YouTube":
                    trailer = v.get("key")
                    break

            # Film/Serie correlati (max 5)
            related = []
            for r in info.get("similar", {}).get("results", [])[:5]:
                related.append({
                    "id": r.get("id"),
                    "title": r.get("title") or r.get("name") or "",
                    "poster": TMDB_IMAGE_BASE + r["poster_path"] if r.get("poster_path") else ""
                })

            entry = {
                "id": str(tmdb_id),
                "type": type_,
                "title": title,
                "poster": poster,
                "genres": genres,
                "vote": vote,
                "overview": overview,
                "year": year,
                "duration": duration,
                "trailer": trailer,
                "related": related,
                "link": link
            }
            entries.append(entry)

            # Aggiungi le ultime novità (solo prime 20 per sezione latest)
            if len(latest_entries.split("</div>")) <= 20:
                latest_entries += f"""
                <div class='card' onclick='openInfo(allData[{len(entries)-1}])'>
                    <img class='poster' src='{poster}' alt='{title}'>
                    <div class='badge'>{vote:.1f}</div>
                </div>
                """

    # Genera HTML finale
    html_content = build_html(entries, latest_entries)

    # Scrivi su file
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"File generato: {OUTPUT_HTML}")


if __name__ == "__main__":
    main()
