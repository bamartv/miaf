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
        params={"api_key": api_key, "language": language, "append_to_response": "credits"},
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
#favoriteInCard.favorite-btn{{position:static;cursor:pointer;font-size:15px;}}
#loadMore{{display:block;margin:20px auto;padding:10px 20px;font-size:16px;background:#e50914;color:#fff;border:none;border-radius:8px;cursor:pointer;}}
#playerOverlay{{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.9);display:none;align-items:center;justify-content:center;z-index:1000;flex-direction:column;}}
#playerOverlay iframe{{width:100%;height:100%;border:none;position:relative;z-index:1;}}
#playerTitle{{position:absolute;top:20px;left:50%;transform:translateX(-50%);background:rgba(0,0,0,0.7);color:#fff;padding:8px 12px;border-radius:8px;font-size:18px;display:none;z-index:10;}}
#infoCard {{
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    display: none;
    z-index: 1001;
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
}}

    /* CENTRAGGIO perfetto */
    display: flex;
    align-items: center;
    justify-content: center;
}}
#infoCard > div {{
    position: relative;
    background: transparent;
    border-radius: 10px;
    padding: 20px;
    max-width: 800px;
    width: 90%;
    text-align: center;
}}
#infoCard h2 {{
    font-size: 3em;
    font-weight: 800;
    color: #fff;
    margin-bottom: 20px;
}}

#infoCard button#playBtn,
#infoCard button#closeCardBtn,
#infoCard button#favoriteInCard {{
    width: 120px;       /* stessa larghezza */
    height: 38px;       /* stessa altezza */
    padding: 8px 0;     /* verticale interna */
    background: #141414;
    border: none;
    color: #fff;
    border-radius: 5px;
    cursor: pointer;
    vertical-align: middle;
    text-align: center;
}}
#infoCard button#favoriteInCard.active {{
    background: gold;   /* sfondo dorato */
    color: #141414;     /* testo scuro per contrasto */
}}
#infoCard p{{margin:5px 0;}}
#infoCard select{{margin:5px 5px 5px 0;padding:6px;}}
#latest{{display:flex;overflow-x:auto;gap:10px;margin-bottom:20px;padding-bottom:10px;scroll-behavior: smooth;}}
#latest::-webkit-scrollbar {{display: none;}}
#latest {{-ms-overflow-style: none;scrollbar-width: none;}}
#latest .poster{{width:100px;flex-shrink:0;}}
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

<div id='infoCard' style="position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(20,20,20,0.85); display:none; z-index:1001; backdrop-filter:blur(8px); align-items:center; justify-content:center;">
  <div style="position:relative; background:transparent; border-radius:10px; padding:20px; max-width:800px; width:90%; text-align:center;">
    <h2 id="infoTitle" style="font-family:'Roboto','Helvetica Neue',Helvetica,Arial,sans-serif; font-weight:bold; font-size:2em; letter-spacing:-0.5px; color:#ffffff; margin-top:0;"></h2>
    
    <div style="display:flex; justify-content:center; align-items:center; gap:10px; margin:10px 0; flex-wrap:wrap;">
      <button id="playBtn" class="btn-play">Riproduci</button>
      <button id="closeCardBtn" class="btn-close">Chiudi</button>
      <button id="favoriteInCard" class="favorite-btn">Preferiti</button>
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

closeCardBtn.onclick = () => {{
  infoCard.style.display='none';
  history.replaceState({{page:"grid"}}, "", "#grid");
}};

function showLatest(){{
    let scrollPos = 0;
    function scroll() {{
        scrollPos += 1;
        if(scrollPos > latestDiv.scrollWidth - latestDiv.clientWidth) scrollPos = 0;
        latestDiv.scrollTo({{ left: scrollPos, behavior: 'smooth' }});
    }}
    setInterval(scroll, 30);
}}

