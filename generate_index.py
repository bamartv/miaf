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
- InfoCard a tutta pagina con poster sfondo + trailer dinamico
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
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"
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
        params={"api_key": api_key, "language": language, "append_to_response": "credits,videos"},
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
#infoCard{{position:fixed;top:0;left:0;width:100%;height:100%;background:#000;display:none;z-index:1001;color:#fff;overflow:auto;}}
#infoContent{{position:relative;width:100%;height:100%;background-size:cover;background-position:center;display:flex;flex-direction:column;justify-content:flex-end;padding:20px;box-sizing:border-box;}}
#infoText{{background:linear-gradient(to bottom, rgba(0,0,0,0) 35%, rgba(0,0,0,0.9) 100%);padding:20px;}}
#infoText h1{{margin-top:0;color:#fff;text-shadow:2px 2px 6px rgba(0,0,0,0.8);}}
#infoText p{{margin:5px 0;}}
#buttons{{display:flex;gap:10px;margin:10px 0;}}
.button{{padding:10px 16px;border:none;border-radius:6px;cursor:pointer;font-size:16px;background:#111;color:#fff;box-shadow:0 2px 6px rgba(0,0,0,0.5);transition:background 0.2s;}}
.button:hover{{background:#333;}}
#trailer{{width:100%;max-width:500px;height:280px;border:none;border-radius:8px;margin-bottom:20px;}}
#related{{display:flex;overflow-x:auto;gap:10px;padding-bottom:10px;}}
#related::-webkit-scrollbar {{ display: none; }}
.related-item{{flex:0 0 auto;width:120px;border-radius:6px;}}
.related-item img{{width:100%;border-radius:6px;}}
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

<div id='infoCard'>
    <div id='infoContent'>
        <div id='infoText'>
            <h1 id='infoTitle'></h1>
            <div id='buttons'>
                <button id='playBtn' class='button'>Guarda</button>
                <button id='favoriteInCard' class='button'>★ Preferiti</button>
                <button id='closeCardBtn' class='button'>Chiudi</button>
            </div>
            <p id='infoYear'></p>
            <p id='infoDuration'></p>
            <p id='infoGenres'></p>
            <p id='infoCast'></p>
            <p id='infoOverview'></p>
            <iframe id='trailer' src='' allowfullscreen></iframe>
            <h2>Film correlati</h2>
            <div id='related'></div>
            <select id='seasonSelect'></select>
            <select id='episodeSelect'></select>
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
const infoContent=document.getElementById('infoContent');
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
    infoContent.style.backgroundImage = `url(${{item.poster}})`;
    infoTitle.textContent = item.title;
    infoGenres.textContent = "Generi: " + (item.genres && item.genres.length ? item.genres.join(", ") : "");
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

    // Trailer
    const trailerData = (item.videos || []).find(v => v.type==='Trailer' && v.site==='YouTube');
    const trailerIframe = document.getElementById('trailer');
    trailerIframe.src = trailerData ? `https://www.youtube.com/embed/${{trailerData.key}}?autoplay=1&mute=0` : '';

    playBtn.onclick = () => {{
        if(trailerIframe.src) trailerIframe.scrollIntoView({{behavior:'smooth'}});
    }};

    if(push) {{
        history.pushState({{page:"info", itemId:item.id}}, "", "#info-"+item.id);
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
                <span class="favorite-btn ${{isFav ? 'active' :''}}">★</span>
            `;
            card.onclick = () => {{
                addToRecent(m.id);
                openInfo(m);
            }};
            grid.appendChild(card);
            count++;
        }}
    }}
}}

document.getElementById('searchBox').oninput = () => render(true);
document.getElementById('typeSelect').onchange = (e) => {{
    const val = e.target.value;
    currentType = val;
    if(val==='favorites') {{
        currentList = allData.filter(d=>favorites.includes(d.id));
    }} else if(val==='recent') {{
        currentList = recentList.map(id => allData.find(d=>d.id===id)).filter(Boolean);
    }} else {{
        currentList = allData.filter(d=>d.type===val);
    }}
    render(true);
}};

document.getElementById('loadMore').onclick = () => render(false);

window.onpopstate = (event) => {{
    if(event.state?.page==="info") {{
        const item = allData.find(d=>d.id===event.state.itemId);
        if(item) openInfo(item,false);
    }} else {{
        infoCard.style.display='none';
    }}
}};

showLatest();
render(true);

</script>
</body>
</html>"""
    return html

def main():
    api_key = get_api_key()
    entries=[]
    latest_entries=""
    for type_ in ["movie","tv"]:
        data = fetch_list(SRC_URLS[type_])
        ids = extract_ids(data)
        for tmdb_id in ids[:50]:  # limitiamo per esempio a 50
            info = tmdb_get(api_key, type_, tmdb_id)
            if not info: continue
            item = {{
                "id": f"{type_}_{tmdb_id}",
                "type": type_,
                "title": info.get("title") or info.get("name") or "",
                "year": (info.get("release_date") or info.get("first_air_date") or "")[:4],
                "duration": info.get("runtime") or (info.get("episode_run_time") and info.get("episode_run_time")[0]) or "",
                "genres": [g["name"] for g in info.get("genres",[])],
                "overview": info.get("overview",""),
                "poster": TMDB_IMAGE_BASE + info["poster_path"] if info.get("poster_path") else "",
                "vote": info.get("vote_average") or "",
                "cast": [c["name"] for c in info.get("credits",{{}}).get("cast",[])],
                "videos": info.get("videos",{{}}).get("results",[]),
                "seasons": info.get("number_of_seasons",1),
                "episodes": {{s+1: e.get("episode_count",1) for s,e in enumerate(info.get("seasons",[]))}}
            }}
            entries.append(item)
            latest_entries += f"<img class='poster' src='{item['poster']}' title='{item['title']}'>"

    html_content = build_html(entries, latest_entries)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"HTML generato in {OUTPUT_HTML}")

if __name__=="__main__":
    main()
