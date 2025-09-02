#!/usr/bin/env python3
"""
generate_index.py

Aggiunta gestione Preferiti con stellina e filtro multi-genere.
- Stellina sulle locandine: solo visuale (non cliccabile)
- Stellina cliccabile dentro la card info
- Possibilità di selezionare più generi
- Menu principale con Film, Serie TV, Preferiti, Recenti
- Titolo che appare nel player quando si tocca lo schermo e sparisce dopo 2 secondi
"""

import os, requests

TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"
OUTPUT_HTML = "index.html"

# --- CONFIG ---
VIX_LINK_MOVIE = "https://embedder.net/e/movie?id={}"
SRC_URLS = {
    "movie": "https://api.themoviedb.org/3/movie/popular?language=it-IT&page=1",
    "tv": "https://api.themoviedb.org/3/tv/popular?language=it-IT&page=1"
}
# ---------------

def get_api_key():
    return os.environ.get("TMDB_KEY","")

def fetch_list(url):
    resp = requests.get(url+"&api_key="+get_api_key())
    return resp.json() if resp.ok else {}

def extract_ids(data):
    return [m["id"] for m in data.get("results",[])]

def tmdb_get(api_key, type_, tmdb_id):
    url = f"https://api.themoviedb.org/3/{type_}/{tmdb_id}?api_key={api_key}&language=it-IT&append_to_response=credits,seasons"
    r = requests.get(url)
    return r.json() if r.ok else None

def build_html(entries, latest_html):
    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<title>Catalogo</title>
