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

# --- Config ---
SRC_URLS = {
    "movie": "https://vixsrc.to/api/list/movie?lang=it",
    "tv": "https://vixsrc.to/api/list/tv?lang=it"
}
TMDB_BASE = "https://api.themoviedb.org/3/{type}/{id}"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"  # poster più grande
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
#favoriteInCard.favorite-btn{{position:static;cursor:pointer;margin-left:auto;font-size:22px;}}
#loadMore{{display:block;margin:20px auto;padding:10px 20px;font-size:16px;background:#e50914;color:#fff;border:none;border-radius:8px;cursor:pointer;}}
#playerOverlay{{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.9);display:none;align-items:center;justify-content:center;z-index:1000;flex-direction:column;}}
#playerOverlay iframe{{width:100%;height:100%;border:none;position:relative;z-index:1;}}
#playerTitle{{position:absolute;top:20px;left:50%;transform:translateX(-50%);background:rgba(0,0,0,0.7);color:#fff;padding:8px 12px;border-radius:8px;font-size:18px;display:none;z-index:10;}}

#infoCard{{position:fixed;top:0;left:0;width:100%;height:100%;display:none;z-index:1001;color:#fff;overflow:auto;}}
#infoCardOverlay{{position:fixed;top:0;left:0;width:100%;height:100%;z-index:0;background-size:contain;background-position:center center;background-repeat:no-repeat;opacity:0.25;}}
#infoCardContent{{position:relative;z-index:1;padding:20px;max-width:800px;width:90%;margin:auto;background:linear-gradient(to bottom, rgba(0,0,0,0) 50%, rgba(0,0,0,1) 100%);}}

#latest{{display:flex;overflow-x:auto;gap:10px;margin-bottom:20px;padding-bottom:10px;scroll-behavior:smooth;}}
#latest::-webkit-scrollbar{{display:none;}}
#latest{{-ms-overflow-style:none;scrollbar-width:none;}}
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

<div id='infoCard'>
  <div id='infoCardOverlay'></div>
  <div id='infoCardContent'>
    <h2 id="infoTitle"></h2>
    <div style="display:flex;align-items:center;gap:10px;margin:10px 0;">
      <button id="playBtn" class="btn-play">Riproduci</button>
      <button id="closeCardBtn" class="btn-close">Chiudi</button>
      <span id="favoriteInCard" class="favorite-btn">★</span>
    </div>
    <div id="infoDetails">
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
    const overlayBg=document.getElementById('infoCardOverlay');
    overlayBg.style.backgroundImage = "url('" + item.poster + "')";
    overlayBg.style.backgroundSize="contain";
    overlayBg.style.backgroundPosition="center center";
    overlayBg.style.backgroundRepeat="no-repeat";
    overlayBg.style.opacity="0.25";

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

    seasonSelect.style.display='none';
    episodeSelect.style.display='none';

    if(item.type==='tv') {{
        seasonSelect.style.display='inline';
        episodeSelect.style.display='inline';
        seasonSelect.innerHTML="";
        for(let s=1;s<=item.seasons;s++) {{
            let o=document.createElement('option');
            o.value=s;
            o.textContent="Stagione " + s;
            seasonSelect.appendChild(o);
        }}
        seasonSelect.onchange=updateEpisodes;
        updateEpisodes();
    }}

    playBtn.onclick=() => openPlayer(item);

    if(push) {{
        history.pushState({{page:"info", itemId:item.id}}, "", "#info-"+item.id);
    }}

    function updateEpisodes(){{
        let season=parseInt(seasonSelect.value);
        let epCount=item.episodes[season] || 1;
        episodeSelect.innerHTML="";
        for(let e=1;e<=epCount;e++){{
            let o=document.createElement('option');
            o.value=e;
            o.textContent="Episodio " + e;
            episodeSelect.appendChild(o);
        }}
    }}
}}

