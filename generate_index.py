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
import json

# --- Config ---
SRC_URLS = {{
    "movie": "https://vixsrc.to/api/list/movie?lang=it",
    "tv": "https://vixsrc.to/api/list/tv?lang=it"
}}
TMDB_BASE = "https://api.themoviedb.org/3/{{type}}/{{id}}"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w300"
VIX_LINK_MOVIE = "https://vixsrc.to/movie/{{}}/?"
OUTPUT_HTML = "index.html"
HEADERS = {{"User-Agent": "Mozilla/5.0 (compatible; script/1.0)"}}


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
        params={{"api_key": api_key, "language": language, "append_to_response": "credits"}},
        timeout=15
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


def build_html(entries, latest_entries):
    entries_js = json.dumps(entries, ensure_ascii=False)

    html = f"""<!doctype html>
<html lang='it'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Movies & Series</title>
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
#favoriteInCard.favorite-btn{{{{position:static;cursor:pointer;margin-left:auto;font-size:22px;}}}}
#loadMore{{{{display:block;margin:20px auto;padding:10px 20px;font-size:16px;background:#e50914;color:#fff;border:none;border-radius:8px;cursor:pointer;}}}}
#playerOverlay{{{{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.9);display:none;align-items:center;justify-content:center;z-index:1000;flex-direction:column;}}}}
#playerOverlay iframe{{{{width:100%;height:100%;border:none;position:relative;z-index:1;}}}}
#playerTitle{{{{position:absolute;top:20px;left:50%;transform:translateX(-50%);background:rgba(0,0,0,0.7);color:#fff;padding:8px 12px;border-radius:8px;font-size:18px;display:none;z-index:10;}}}}

/* 🔹 infocard fullscreen */
#infoCard{{{{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(20,20,20,0.95);display:none;z-index:1001;backdrop-filter:blur(8px);color:#fff;padding:40px;overflow:auto;box-sizing:border-box;}}}}
#infoCard h2{{{{margin-top:0;color:#e50914;display:inline-block;}}}}
#infoCard button#playBtn{{{{margin-left:10px;padding:8px 12px;background:#e50914;border:none;color:#fff;border-radius:5px;cursor:pointer;vertical-align:middle;}}}}
#infoCard p{{{{margin:5px 0;}}}}
#infoCard select{{{{margin:5px 5px 5px 0;padding:6px;}}}}

#latest{{{{display:flex;overflow-x:auto;gap:10px;margin-bottom:20px;padding-bottom:10px;scroll-behavior: smooth;}}}}
#latest::-webkit-scrollbar {{{{display: none;}}}}
#latest {{{{-ms-overflow-style: none;scrollbar-width: none;}}}}
#latest .poster{{{{width:100px;flex-shrink:0;}}}}
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

function renderGenres() {{
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
}}

function showList() {{
  let grid = document.getElementById('moviesGrid');
  let count = 0;
  let search = document.getElementById('searchBox').value.toLowerCase();
  let gSel = Array.from(document.getElementById('genreSelect').selectedOptions).map(o => o.value);
  let typeSel = document.getElementById('typeSelect').value;

  grid.innerHTML = "";
  shown = 0;
  let filtered = allData.filter(m => {{
    if (typeSel==='favorites' && !favorites.includes(m.id)) return false;
    if (typeSel==='recent' && !recentList.includes(m.id)) return false;
    if (typeSel!=='favorites' && typeSel!=='recent' && m.type!==typeSel) return false;
    if (search && !m.title.toLowerCase().includes(search)) return false;
    if (gSel.length>0 && !gSel.some(g => m.genres.includes(g))) return false;
    return true;
  }});
  currentList = filtered;

  loadMore();
}}

function loadMore() {{
  let grid = document.getElementById('moviesGrid');
  let count = 0;
  while(shown<currentList.length && count<40) {{
    let m = currentList[shown++];
    let card = document.createElement('div');
    card.className = 'card';
    card.onclick = () => openInfo(m);

    let img = document.createElement('img');
    img.src = m.poster;
    img.className = 'poster';
    card.appendChild(img);

    let fav = document.createElement('span');
    fav.className = 'favorite-btn' + (favorites.includes(m.id)?' active':'');
    fav.textContent = '★';
    card.appendChild(fav);

    let b = document.createElement('div');
    b.className = 'badge';
    b.textContent = m.type==='movie'?'Film':'Serie';
    card.appendChild(b);

    grid.appendChild(card);
    count++;
  }}
  document.getElementById('loadMore').style.display = shown<currentList.length? 'block':'none';
}}

function toggleFavorite(id) {{
  if (favorites.includes(id)) {{
    favorites = favorites.filter(f => f!==id);
  }} else {{
    favorites.push(id);
  }}
  localStorage.setItem("favorites", JSON.stringify(favorites));
  showList();
}}

function openInfo(m) {{
  currentItem = m;
  document.getElementById('infoTitle').textContent = m.title;
  document.getElementById('infoGenres').textContent = "Generi: "+m.genres.join(", ");
  document.getElementById('infoVote').textContent = "Voto: "+m.vote;
  document.getElementById('infoOverview').textContent = m.overview;
  document.getElementById('infoYear').textContent = "Anno: "+m.year;
  document.getElementById('infoDuration').textContent = "Durata: "+m.runtime;
  document.getElementById('infoCast').textContent = "Cast: "+m.cast.join(", ");
  document.getElementById('favoriteInCard').className = "favorite-btn"+(favorites.includes(m.id)?' active':'');
  document.getElementById('infoCard').style.display = 'block';
}}

function closeInfo() {{
  document.getElementById('infoCard').style.display = 'none';
}}

document.getElementById('playBtn').onclick = () => {{
  if (!currentItem) return;
  document.getElementById('playerOverlay').style.display = 'flex';
  document.querySelector('#playerOverlay iframe').src = currentItem.link;
  document.getElementById('playerTitle').textContent = currentItem.title;
  document.getElementById('playerTitle').style.display = 'block';

  if (!recentList.includes(currentItem.id)) {{
    recentList.push(currentItem.id);
    localStorage.setItem("recent", JSON.stringify(recentList));
  }}
}};

document.getElementById('closeCardBtn').onclick = closeInfo;
document.getElementById('favoriteInCard').onclick = () => {{
  if (currentItem) toggleFavorite(currentItem.id);
  document.getElementById('favoriteInCard').classList.toggle('active');
}};

document.getElementById('loadMore').onclick = loadMore;
document.getElementById('typeSelect').onchange = showList;
document.getElementById('genreSelect').onchange = showList;
document.getElementById('searchBox').oninput = showList;

renderGenres();
showList();
</script>
</body>
</html>
"""
    return html


