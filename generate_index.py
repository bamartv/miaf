#!/usr/bin/env python3
"""
generate_index.py

Genera pagina HTML con tutte le funzionalità:
- Preferiti e Visti recentemente
- Stellina sulle locandine
- Info card con locandina di sfondo e dissolvenza nera
- Trailer autoplay per ogni film
- Generi multipli, ricerca e filtro
- Player fullscreen
- Back button corretto
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
        params={"api_key": api_key, "language": language, "append_to_response": "credits,videos"},
        timeout=15
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()

def build_html(entries, latest_entries):
    html = f"""<!DOCTYPE html>
<html lang='it'>
<head>
<meta charset='UTF-8'>
<meta name='viewport' content='width=device-width, initial-scale=1.0'>
<title>Movies & Series</title>
<style>
body {{
    margin:0;
    font-family: Arial, sans-serif;
    background:#000;
    color:#fff;
}}
.controls {{
    display:flex;gap:10px;justify-content:center;margin-bottom:20px;flex-wrap:wrap;
}}
input,select {{
    padding:8px;font-size:14px;border-radius:4px;border:none;
}}
.grid {{
    display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:12px;
}}
.card {{
    position:relative;cursor:pointer;transition: transform 0.2s;border-radius:12px;overflow:hidden;border:2px solid #444;background:#1f1f1f;
}}
.card:hover {{
    transform:scale(1.05);border-color:#e50914;background:#2a2a2a;
}}
.poster {{
    width:100%;border-radius:0;display:block;
}}
.badge {{
    position:absolute;top:8px;right:8px;background:#e50914;color:#fff;padding:4px 6px;font-size:14px;font-weight:bold;border-radius:8px;text-align:center;
}}
.favorite-btn {{
    font-size:20px;color:#fff;text-shadow:0 0 4px #000;
}}
.favorite-btn.active {{color:gold;}}
.card .favorite-btn{{position:absolute;top:8px;left:8px;pointer-events:none;}}
#favoriteInCard.favorite-btn{{position:static;cursor:pointer;margin-left:auto;font-size:22px;}}
#loadMore{{display:block;margin:20px auto;padding:10px 20px;font-size:16px;background:#e50914;color:#fff;border:none;border-radius:8px;cursor:pointer;}}
#playerOverlay{{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.9);display:none;align-items:center;justify-content:center;z-index:1000;flex-direction:column;}}
#playerOverlay iframe{{width:100%;height:100%;border:none;position:relative;z-index:1;}}
#playerTitle{{position:absolute;top:20px;left:50%;transform:translateX(-50%);background:rgba(0,0,0,0.7);color:#fff;padding:8px 12px;border-radius:8px;font-size:18px;display:none;z-index:10;}}
#infoCard {{
    position:fixed;top:0;left:0;width:100%;height:100%;display:none;z-index:1001;backdrop-filter:blur(8px);color:#fff;overflow:auto;
}}
#infoContent {{
    position:relative;max-width:800px;margin:40px auto;padding:20px;border-radius:10px;
}}
#infoCard h2{{margin-top:0;color:#fff;}}
#infoCard p{{margin:5px 0;}}
#infoCard button {{
    padding:8px 12px;border:none;border-radius:5px;cursor:pointer;margin-right:5px;
}}
#infoCard #playBtn, #infoCard #favoriteInCard, #infoCard #closeCardBtn {{
    background:#000;color:#fff;
}}
#trailer {{
    width:100%;max-width:500px;height:280px;border:none;border-radius:8px;margin-bottom:20px;
}}
#related {{
    display:flex;overflow-x:auto;gap:10px;padding-bottom:10px;
}}
#related::-webkit-scrollbar {{display:none;}}
.related-item {{flex:0 0 auto;width:120px;border-radius:6px;}}
.related-item img {{width:100%;border-radius:6px;}}
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
  <iframe allow='autoplay; fullscreen; encrypted-media' allowfullscreen></iframe>
  <div id='playerTitle'></div>
</div>