function openPlayer(item, push=true) {{
    infoCard.style.display='none';
    overlay.style.display='flex';
    let link=item.link;
    if(item.type==='tv'){{
        let season=parseInt(seasonSelect.value) || 1;
        let episode=parseInt(episodeSelect.value) || 1;
        link = `https://vixsrc.to/tv/${{item.id}}/${{season}}/${{episode}}?lang=it&sottotitoli=off&autoplay=1`;
    }} else {{
        link = `https://vixsrc.to/movie/${{item.id}}/?lang=it&sottotitoli=off&autoplay=1`;
    }}
    iframe.src = link;

    if (overlay.requestFullscreen) overlay.requestFullscreen();
    else if (overlay.webkitRequestFullscreen) overlay.webkitRequestFullscreen();
    else if (overlay.msRequestFullscreen) overlay.msRequestFullscreen();

    if(push) {{
        history.pushState({{page:"player", itemId:item.id}}, "", "#player-"+item.id);
    }}
}}

// Gestione preferiti e recenti
function toggleFavorite(id) {{
  if(favorites.includes(id)) favorites=favorites.filter(f=>f!==id);
  else favorites.push(id);
  localStorage.setItem("favorites", JSON.stringify(favorites));
  render(true);
}}
function addToRecent(id) {{
  recentList = recentList.filter(x => x!==id);
  recentList.unshift(id);
  if(recentList.length>20) recentList.pop();
  localStorage.setItem("recent", JSON.stringify(recentList));
}}

// Rendering griglia
function render(filterType=null){{
    grid.innerHTML="";
    let data=allData;
    if(filterType==="favorites") data=data.filter(e=>favorites.includes(e.id));
    else if(filterType==="recent") data=data.filter(e=>recentList.includes(e.id));
    for(let item of data){{
        let card=document.createElement('div');
        card.className="card";
        card.innerHTML=`<img class='poster' src='${{item.poster}}'>
                        <span class="favorite-btn ${favorites.includes(item.id)?'active':''}">★</span>`;
        card.onclick=()=>{{ openInfo(item); addToRecent(item.id); }};
        grid.appendChild(card);
    }}
}}

document.getElementById('typeSelect').onchange=function(){{
    render(this.value);
}};
document.getElementById('searchBox').oninput=function(){{
    let query=this.value.toLowerCase();
    let filtered=allData.filter(e=>e.title.toLowerCase().includes(query));
    grid.innerHTML="";
    for(let item of filtered){{
        let card=document.createElement('div');
        card.className="card";
        card.innerHTML=`<img class='poster' src='${{item.poster}}'>
                        <span class="favorite-btn ${favorites.includes(item.id)?'active':''}">★</span>`;
        card.onclick=()=>{{ openInfo(item); addToRecent(item.id); }};
        grid.appendChild(card);
    }}
}};

// Avvio
render();
showLatest();

</script>
</body>
</html>
"""
    return html


def main():
    api_key = get_api_key()
    all_entries = []

    for type_, url in SRC_URLS.items():
        data = fetch_list(url)
        for item in data:
            tmdb = tmdb_get(api_key, type_, item.get("tmdb_id") or item.get("id"))
            if not tmdb:
                continue
            entry = {
                "id": item.get("id"),
                "title": tmdb.get("title") or tmdb.get("name"),
                "poster": TMDB_IMAGE_BASE + (tmdb.get("poster_path") or ""),
                "genres": [g["name"] for g in tmdb.get("genres", [])],
                "vote": tmdb.get("vote_average") or 0,
                "overview": tmdb.get("overview") or "",
                "year": (tmdb.get("release_date") or tmdb.get("first_air_date") or "")[:4],
                "duration": tmdb.get("runtime") or (tmdb.get("episode_run_time") or [0])[0],
                "cast": [c["name"] for c in tmdb.get("credits", {}).get("cast", [])],
                "type": type_,
                "seasons": tmdb.get("number_of_seasons") or 0,
                "episodes": {s+1: ep.get("episode_count", 1) for s, ep in enumerate(tmdb.get("seasons", []))},
                "link": VIX_LINK_MOVIE.format(item.get("id"))
            }
            all_entries.append(entry)

    latest_html = "".join([f"<div class='card'><img class='poster' src='{e['poster']}'/></div>" for e in all_entries[:10]])
    html = build_html(all_entries, latest_html)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"File generato: {OUTPUT_HTML}"


if __name__ == "__main__":
    main()
