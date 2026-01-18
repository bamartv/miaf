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
    items = data if isinstance(data, list) else data.get("results", [])
    for i in items:
        if isinstance(i, dict):
            for k in ("tmdb_id", "tmdbId", "id"):
                if k in i:
                    ids.append(str(i[k]))
                    break
    return ids


def tmdb_get(api_key, type_, tmdb_id):
    r = requests.get(
        TMDB_BASE.format(type=type_, id=tmdb_id),
        params={"api_key": api_key, "language": "it-IT"},
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

    html = """<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TV Media Center</title>

<style>
body {
  margin:0;
  background:#000;
  color:#fff;
  font-family:Arial,sans-serif;
}

.row {
  margin:20px 10px;
  position:relative;
}

.row-arrow {
  position:absolute;
  top:50%;
  transform:translateY(-50%);
  width:50px;
  height:120px;
  background:rgba(0,0,0,0.6);
  color:#fff;
  font-size:40px;
  display:flex;
  align-items:center;
  justify-content:center;
  cursor:pointer;
  opacity:0;
  transition:opacity .3s;
  z-index:10;
  user-select:none;
}

.row:hover .row-arrow {
  opacity:1;
}

.row-arrow.left { left:0; }
.row-arrow.right { right:0; }


.topbar {
  position:sticky;
  top:0;
  z-index:100;
  background:rgba(0,0,0,.9);
  padding:12px;
  display:flex;
  gap:10px;
  flex-wrap:wrap;
}

.topbar input, .topbar select {
  padding:8px;
  font-size:16px;
}

.topbar button {
  padding:8px 14px;
  border-radius:10px;
  border:none;
  background:#dc2626;
  color:#fff;
  font-weight:bold;
  cursor:pointer;
}

.row h2 { margin:10px; }

.row-content {
  display:flex;
  gap:12px;
  overflow-x:auto;
  padding:10px;
}
.row-content::-webkit-scrollbar { display:none; }

.poster {
  min-width:150px;
  border-radius:12px;
  overflow:hidden;
  cursor:pointer;
  transition:transform .2s;
}
.poster:hover { transform:scale(1.08); }
.poster img { width:100%; display:block; }

.grid {
  display:grid;
  grid-template-columns:repeat(auto-fill,minmax(150px,1fr));
  gap:14px;
  padding:20px;
}

/* INFOCARD */
#infoCard {
  position:fixed;
  inset:0;
  display:none;
  z-index:1000;
}

#infoBackdrop {
  position:absolute;
  inset:0;
  background-size: cover;
  background-position: center;
  transform: scale(1.05);
  filter: blur(6px) brightness(.72);
}


#infoOverlay {
  position:absolute;
  inset:0;
  background:linear-gradient(to right, rgba(0,0,0,.9) 30%, rgba(0,0,0,.4) 70%);
}

#infoBox {
  position:relative;
  max-width:900px;
  width:90%;
  margin:auto;
  padding:30px;
  z-index:2;
}

#closeBtn {
  position:absolute;
  top:20px;
  right:20px;
  font-size:26px;
  cursor:pointer;
}

.actions button {
  padding:10px 16px;
  border:none;
  border-radius:8px;
  font-size:16px;
  margin-right:10px;
  cursor:pointer;
}

.play { background:#dc2626; color:#fff; }
.fav { background:#2563eb; color:#fff; }
.close { background:#374151; color:#fff; }

select.episode {
  padding:8px;
  margin-right:8px;
}
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
  <select id="genreSelect" multiple size="1">
  </select>

  <button id="randomPick">🎲 Cosa guardiamo stasera?</button>
</div>

<div id="content"></div>

<div id="infoCard">
  <div id="infoBackdrop"></div>
  <div id="infoOverlay"></div>
  <div id="infoBox">
    <h1 id="infoTitle"></h1>
    <div id="infoMeta"></div>
    <p id="infoOverview"></p>

    <div id="tvControls" style="display:none">
      <select id="seasonSel" class="episode"></select>
      <select id="episodeSel" class="episode"></select>
    </div>

    <div class="actions">
      <button class="play" id="playBtn">▶ Guarda</button>
      <button class="fav" id="favBtn">★ Preferiti</button>
      <button class="close" id="closeBtnBottom">✕ Chiudi</button>
    </div>
  </div>
</div>

<script>
const DATA = __DATA__;

const content = document.getElementById("content");
const search = document.getElementById("searchBox");
const typeSelect = document.getElementById("typeSelect");
const genreSelect = document.getElementById("genreSelect");
const randomPickBtn = document.getElementById("randomPick");

let favorites = JSON.parse(localStorage.getItem("fav") || "[]");
let recent = JSON.parse(localStorage.getItem("recent") || "[]");
let currentItem = null;

/* generi */
[...new Set(DATA.flatMap(x=>x.genres||[]))].sort().forEach(g=>{
  const o=document.createElement("option");
  o.value=g; o.textContent=g;
  genreSelect.appendChild(o);
});

function poster(item) {
  return `
    <div class="poster" onclick="openInfoById('${item.id}')">
      <img loading="lazy" src="${item.poster}">
    </div>`;
}

function addRow(title, items) {
  if(!items.length) return;
  content.innerHTML += `
    <div class="row">
      <h2>${title}</h2>

      <div class="row-arrow left" onclick="scrollRow(this,-1)">‹</div>
      <div class="row-arrow right" onclick="scrollRow(this,1)">›</div>

      <div class="row-content">
        ${items.slice(0,25).map(poster).join("")}
      </div>
    </div>`;
}


function buildHome(list) {
  content.innerHTML="";
  addRow("🔥 Ultime uscite",[...list].sort((a,b)=>b.added.localeCompare(a.added)));
  [...new Set(list.flatMap(x=>x.genres||[]))].forEach(g=>{
    addRow(g,list.filter(x=>x.genres?.includes(g)));
  });
}

function scrollRow(el, dir){
  const row = el.parentElement.querySelector(".row-content");
  row.scrollLeft += dir * 400;
}


function buildGrid(list) {
  content.innerHTML=`<div class="grid">${list.map(poster).join("")}</div>`;
}

function rebuild() {
  const q=search.value.toLowerCase();
  const t=typeSelect.value;

  let list=DATA;
  if(t==="favorites") list=DATA.filter(x=>favorites.includes(x.id));
  else if(t==="recent") list=DATA.filter(x=>recent.includes(x.id));
  else list=DATA.filter(x=>x.type===t);

  if(q) list=list.filter(x=>x.title.toLowerCase().includes(q));
  const selectedGenres = [...genreSelect.selectedOptions].map(o=>o.value);

  if (selectedGenres.length) {
    list = list.filter(item =>
      selectedGenres.every(g => item.genres?.includes(g))
   );
}

  if(q||g||t!=="movie") buildGrid(list);
  else buildHome(list);
}

function randomPick() {
  const q = search.value.toLowerCase();
  const g = genreSelect.value;
  const t = typeSelect.value;

  let list = DATA;

  if (t === "favorites") list = DATA.filter(x => favorites.includes(x.id));
  else if (t === "recent") list = DATA.filter(x => recent.includes(x.id));
  else list = DATA.filter(x => x.type === t);

  if (q) list = list.filter(x => x.title.toLowerCase().includes(q));
  if (g) list = list.filter(x => x.genres?.includes(g));

  if (!list.length) {
    alert("Nessun titolo disponibile con questi filtri 😅");
    return;
  }

  const pick = list[Math.floor(Math.random() * list.length)];
  openInfoById(pick.id);
}


function openInfoById(id){
  const item = DATA.find(x=>x.id===id);
  if(!item) return;
  currentItem=item;

  document.getElementById("infoBackdrop").style.backgroundImage=`url(${item.poster})`;
  infoTitle.textContent=item.title;
  infoOverview.textContent=item.overview;
  infoMeta.textContent=item.genres.join(" • ");

  const tvControls=document.getElementById("tvControls");
  tvControls.style.display=item.type==="tv"?"block":"none";

  if(item.type==="tv"){
    seasonSel.innerHTML="";
    episodeSel.innerHTML="";
    for(let s=1;s<=5;s++){
      seasonSel.innerHTML+=`<option value="${s}">Stagione ${s}</option>`;
    }
    for(let e=1;e<=10;e++){
      episodeSel.innerHTML+=`<option value="${e}">Episodio ${e}</option>`;
    }
  }

  playBtn.onclick=()=>{
    if(item.type==="tv"){
      window.open(`https://vixsrc.to/tv/${item.id}/${seasonSel.value}/${episodeSel.value}`);
    } else {
      window.open(item.link);
    }
  };

  favBtn.onclick=()=>toggleFav(item.id);
  document.getElementById("infoCard").style.display="block";
}

function toggleFav(id){
  favorites=favorites.includes(id)?favorites.filter(x=>x!==id):[...favorites,id];
  localStorage.setItem("fav",JSON.stringify(favorites));
}

document.getElementById("closeBtnBottom").onclick = () => {
  document.getElementById("infoCard").style.display = "none";
};
document.addEventListener("keydown",e=>{ if(e.key==="Escape") infoCard.style.display="none"; });

search.oninput=rebuild;
genreSelect.oninput = rebuild;
typeSelect.onchange=rebuild;
randomPickBtn.onclick = randomPick;
rebuild();
</script>

</body>
</html>
"""

    return html.replace("__DATA__", entries_json)


# ================= MAIN =================

def main():
    api_key = get_api_key()
    old = {e["id"]: e for e in load_archive()}
    new = []

    for t, url in SRC_URLS.items():
        data = fetch_list(url)
        for tmdb_id in extract_ids(data):
            info = tmdb_get(api_key, t, tmdb_id)
            if not info:
                continue

            poster_path = info.get("poster_path")
            if not poster_path:
                continue  # salta titoli senza locandina

            new.append({
                "id": tmdb_id,
                "title": info.get("title") or info.get("name") or "",
                "poster": TMDB_IMAGE + poster_path,
                "overview": info.get("overview",""),
                "type": t,
                "genres": [g["name"] for g in info.get("genres", [])],
                "link": f"https://vixsrc.to/{t}/{tmdb_id}/",
                "added": datetime.utcnow().isoformat()
            })

    for e in new:
        old[e["id"]] = e

    entries = list(old.values())
    save_archive(entries)

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(build_html(entries))

    print(f"✅ {OUTPUT_HTML} generato con {len(entries)} titoli")


if __name__ == "__main__":
    main()
