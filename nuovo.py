#!/usr/bin/env python3
import os, sys, json, requests
from datetime import datetime

# ================= CONFIG =================
SRC_URLS = {
    "movie": "https://vixsrc.to/api/list/movie?lang=it",
    "tv": "https://vixsrc.to/api/list/tv?lang=it"
}

TMDB_BASE = "https://api.themoviedb.org/3/{type}/{id}"
TMDB_IMAGE = "https://image.tmdb.org/t/p/w780"
OUTPUT_HTML = "index2.html"
ARCHIVE_FILE = "entries.json"

HEADERS = {"User-Agent": "Mozilla/5.0"}
# =========================================


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
    return r.json() if r.status_code == 200 else None


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
body {{
  margin:0;
  background:#b91c1c;
  color:#fff;
  font-family:Arial;
}}

.topbar {{
  position:sticky;
  top:0;
  z-index:100;
  background:#000;
  padding:12px;
  display:flex;
  gap:10px;
}}

.topbar input, .topbar select {{
  padding:8px;
  font-size:16px;
}}

.topbar button {{
  padding:8px 14px;
  border-radius:10px;
  border:none;
  background:#dc2626;
  color:#fff;
  font-weight:bold;
  cursor:pointer;
}}

.row {{
  margin:20px 10px;
}}

.row h2 {{
  margin:10px;
  font-size:20px;
}}

.row-content {{
  display:flex;
  gap:12px;
  overflow-x:auto;
  padding:10px;
}}

.row-content::-webkit-scrollbar {{
  display:none;
}}

.poster {{
  min-width:140px;
  border-radius:12px;
  overflow:hidden;
  cursor:pointer;
  transition:transform .2s;
}}

.poster:focus {{
  outline:3px solid gold;
  transform:scale(1.1);
}}

.poster img {{
  width:100%;
  display:block;
}}

#infoCard {{
  position:fixed;
  inset:0;
  display:none;
  background:rgba(0,0,0,.85);
  z-index:1000;
  align-items:center;
  justify-content:center;
}}

#infoBox {{
  max-width:800px;
  width:90%;
  background:#111;
  padding:20px;
  border-radius:14px;
}}
button {{
  padding:10px 16px;
  border:none;
  border-radius:8px;
  font-size:16px;
}}
</style>
</head>

<body>

<div class="topbar">
  <input id="searchBox" placeholder="Cerca titolo...">
  <select id="typeSelect">
    <option value="movie">🎬 Film</option>
    <option value="tv">📺 Serie TV</option>
    <option value="favorites">★ Preferiti</option>
    <option value="recent">🕘 Recenti</option>
  </select>
  <button id="randomPick">🎲 Cosa guardiamo stasera?</button>
</div>

<div id="rows"></div>

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
const rows = document.getElementById("rows");
const search = document.getElementById("searchBox");
const typeSelect = document.getElementById("typeSelect");

let favorites = JSON.parse(localStorage.getItem("fav") || "[]");
let recent = JSON.parse(localStorage.getItem("recent") || "[]");
let currentPool = [];

function createRow(title, items) {{
  if (!items.length) return;

  const row = document.createElement("div");
  row.className = "row";
  row.innerHTML = `<h2>${{title}}</h2><div class="row-content"></div>`;
  const content = row.querySelector(".row-content");

  items.forEach(item => {{
    const p = document.createElement("div");
    p.className = "poster";
    p.tabIndex = 0;
    p.innerHTML = `<img src="${{item.poster}}">`;
    p.onclick = () => openInfo(item);
    content.appendChild(p);
  }});

  rows.appendChild(row);
}}

function buildRows() {{
  rows.innerHTML = "";
  const t = typeSelect.value;
  const q = search.value.toLowerCase();

  let list = DATA;
  if (t === "favorites") list = DATA.filter(x => favorites.includes(x.id));
  else if (t === "recent") list = DATA.filter(x => recent.includes(x.id));
  else list = DATA.filter(x => x.type === t);

  if (q) list = list.filter(x => x.title.toLowerCase().includes(q));
  currentPool = list;

  createRow("🔥 Ultime uscite", [...list].sort((a,b)=>b.added.localeCompare(a.added)).slice(0,20));

  const genres = ["Animazione","Commedia","Azione","Horror","Fantasy","Dramma"];
  genres.forEach(g => {{
    createRow(g, list.filter(x => x.genres && x.genres.includes(g)).slice(0,25));
  }});
}}

function openInfo(item) {{
  infoTitle.textContent = item.title;
  infoOverview.textContent = item.overview;
  playBtn.onclick = () => window.open(item.link,"_blank");
  favBtn.onclick = () => toggleFav(item.id);
  infoCard.style.display = "flex";

  recent = [item.id, ...recent.filter(x=>x!==item.id)].slice(0,20);
  localStorage.setItem("recent", JSON.stringify(recent));
}}

function closeInfo() {{
  infoCard.style.display = "none";
}}

function toggleFav(id) {{
  favorites = favorites.includes(id)
    ? favorites.filter(x=>x!==id)
    : favorites.concat(id);
  localStorage.setItem("fav", JSON.stringify(favorites));
}}

document.getElementById("randomPick").onclick = () => {{
  if (!currentPool.length) return;
  openInfo(currentPool[Math.floor(Math.random()*currentPool.length)]);
}};

search.oninput = buildRows;
typeSelect.onchange = buildRows;

buildRows();
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
                "genres": [g["name"] for g in info.get("genres",[])],
                "link": f"https://vixsrc.to/{t}/{tmdb_id}/",
                "added": datetime.utcnow().isoformat()
            })

    for e in new:
        old[e["id"]] = e

    entries = list(old.values())
    save_archive(entries)

    with open(OUTPUT_HTML,"w",encoding="utf-8") as f:
        f.write(build_html(entries))

    print(f"✅ index2.html generato con {len(entries)} titoli")

if __name__ == "__main__":
    main()