<div id='infoCard'>
  <div id='infoContent'>
    <h2 id='infoTitle'></h2>
    <div style='display:flex;align-items:center;gap:10px;margin:10px 0;'>
      <button id='playBtn'>Riproduci</button>
      <button id='favoriteInCard'>★</button>
      <button id='closeCardBtn'>Chiudi</button>
    </div>
    <p id='infoGenres'></p>
    <p id='infoVote'></p>
    <p id='infoOverview'></p>
    <p id='infoYear'></p>
    <p id='infoDuration'></p>
    <p id='infoCast'></p>
    <iframe id='trailer' allowfullscreen></iframe>
    <h3>Film correlati</h3>
    <div id='related'></div>
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
const infoYear=document.getElementById('infoYear');
const infoDuration=document.getElementById('infoDuration');
const infoCast=document.getElementById('infoCast');
const playBtn=document.getElementById('playBtn');
const closeCardBtn=document.getElementById('closeCardBtn');
const favoriteInCard=document.getElementById('favoriteInCard');
const trailer=document.getElementById('trailer');
const latestDiv=document.getElementById('latest');
const genreSelect=document.getElementById('genreSelect');

closeCardBtn.onclick = () => {{
    infoCard.style.display='none';
    trailer.src='';
    history.replaceState({{page:"grid"}}, "", "#grid");
}};

function openInfo(item, push=true) {{
    currentItem = item;
    infoCard.style.display='block';
    infoContent.style.backgroundImage = `linear-gradient(to bottom, rgba(0,0,0,0) 35%, rgba(0,0,0,1) 50%, rgba(0,0,0,1) 100%), url('${{item.poster}}')`;
    infoContent.style.backgroundSize='cover';
    infoContent.style.backgroundPosition='center';
    
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

    trailer.src = item.trailer ? item.trailer + "?autoplay=1" : "";
    
    const relatedDiv = document.getElementById('related');
    relatedDiv.innerHTML = '';
    if(item.related && item.related.length) {{
        item.related.forEach(r=>{{
            const div = document.createElement('div');
            div.className='related-item';
            div.innerHTML=`<img src='${{r.poster}}' alt='${{r.title}}'>`;
            div.onclick = () => openInfo(r);
            relatedDiv.appendChild(div);
        }});
    }}

    if(push) history.pushState({{page:"info", itemId:item.id}}, "", "#info-"+item.id);
}}

function toggleFavorite(id) {{
  if(favorites.includes(id)) favorites = favorites.filter(f=>f!==id);
  else favorites.push(id);
  localStorage.setItem("favorites", JSON.stringify(favorites));
  render(true);
}}

function addToRecent(id) {{
  recentList = recentList.filter(x => x !== id);
  recentList.unshift(id);
  if(recentList.length > 20) recentList.pop();
  localStorage.setItem("recent", JSON.stringify(recentList));
}}

function openPlayer(item, push=true) {{
    infoCard.style.display='none';
    overlay.style.display='flex';
    iframe.src = item.link + "&autoplay=1";
    addToRecent(item.id);
    if(overlay.requestFullscreen) overlay.requestFullscreen();
    else if(overlay.webkitRequestFullscreen) overlay.webkitRequestFullscreen();
    else if(overlay.msRequestFullscreen) overlay.msRequestFullscreen();
    if(push) history.pushState({{page:"player", itemId:item.id}}, "", "#player-"+item.id);
}}

function closePlayer() {{
    overlay.style.display='none';
    iframe.src='';
    if(document.fullscreenElement) document.exitFullscreen();
    if(currentItem) infoCard.style.display='block';
}}

window.addEventListener("popstate", function(e){{
    const state = e.state;
    if(!state || state.page==="grid") {{
        overlay.style.display='none';
        iframe.src='';
        infoCard.style.display='none';
        return;
    }}
    const item = allData.find(x=>x.id==state.itemId);
    if(!item) return;
    if(state.page==="player") openPlayer(item,false);
    else if(state.page==="info") openInfo(item,false);
}});

