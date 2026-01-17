#!/usr/bin/env python3
import os, sys, json, requests, time
from datetime import datetime

# ================= CONFIG =================
SRC_URLS = {
    "movie": "https://vixsrc.to/api/list/movie?lang=it",
    "tv": "https://vixsrc.to/api/list/tv?lang=it"
}

TMDB_BASE = "https://api.themoviedb.org/3/{type}/{id}"
TMDB_IMAGE = "https://image.tmdb.org/t/p/w780"
OUTPUT_HTML = "index2.html"   # <-- cambia in index2.html se vuoi
ARCHIVE_FILE = "entries.json"

HEADERS = {"User-Agent": "Mozilla/5.0"}
# ==========================================

def get_api_key():
    key = os.getenv("TMDB_API_KEY")
    if not key:
        print("❌ TMDB_API_KEY mancante")
        sys.exit(1)
    return key

def fetch_list(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.json()

def extract_ids(data):
    ids = []
    for i in data if isinstance(data, list) else data.get("results", []):
        if isinstance(i, dict):
            for k in ("tmdb_id", "tmdbId", "id"):
                if k in i:
                    ids.append(str(i[k]))
                    break
    return ids

def tmdb_get(api_key, type_, tmdb_id):
    r = requests.get(
        TMDB_BASE.format(type=type_, id=tmdb_id),
        params={"api_key": api_key, "language": "it-IT", "append_to_response": "credits"},
        timeout=15
    )
    if r.status_code != 200:
        return None
    return r.json()

def load_archive():
    if os.path.exists(ARCHIVE_FILE):
        with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_archive(data):
    with open(ARCHIVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ================= HTML =================

def build_html(entries):
    entries_json = json.dumps(entries, ensure_ascii=False)

    return f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TV Media Center</title>

<style>
body{{margin:0;background:#141414;color:#fff;font-family:Arial}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:14px;padding:20px}}
.card{{outline:none;cursor:pointer;border-radius:12px;overflow:hidden;transition:transform .2s}}
.card:focus{{transform:scale(1.15);box-shadow:0 0 0 4px #e50914}}
.card img{{width:100%}}

.topbar{{position:sticky;top:0;z-index:100;background:#000;padding:12px;display:flex;gap:10px}}
.topbar input,.topbar select{{padding:8px;font-size:16px}}

#infoCard{{position:fixed;inset:0;display:none;background:rgba(0,0,0,.85);z-index:1000;
display:flex;align-items:center;justify-content:center}}

#infoBox{{max-width:800px;width:90%;background:#111;padding:20px;border-radius:14px}}
button{{padding:10px 16px;border:none;border-radius:8px;font-size:16px}}
button:focus{{outline:3px solid gold}}
</style>
</head>

<body>

<div class="topbar">
  <input id="search" placeholder="Cerca">
  <select id="type">
    <option value="movie">Film</option>
    <option value="tv">Serie TV</option>
    <option value="favorites">★ Preferiti</option>
    <option value="recent">👁 Recenti</option>
  </select>
</div>

<div id="grid" class="grid"></div>

<div id="infoCard">
  <div id="infoBox">
    <h2 id="infoTitle"></h2>
    <p id="infoOverview"></p>
    <button id="playBtn">▶ Guarda</button>
    <button id="favBtn">★ Preferiti</button>
    <button onclick="closeInfo()">Chiudi</button>
  </div>
</div>

<script>
const DATA = {entries_json};
let shown = 0;
const STEP = 40;
let current = [];
let favorites = JSON.parse(localStorage.getItem("fav")||"[]");
let recent = JSON.parse(localStorage.getItem("recent")||"[]");

const grid = document.getElementById("grid");

function applyFilter() {{
  const t = type.value;
  const q = search.value.toLowerCase();

  let list = DATA;
  if(t==="favorites") list = DATA.filter(x=>favorites.includes(x.id));
  else if(t==="recent") list = DATA.filter(x=>recent.includes(x.id));
  else list = DATA.filter(x=>x.type===t);

  if(q) list = list.filter(x=>x.title.toLowerCase().includes(q));

  current = list.sort((a,b)=>b.added.localeCompare(a.added));
  shown = 0;
  grid.innerHTML="";
  loadMore();
}}

function loadMore() {{
  current.slice(shown, shown+STEP).forEach(item=>{{
    const c=document.createElement("div");
    c.className="card";
    c.tabIndex=0;
    c.innerHTML=`<img src="${{item.poster}}">`;
    c.onclick=()=>openInfo(item);
    grid.appendChild(c);
  }});
  shown+=STEP;
}}

window.onscroll=()=> {{
  if(window.innerHeight+scrollY>document.body.offsetHeight-600) loadMore();
}}

function openInfo(item) {{
  infoTitle.textContent=item.title;
  infoOverview.textContent=item.overview;
  favBtn.onclick=()=>toggleFav(item.id);
  playBtn.onclick=()=>window.open(item.link,"_blank");
  infoCard.style.display="flex";

  recent.unshift(item.id);
  recent=[...new Set(recent)].slice(0,20);
  localStorage.setItem("recent",JSON.stringify(recent));
}}

function closeInfo() {{
  infoCard.style.display="none";
}}

function toggleFav(id) {{
  favorites = favorites.includes(id)
    ? favorites.filter(x=>x!==id)
    : favorites.concat(id);
  localStorage.setItem("fav",JSON.stringify(favorites));
}}

search.oninput=applyFilter;
type.onchange=applyFilter;

applyFilter();
</script>

</body>
</html>
"""

# ================= MAIN =================

def main():
    api_key = get_api_key()
    old = {e["id"]: e for e in load_archive()}
    new = []

    for t, url in SRC_URLS.items():
        ids = extract_ids(fetch_list(url))
        for tmdb_id in ids:
            info = tmdb_get(api_key, t, tmdb_id)
            if not info:
                continue

            new.append({
                "id": tmdb_id,
                "title": info.get("title") or info.get("name"),
                "poster": TMDB_IMAGE + info["poster_path"] if info.get("poster_path") else "",
                "overview": info.get("overview",""),
                "type": t,
                "link": f"https://vixsrc.to/{t}/{tmdb_id}/",
                "added": datetime.utcnow().isoformat()
            })

    for e in new:
        old[e["id"]] = e

    entries = list(old.values())
    save_archive(entries)

    with open(OUTPUT_HTML,"w",encoding="utf-8") as f:
        f.write(build_html(entries))

    print(f"✅ index.html generato con {len(entries)} titoli")

if __name__=="__main__":
    main()