function openInfo(item, push=true) {{
    currentItem = item;
    infoCard.style.display='block';
    infoCard.style.backgroundImage = `linear-gradient(to right, rgba(20,20,20,0.85) 30%, rgba(20,20,20,0.4) 70%), url('${{item.poster}}')`;
    infoCard.style.backgroundColor = "rgba(20,20,20,0.85)";
    infoTitle.textContent = item.title;
    infoGenres.textContent = "Generi: " + (item.genres && item.genres.length ? item.genres.join(", ") : "");
    infoVote.textContent = "★ " + item.vote;
    infoOverview.textContent = item.overview || "";
    infoYear.textContent = item.year ? "Anno: " + item.year : "";
    infoDuration.textContent = item.duration ? "Durata: " + item.duration + " min" : "";
    infoCast.textContent = item.cast && item.cast.length ? "Cast: " + item.cast.slice(0,5).join(", ") : "";

    favoriteInCard.classList.toggle("active", favorites.includes(item.id));
    favoriteInCard.onclick = () => {{
        toggleFavorite(item.id);
        favoriteInCard.classList.toggle("active", favorites.includes(item.id));
    }};

    seasonSelect.style.display = 'none';
    episodeSelect.style.display = 'none';

    if(item.type==='tv') {{
        seasonSelect.style.display = 'inline';
        episodeSelect.style.display = 'inline';
        seasonSelect.innerHTML = "";
        for(let s=1;s<=item.seasons;s++) {{
            let o = document.createElement('option');
            o.value = s;
            o.textContent = "Stagione " + s;
            seasonSelect.appendChild(o);
        }}
        seasonSelect.onchange = updateEpisodes;
        updateEpisodes();
    }}

    playBtn.onclick = () => openPlayer(item);

    if(push) {{
        history.pushState({{page:"info", itemId:item.id}}, "", "#info-"+item.id);
    }}

    function updateEpisodes() {{
        let season = parseInt(seasonSelect.value);
        let epCount = item.episodes[season] || 1;
        episodeSelect.innerHTML = "";
        for(let e=1;e<=epCount;e++) {{
            let o = document.createElement('option');
            o.value = e;
            o.textContent = "Episodio " + e;
            episodeSelect.appendChild(o);
        }}
    }}
}}

function openPlayer(item, push=true) {{
    infoCard.style.display = 'none';
    overlay.style.display='flex';
    let link = item.link;
    if(item.type==='tv') {{
        let season = parseInt(seasonSelect.value) || 1;
        let episode = parseInt(episodeSelect.value) || 1;
        link = `https://vixsrc.to/tv/${{item.id}}/${{season}}/${{episode}}?lang=it&sottotitoli=off&autoplay=1`;
    }} else {{
        link = `https://vixsrc.to/movie/${{item.id}}/?lang=it&sottotitoli=off&autoplay=1`;
    }}
    iframe.src = link;
    addToRecent(item.id);

    if (overlay.requestFullscreen) overlay.requestFullscreen();
    else if (overlay.webkitRequestFullscreen) overlay.webkitRequestFullscreen();
    else if (overlay.msRequestFullscreen) overlay.msRequestFullscreen();

    if(push) {{
        history.pushState({{page:"player", itemId:item.id}}, "", "#player-"+item.id);
    }}
}}

function closePlayer(push=true) {{
    overlay.style.display='none';
    iframe.src='';
    if (document.fullscreenElement) document.exitFullscreen();
    else if (document.webkitFullscreenElement) document.webkitExitFullscreen();
    else if (document.msFullscreenElement) document.msExitFullscreen();

    if(currentItem) {{
        infoCard.style.display = 'block';
        if(push) {{
            history.pushState({{page:"info", itemId:currentItem.id}}, "", "#info-"+currentItem.id);
        }}
    }}
}}

function toggleFavorite(id) {{
  if(favorites.includes(id)) {{
    favorites = favorites.filter(f=>f!==id);
  }} else {{
    favorites.push(id);
  }}
  localStorage.setItem("favorites", JSON.stringify(favorites));
  render(true);
}}

function addToRecent(id) {{
  recentList = recentList.filter(x => x !== id);
  recentList.unshift(id);
  if(recentList.length > 20) recentList.pop();
  localStorage.setItem("recent", JSON.stringify(recentList));
}}

window.addEventListener("popstate", function(e) {{
    const state = e.state;

    if(state && state.page === "info" && overlay.style.display !== 'flex' && infoCard.style.display === 'none') {{
        history.back();
        return;
    }}

    if(!state || state.page==="grid" || state.page==="home") {{
        overlay.style.display='none';
        iframe.src='';
        infoCard.style.display='none';
        return;
    }}

    const itemId = state.itemId;
    const item = allData.find(x => String(x.id) === String(itemId));
    if(!item) {{
        overlay.style.display='none';
        iframe.src='';
        infoCard.style.display='none';
        return;
    }}

    if(state.page === "player") {{
        openPlayer(item, false);
    }} else if(state.page === "info") {{
        if(overlay.style.display==='flex') {{
            closePlayer(false);
        }}
        openInfo(item, false);
    }} else {{
        overlay.style.display='none';
        iframe.src='';
        infoCard.style.display='none';
    }}
}});