let currentType='movie', currentList=[], shown=0;

function render(reset=false) {{
    if(reset) {{ grid.innerHTML=''; shown=0; }}
    let count=0;
    let s=document.getElementById('searchBox').value.toLowerCase();
    let gSel=Array.from(genreSelect.selectedOptions).map(o=>o.value);
    while(shown<currentList.length && count<40) {{
        let m = currentList[shown++];
        let isFav = favorites.includes(m.id);
        let genreMatch = gSel.length===0 || gSel.includes('all') || gSel.every(g => m.genres.includes(g));
        if(genreMatch && m.title.toLowerCase().includes(s)) {{
            const card = document.createElement('div');
            card.className='card';
            card.innerHTML=`
                <img class='poster' src='${{m.poster}}' alt='${{m.title}}'>
                <div class='badge'>${{m.vote}}</div>
                <span class="favorite-btn ${{isFav?'active':''}}" style="pointer-events:none;">★</span>
            `;
            card.onclick=()=>openInfo(m);
            grid.appendChild(card);
            count++;
        }}
    }}
}}

function populateGenres(){{
    const set=new Set();
    currentList.forEach(m=>m.genres.forEach(g=>set.add(g)));
    genreSelect.innerHTML='<option value="all">Tutti i generi</option>';
    [...set].sort().forEach(g=>{{
        const o=document.createElement('option');
        o.value=o.textContent=g;
        genreSelect.appendChild(o);
    }});
}}

function updateType(t){{
    currentType=t;
    if(t==="movie" || t==="tv") {{
        currentList=allData.filter(x=>x.type===t);
        genreSelect.style.display='inline';
        populateGenres();
    }} else if(t==="favorites") {{
        currentList=allData.filter(x=>favorites.includes(x.id));
        genreSelect.style.display='none';
    }} else if(t==="recent") {{
        currentList=allData.filter(x=>recentList.includes(x.id));
        genreSelect.style.display='none';
    }}
    render(true);
}}

document.getElementById('typeSelect').onchange=e=>updateType(e.target.value);
document.getElementById('genreSelect').onchange=()=>render(true);
document.getElementById('searchBox').oninput=()=>render(true);
document.getElementById('loadMore').onclick=()=>render(false);

history.replaceState({{page:"grid"}}, "", "#grid");
updateType('movie');
</script>
</body>
</html>"""
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
                continue
            if not info:
                continue

            title = info.get("title") or info.get("name") or f"ID {tmdb_id}"
            poster = TMDB_IMAGE_BASE + info["poster_path"] if info.get("poster_path") else ""
            genres = [g["name"] for g in info.get("genres", [])]
            vote = info.get("vote_average", 0)
            overview = info.get("overview", "")
            year = (info.get("release_date") or info.get("first_air_date") or "")[:4]
            runtime_list = info.get("episode_run_time") or []
            duration = info.get("runtime") or (runtime_list[0] if runtime_list else None)
            cast = [c["name"] for c in info.get("credits", {}).get("cast", [])] if info.get("credits") else []

            # Prende trailer YouTube ufficiale
            trailer = ""
            videos = info.get("videos", {}).get("results", [])
            for v in videos:
                if v.get("site")=="YouTube" and v.get("type")=="Trailer":
                    trailer = "https://www.youtube.com/embed/" + v.get("key")
                    break

            entries.append({{
                "id": str(tmdb_id),
                "title": title,
                "poster": poster,
                "genres": genres,
                "vote": vote,
                "overview": overview,
                "link": VIX_LINK_MOVIE.format(tmdb_id),
                "type": type_,
                "duration": duration or 0,
                "year": year or "",
                "cast": cast,
                "trailer": trailer,
                "related": []
            }})

            if idx < 10:
                latest_entries += f"<img class='poster' src='{poster}' alt='{title}' title='{title}'>\n"

    html = build_html(entries, latest_entries)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Generato {OUTPUT_HTML} con {len(entries)} elementi e ultime novità scrollabili")

if __name__ == "__main__":
    main()
