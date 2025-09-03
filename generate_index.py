#!/usr/bin/env python3
"""
generate_index.py

Script per generare una pagina HTML con film e serie TV da VixSrc/TMDB.
Funzionalità:
- Ricerca, filtro per generi, caricamento incrementale
- Preferiti con stellina (localStorage)
- Visti di recente (localStorage)
- Ultime novità in carosello orizzontale
- Back button: chiude prima il player poi la card
- InfoCard fullscreen (MODIFICA)
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
        params={"api_key": api_key, "language": language, "append_to_response": "credits"},
        timeout=15
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


def build_html(entries, latest_entries):
    import json
    entries_js = json.dumps(entries, ensure_ascii=False)

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

/* 🔹 infocard fullscreen */
#infoCard{{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(20,20,20,0.95);display:none;z-index:1001;backdrop-filter:blur(8px);color:#fff;padding:40px;overflow:auto;box-sizing:border-box;}}
#infoCard h2{{margin-top:0;color:#e50914;display:inline-block;}}
#infoCard button#playBtn{{margin-left:10px;padding:8px 12px;background:#e50914;border:none;color:#fff;border-radius:5px;cursor:pointer;vertical-align:middle;}}
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

<!-- 🔹 infocard fullscreen -->
<div id='infoCard'>
  <h2 id="infoTitle"></h2>
  <div style="display:flex;align-items:center;gap:10px;margin:10px 0;">
    <button id="playBtn">Riproduci</button>
    <button id="closeCardBtn">Chiudi</button>
    <span id="favoriteInCard" class="favorite-btn">★</span>
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

<script>
const allData = {entries_js};
let favorites = JSON.parse(localStorage.getItem("favorites") || "[]");
let recentList = JSON.parse(localStorage.getItem("recent") || "[]");
let currentItem = null;
let shown = 0;
let currentList = [];

function renderGenres(){
  let genreSet = new Set();
  allData.forEach(m => m.genres.forEach(g => genreSet.add(g)));
  let sel = document.getElementById('genreSelect');
  sel.innerHTML = "";
  Array.from(genreSet).sort().forEach(g => {{
    let opt = document.createElement('option');
    opt.value = g;
    opt.textContent = g;
    sel.appendChild(opt);
  }});
}

function renderList(reset=true){
  let grid = document.getElementById('moviesGrid');
  if(reset){{grid.innerHTML="";shown=0;}}
  let count=0;
  let search=document.getElementById('searchBox').value.toLowerCase();
  let gSel=Array.from(document.getElementById('genreSelect').selectedOptions).map(o=>o.value);
  let typeSel=document.getElementById('typeSelect').value;
  if(typeSel==="favorites") currentList=allData.filter(m=>favorites.includes(m.id));
  else if(typeSel==="recent") currentList=allData.filter(m=>recentList.includes(m.id));
  else currentList=allData.filter(m=>m.type===typeSel);

  while(shown<currentList.length && count<40){{
    let m=currentList[shown++];
    let isFav=favorites.includes(m.id);
    let genreMatch=gSel.length===0||gSel.includes('all')||m.genres.some(g=>gSel.includes(g));
    if(m.title.toLowerCase().includes(search)&&genreMatch){{
      let div=document.createElement('div');
      div.className="card";
      div.innerHTML=`<img src="${m.poster}" class="poster"><div class="favorite-btn ${isFav?"active":""}">★</div>`;
      div.onclick=()=>openInfo(m);
      grid.appendChild(div);
      count++;
    }}
  }}
}

function openInfo(m){{
  currentItem=m;
  document.getElementById('infoTitle').textContent=m.title;
  document.getElementById('infoGenres').textContent="Generi: "+m.genres.join(", ");
  document.getElementById('infoVote').textContent="Voto: "+m.vote;
  document.getElementById('infoOverview').textContent=m.overview;
  document.getElementById('infoYear').textContent="Anno: "+m.year;
  document.getElementById('infoDuration').textContent="Durata: "+(m.duration||"-")+" min";
  document.getElementById('infoCast').textContent="Cast: "+m.cast.join(", ");
  let favBtn=document.getElementById('favoriteInCard');
  favBtn.classList.toggle("active",favorites.includes(m.id));
  document.getElementById('infoCard').style.display="block";

  // stagioni
  let sSel=document.getElementById('seasonSelect');
  let eSel=document.getElementById('episodeSelect');
  sSel.innerHTML=""; eSel.innerHTML="";
  if(m.type==="tv"){{
    for(let s=1;s<=m.seasons;s++){{
      let opt=document.createElement('option');
      opt.value=s; opt.textContent="Stagione "+s;
      sSel.appendChild(opt);
    }}
    sSel.onchange=()=>renderEpisodes(m);
    renderEpisodes(m);
  }}
}}

function renderEpisodes(m){{
  let sSel=document.getElementById('seasonSelect');
  let eSel=document.getElementById('episodeSelect');
  eSel.innerHTML="";
  let season=sSel.value;
  let epCount=m.episodes[season]||0;
  for(let e=1;e<=epCount;e++){{
    let opt=document.createElement('option');
    opt.value=e; opt.textContent="Episodio "+e;
    eSel.appendChild(opt);
  }}
}}

function openPlayer(m){{
  let overlay=document.getElementById('playerOverlay');
  let iframe=overlay.querySelector('iframe');
  let titleBox=document.getElementById('playerTitle');
  iframe.src=m.link||"https://vixsrc.to/embed/"+m.id;
  overlay.style.display="flex";
  titleBox.textContent=m.title;
  titleBox.style.display="block";
  setTimeout(()=>titleBox.style.display="none",3000);
  if(!recentList.includes(m.id)){{
    recentList.unshift(m.id);
    if(recentList.length>20) recentList.pop();
    localStorage.setItem("recent",JSON.stringify(recentList));
  }}
}}

function closePlayer(){{
  let overlay=document.getElementById('playerOverlay');
  overlay.querySelector('iframe').src="";
  overlay.style.display="none";
}}

document.getElementById('playBtn').onclick=()=>openPlayer(currentItem);
document.getElementById('closeCardBtn').onclick=()=>document.getElementById('infoCard').style.display="none";
document.getElementById('loadMore').onclick=()=>renderList(false);
document.getElementById('searchBox').oninput=()=>renderList();
document.getElementById('genreSelect').onchange=()=>renderList();
document.getElementById('typeSelect').onchange=()=>renderList();

document.getElementById('favoriteInCard').onclick=()=>{
  if(!currentItem)return;
  let id=currentItem.id;
  if(favorites.includes(id)) favorites=favorites.filter(f=>f!==id);
  else favorites.push(id);
  localStorage.setItem("favorites",JSON.stringify(favorites));
  document.getElementById('favoriteInCard').classList.toggle("active",favorites.includes(id));
  renderList();
};

window.onpopstate=()=>{
  if(document.getElementById('playerOverlay').style.display==="flex") closePlayer();
  else if(document.getElementById('infoCard').style.display==="block") document.getElementById('infoCard').style.display="none";
};

renderGenres();
renderList();
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
            episodes = {str(s["season_number"]): s.get("episode_count", 1) for s in info.get("seasons", []) if s.get("season_number")} if type_=="tv" else {}

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

            if idx < 10:
                latest_entries += f"<img class='poster' src='{poster}' alt='{title}' title='{title}'>\\n"

    html = build_html(entries, latest_entries)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Generato {OUTPUT_HTML} con {len(entries)} elementi")


if __name__ == "__main__":
    main()