let currentType='movie', currentList=[], shown=0;

function render(reset=false) {{
    if(reset){{ grid.innerHTML=''; shown=0; }}
    let count=0;
    let s = document.getElementById('searchBox').value.toLowerCase();
    let gSel = Array.from(document.getElementById('genreSelect').selectedOptions).map(o=>o.value);
    while(shown<currentList.length && count<40) {{
        let m = currentList[shown++];
        let isFav = favorites.includes(m.id);
        let genreMatch = gSel.length===0 || gSel.includes('all') || gSel.every(g => m.genres.includes(g));
        if(genreMatch && m.title.toLowerCase().includes(s)) {{
            const card = document.createElement('div');
            card.className='card';
            card.innerHTML = `
                <img class='poster' src='${{m.poster}}' alt='${{m.title}}'>
                <div class='badge'>${{m.vote}}</div>
                <p style="margin:2px 0;font-size:12px;color:#ccc;">
                    ${{m.duration ? m.duration + ' min • ' : ''}}${{m.year ? m.year : ''}}
                </p>
                <span class="favorite-btn ${{isFav ? 'active' : ''}}" style="pointer-events:none;">★</span>
            `;
            card.onclick = () => openInfo(m);
            grid.appendChild(card);
            count++;
        }}
    }}
}}

function populateGenres(){{
    const set=new Set();
    currentList.forEach(m=>m.genres.forEach(g=>set.add(g)));
    const sel=document.getElementById('genreSelect');
    sel.innerHTML='<option value="all">Tutti i generi</option>';
    [...set].sort().forEach(g=>{{
        const o=document.createElement('option');
        o.value=o.textContent=g;
        sel.appendChild(o);
    }});
}}

function updateType(t){{
    currentType=t;
    if(t==="movie" || t==="tv"){{
        currentList=allData.filter(x=>x.type===t);
        genreSelect.style.display='inline';
        populateGenres();
    }} else if(t==="favorites"){{
        currentList=allData.filter(x=>favorites.includes(x.id));
        genreSelect.style.display='none';
    }} else if(t==="recent"){{
        currentList=allData.filter(x=>recentList.includes(x.id));
        genreSelect.style.display='none';
    }}
    render(true);
}}

/* Eventi UI */
document.getElementById('typeSelect').onchange=e=>updateType(e.target.value);
document.getElementById('genreSelect').onchange=()=>render(true);
document.getElementById('searchBox').oninput=()=>render(true);
document.getElementById('loadMore').onclick=()=>render(false);

/* stato iniziale nella history */
history.replaceState({{page:"grid"}}, "", "#grid");

updateType('movie');
showLatest();
</script>
</body>
</html>
"""
    return html


def main():
    api_key = get_api_key()
    entries = []
    latest_entries = ""

    # Carica vecchi titoli dall'archivio, se esiste
    try:
        old_entries = load_archive()
    except FileNotFoundError:
        old_entries = []

    # Ciclo sulle sorgenti VIX
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
            seasons = info.get("number_of_seasons", 1) if type_ == "tv" else 0
            episodes = {str(s["season_number"]): s.get("episode_count", 1) 
                        for s in info.get("seasons", []) if s.get("season_number")} if type_ == "tv" else {}

            year = (info.get("release_date") or info.get("first_air_date") or "")[:4]

            runtime_list = info.get("episode_run_time") or []
            duration = info.get("runtime") or (runtime_list[0] if runtime_list else None)

            cast = [c["name"] for c in info.get("credits", {}).get("cast", [])] if info.get("credits") else []

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
                "cast": cast
            })

            # Solo prime 10 per latest
            if idx < 10:
                latest_entries += f"<img class='poster' src='{poster}' alt='{title}' title='{title}'>\n"

    # --- Unione con l'archivio esistente ---
    combined = {e["id"]: e for e in old_entries}
    for e in entries:
        combined[e["id"]] = e  # aggiorna o aggiunge nuovo
    all_entries = list(combined.values())

    # Debug e salvataggio
    print(f"Totale entries da salvare: {len(all_entries)}")
    save_archive(all_entries)
    print(f"Archivio salvato su {ARCHIVE_FILE}")

    # Genera HTML finale
    html = build_html(all_entries, latest_entries)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Generato {OUTPUT_HTML} con {len(all_entries)} elementi e ultime novità scrollabili")


if __name__ == "__main__":
    main()