<style>
body {{margin:0;font-family:sans-serif;background:#111;color:#eee}}
header {{padding:10px;text-align:center;background:#222;position:sticky;top:0;z-index:1000}}
#searchBox {{width:60%;padding:8px}}
#typeSelect {{padding:8px}}
.grid {{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;padding:10px}}
.poster {{width:100%;border-radius:10px;cursor:pointer}}
#infoOverlay, #playerOverlay {{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.9);color:#fff;display:none;z-index:1001;overflow:auto}}
.overlay-content {{padding:20px;max-width:600px;margin:auto}}
.close-btn {{position:absolute;top:10px;right:20px;cursor:pointer;font-size:24px}}
.star {{cursor:pointer;font-size:24px;color:#ff0}}
#playerOverlay iframe {{width:100%;height:60%}}
#latest {{display:flex;overflow-x:auto;gap:10px;padding:10px}}
#playerTitle {{
  position:absolute;
  top:20px;
  left:50%;
  transform:translateX(-50%);
  background:rgba(0,0,0,0.7);
  color:#fff;
  padding:8px 12px;
  border-radius:8px;
  font-size:18px;
  display:none;
  z-index:1002;
}}
</style>
</head>
<body>
<header>
  <input id="searchBox" placeholder="Cerca...">
  <select id="typeSelect">
    <option value="movie">Film</option>
    <option value="tv">Serie TV</option>
    <option value="fav">Preferiti</option>
    <option value="recent">Recenti</option>
  </select>
</header>
<div id="latest">{latest_html}</div>
<div id="grid" class="grid"></div>

<div id="infoOverlay">
  <div class="overlay-content">
    <span class="close-btn" onclick="closeInfo()">&times;</span>
    <h2 id="infoTitle"></h2>
    <img id="infoPoster" style="width:200px">
    <p id="infoOverview"></p>
    <p id="infoDetails"></p>
    <span id="favStar" class="star" onclick="toggleFavorite()">&#9733;</span>
    <button onclick="openPlayer()">Guarda</button>
  </div>
</div>

<div id="playerOverlay">
  <span class="close-btn" onclick="closePlayer()">&times;</span>
  <iframe id="playerFrame" src="" frameborder="0" allowfullscreen></iframe>
  <div id="playerTitle"></div>
</div>

<script>
let allEntries = {entries};
let currentList = allEntries;
let currentItem = null;
let favorites = JSON.parse(localStorage.getItem("favorites")||"[]");
let recent = JSON.parse(localStorage.getItem("recent")||"[]");

function showList(list) {{
  const grid=document.getElementById('grid');
  grid.innerHTML="";
  list.forEach(m=>{{
    let div=document.createElement("div");
    div.innerHTML=`<img class='poster' src='${{m.poster}}' alt='${{m.title}}' onclick='openInfo(${{JSON.stringify(m)}})'>`;
    grid.appendChild(div);
  }});
}}

function openInfo(m) {{
  currentItem=m;
  document.getElementById("infoTitle").innerText=m.title;
  document.getElementById("infoPoster").src=m.poster;
  document.getElementById("infoOverview").innerText=m.overview;
  document.getElementById("infoDetails").innerText=(m.year||"")+" | Voto: "+m.vote;
  document.getElementById("infoOverlay").style.display="block";
  document.getElementById("favStar").style.color=favorites.includes(m.id)?"#ff0":"#555";
}}

function closeInfo() {{
  document.getElementById("infoOverlay").style.display="none";
}}

function openPlayer() {{
  document.getElementById("infoOverlay").style.display="none";
  document.getElementById("playerOverlay").style.display="block";
  document.getElementById("playerFrame").src=currentItem.link||"";
  // salva nei recenti
  if(!recent.includes(currentItem.id)) {{
    recent.unshift(currentItem.id);
    if(recent.length>20) recent.pop();
    localStorage.setItem("recent",JSON.stringify(recent));
  }}
}}

function closePlayer() {{
  document.getElementById("playerOverlay").style.display="none";
  document.getElementById("playerFrame").src="";
}}

function toggleFavorite() {{
  if(favorites.includes(currentItem.id)) {{
    favorites=favorites.filter(id=>id!==currentItem.id);
  }} else {{
    favorites.push(currentItem.id);
  }}
  localStorage.setItem("favorites",JSON.stringify(favorites));
  document.getElementById("favStar").style.color=favorites.includes(currentItem.id)?"#ff0":"#555";
}}

document.getElementById("searchBox").addEventListener("input",e=>{{
  let q=e.target.value.toLowerCase();
  showList(allEntries.filter(m=>m.title.toLowerCase().includes(q)));
}});

document.getElementById("typeSelect").addEventListener("change",e=>{{
  let val=e.target.value;
  if(val=="fav") {{
    showList(allEntries.filter(m=>favorites.includes(m.id)));
  }} else if(val=="recent") {{
    showList(allEntries.filter(m=>recent.includes(m.id)));
  }} else {{
    showList(allEntries.filter(m=>m.type==val));
  }}
}});

// titolo sul tap
const overlay = document.getElementById("playerOverlay");
const playerTitle = document.getElementById("playerTitle");

overlay.addEventListener('click', () => {{
  if(!currentItem) return;
  playerTitle.textContent = currentItem.title;
  playerTitle.style.display = 'block';
  setTimeout(() => {{
    playerTitle.style.display = 'none';
  }}, 2000);
}});

showList(allEntries.filter(m=>m.type=="movie"));
</script>
</body>
</html>
"""
    return html


def main():
    api_key = get_api_key()
    all_entries = []
    latest_html = ""
    for type_, url in SRC_URLS.items():
        data = fetch_list(url)
        ids = extract_ids(data)
        for tmdb_id in ids:
            item = tmdb_get(api_key, type_, tmdb_id)
            if not item:
                continue
            entry = {
                "id": str(tmdb_id),
                "title": item.get("title") or item.get("name") or "",
                "overview": item.get("overview",""),
                "poster": TMDB_IMAGE_BASE + item["poster_path"] if item.get("poster_path") else "",
                "vote": item.get("vote_average",0),
                "genres": [g["name"] for g in item.get("genres",[])],
                "type": type_,
                "year": (item.get("release_date") or item.get("first_air_date") or "")[:4],
                "duration": item.get("runtime") if type_=="movie" else None,
                "seasons": item.get("number_of_seasons") if type_=="tv" else None,
                "episodes": {s["season_number"]: s.get("episode_count",1) for s in item.get("seasons",[])} if type_=="tv" else None,
                "cast": [c["name"] for c in item.get("credits", {}).get("cast", [])],
                "link": VIX_LINK_MOVIE.format(tmdb_id) if type_=="movie" else None
            }
            all_entries.append(entry)

    latest = sorted(all_entries, key=lambda x: x["year"] or "0", reverse=True)[:20]
    for e in latest:
        latest_html += f"<img class='poster' src='{e['poster']}' alt='{e['title']}' onclick='openInfo({{id:\"{e['id']}\"}})'>"

    with open(OUTPUT_HTML,"w",encoding="utf-8") as f:
        f.write(build_html(all_entries, latest_html))

    print(f"File generato: {OUTPUT_HTML}")


if __name__=="__main__":
    main()
