#!/usr/bin/env python3
"""
generate_index.py

Generatore di pagina HTML per Movies & Series con:
- Preferiti e Visti di recente nella tendina principale
- Gestione recenti tramite localStorage (max 20)
- Stellina sulle locandine: solo visuale
- Stellina cliccabile nella scheda info
- Selezione multipla dei generi
- Correzione back button: chiude il player prima di tornare alla griglia
- Titolo nel player comparibile al tocco dello schermo
- Compatibile TV/Firestick (tasti selezionabili)
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
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w780"
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
    # costruzione delle card griglia
    grid_html = ""
    for e in entries:
        grid_html += f"""<div class='card' onclick='openInfo({{id:"{e['id']}"}})'>
<img class='poster' src='{e['poster']}' alt='{e['title']}' title='{e['title']}'>
<div class='badge'>{e['vote']}</div>
</div>"""

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
.favorite-btn{{font-size:20px;color:#000;text-shadow:0 0 4px #000;cursor:pointer;}}
.favorite-btn.active{{color:gold;}}
button{{background:#000;color:#fff;border:none;border-radius:6px;padding:8px 12px;cursor:pointer;font-size:14px;}}
button:focus{{outline:2px solid #e50914;}}
#loadMore{{display:block;margin:20px auto;padding:10px 20px;font-size:16px;background:#e50914;color:#fff;border:none;border-radius:8px;cursor:pointer;}}
#playerOverlay{{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.9);display:none;align-items:center;justify-content:center;z-index:1000;flex-direction:column;}}
#playerOverlay iframe{{width:100%;height:100%;border:none;position:relative;z-index:1;}}
#playerTitle{{position:absolute;top:20px;left:50%;transform:translateX(-50%);background:rgba(0,0,0,0.7);color:#fff;padding:8px 12px;border-radius:8px;font-size:18px;display:none;z-index:10;}}
#infoCard{{position:fixed; top:0; left:0; width:100%; height:100%; display:none; z-index:1001; color:#fff; padding:20px; overflow:auto; background-color:#000; background-size:cover; background-position:center center; background-repeat:no-repeat;}}
#infoCard h2, #infoCard p{{text-shadow:0 2px 6px rgba(0,0,0,.75);}}
#infoCard .content-wrap{{position:relative; padding:40px 20px 20px 20px; max-width:800px; width:90%; margin:0 auto;}}
@media(min-width:768px){{#infoCard .content-wrap{{ padding-top:150px; }}}}
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
<div id='moviesGrid' class='grid'>
{grid_html}
</div>
<button id='loadMore'>Carica altri</button>
<div id='playerOverlay'>
  <iframe allow="autoplay; fullscreen; encrypted-media" allowfullscreen></iframe>
  <div id="playerTitle"></div>
</div>

<div id='infoCard'>
  <div class="content-wrap">
    <h2 id="infoTitle"></h2>
    <div style="display:flex;align-items:center;gap:10px;margin:10px 0;">
      <button id="playBtn">Riproduci</button>
      <button id="closeCardBtn">Chiudi</button>
      <button id="favoriteInCard" class="favorite-btn">+ La mia lista</button>
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
const typeSelect=document.getElementById('typeSelect');
const searchBox=document.getElementById('searchBox');

// --- Funzioni principali ---
function openInfo(item){ 
    currentItem=item;
    const info=allData.find(e=>e.id===item.id);
    if(!info) return;
    infoCard.style.display='block';
    infoTitle.innerText=info.title;
    infoGenres.innerText='Generi: '+info.genres.join(', ');
    infoVote.innerText='Voto: '+info.vote;
    infoOverview.innerText=info.overview;
    infoYear.innerText='Anno: '+info.year;
    infoDuration.innerText='Durata: '+(info.duration||'N/A')+' min';
    infoCast.innerText='Cast: '+info.cast.join(', ');
    favoriteInCard.classList.toggle('active', favorites.includes(info.id));

    seasonSelect.innerHTML='';
    episodeSelect.innerHTML='';
    if(info.type==='tv' && info.seasons>0){
        for(let s=1;s<=info.seasons;s++){
            let opt=document.createElement('option');
            opt.value=s;
            opt.textContent='Stagione '+s;
            seasonSelect.appendChild(opt);
        }
        seasonSelect.onchange();
    }
    history.pushState({"page":"info","id":info.id},"","#info");
}

function openPlayer(link,title){
    iframe.src=link;
    overlay.style.display='flex';
    playerTitle.innerText=title;
    playerTitle.style.display='block';
    addToRecent(currentItem.id);
}

function closePlayer(){
    iframe.src='';
    overlay.style.display='none';
    playerTitle.style.display='none';
}

function toggleFavorite(){
    if(!currentItem) return;
    const id=currentItem.id;
    if(favorites.includes(id)){
        favorites=favorites.filter(f=>f!==id);
        favoriteInCard.classList.remove('active');
    }else{
        favorites.push(id);
        favoriteInCard.classList.add('active');
    }
    localStorage.setItem('favorites',JSON.stringify(favorites));
}

function addToRecent(id){
    recentList=recentList.filter(r=>r!==id);
    recentList.unshift(id);
    if(recentList.length>20) recentList.pop();
    localStorage.setItem('recent',JSON.stringify(recentList));
}

closeCardBtn.onclick=()=>{ infoCard.style.display='none'; history.replaceState({"page":"grid"},"","#grid"); };
playBtn.onclick=()=>{ const info=allData.find(e=>e.id===currentItem.id); if(info.link) openPlayer(info.link,info.title); };
favoriteInCard.onclick=toggleFavorite;

// Scroll ultime novità
let scrollPos=0;
function scrollLatest(){
    scrollPos += 1;
    if(scrollPos>latestDiv.scrollWidth-latestDiv.clientWidth) scrollPos=0;
    latestDiv.scrollTo({left:scrollPos, behavior:'smooth'});
}
setInterval(scrollLatest,30);

// Firestick & TV: gestione focus tasti
const focusable = [playBtn, closeCardBtn, favoriteInCard];
let focusIndex = 0;
function updateFocus(){
    focusable.forEach((b,i)=>b.style.outline=(i===focusIndex?'2px solid #e50914':'none'));
}
document.addEventListener('keydown',(e)=>{
    if(infoCard.style.display==='block'){
        if(e.key==='ArrowRight'){ focusIndex=(focusIndex+1)%focusable.length; updateFocus(); e.preventDefault();}
        else if(e.key==='ArrowLeft'){ focusIndex=(focusIndex-1+focusable.length)%focusable.length; updateFocus(); e.preventDefault();}
        else if(e.key==='Enter'){ focusable[focusIndex].click(); e.preventDefault();}
    }
});
updateFocus();

// Filtri generi e ricerca
function applyFilters(){
    const type=typeSelect.value;
    const search=searchBox.value.toLowerCase();
    const genres=[...genreSelect.selectedOptions].map(o=>o.value);
    grid.innerHTML='';
    let filtered=allData;
    if(type==='favorites') filtered=allData.filter(e=>favorites.includes(e.id));
    else if(type==='recent') filtered=allData.filter(e=>recentList.includes(e.id));
    else filtered=allData.filter(e=>e.type===type);
    if(genres.length>0) filtered=filtered.filter(e=>genres.every(g=>e.genres.includes(g)));
    if(search) filtered=filtered.filter(e=>e.title.toLowerCase().includes(search));
    for(const e of filtered){
        const div=document.createElement('div');
        div.className='card';
        div.innerHTML=`<img class='poster' src='${e.poster}' alt='${e.title}' title='${e.title}'><div class='badge'>${e.vote}</div>`;
        div.onclick=()=>openInfo({id:e.id});
        grid.appendChild(div);
    }
}

typeSelect.onchange=applyFilters;
searchBox.oninput=applyFilters;
genreSelect.onchange=applyFilters;

// Popola selezione generi
const genreSet=new Set();
allData.forEach(e=>e.genres.forEach(g=>genreSet.add(g)));
genreSet.forEach(g=>{
    const opt=document.createElement('option');
    opt.value=g;
    opt.textContent=g;
    genreSelect.appendChild(opt);
});

applyFilters();
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
            seasons = info.get("number_of_seasons", 1) if type_=="tv" else 0
            episodes = {}
            if type_=="tv":
                for s in info.get("seasons", []):
                    season_number = s.get("season_number")
                    if season_number:
                        episodes[season_number] = s.get("episode_count", 1)

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

            if idx < 10 and poster:
                latest_entries += f"<img class='poster' src='{poster}' alt='{title}' title='{title}'>\n"

    html = build_html(entries, latest_entries)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Generato {OUTPUT_HTML} con {len(entries)} elementi e ultime novità scrollabili")

if __name__ == "__main__":
    main()