def main():
    api_key = get_api_key()
    entries = []
    latest_entries_html = ""
    for t, url in SRC_URLS.items():
        data = fetch_list(url)
        ids = extract_ids(data)
        for tmdb_id in ids[:50]:  # limita a 50 per test
            info = tmdb_get(api_key, t, tmdb_id)
            if not info:
                continue
            entry = {{
                "id": f"{{t}}_{{tmdb_id}}",
                "type": t,
                "title": info.get("title") or info.get("name",""),
                "poster": TMDB_IMAGE_BASE + info.get("poster_path",""),
                "overview": info.get("overview",""),
                "genres": [g["name"] for g in info.get("genres",[])],
                "vote": info.get("vote_average",0),
                "year": (info.get("release_date") or info.get("first_air_date",""))[:4],
                "runtime": str(info.get("runtime") or "")+" min",
                "cast": [c["name"] for c in info.get("credits",{{}}).get("cast",[])[:5]],
                "link": VIX_LINK_MOVIE.format(tmdb_id)
            }}
            entries.append(entry)
            if len(latest_entries_html)<2000:
                latest_entries_html += f"<img src='{{entry['poster']}}' class='poster'>"
    html = build_html(entries, latest_entries_html)
    with open(OUTPUT_HTML,"w",encoding="utf-8") as f:
        f.write(html)


if __name__=="__main__":
    main()
