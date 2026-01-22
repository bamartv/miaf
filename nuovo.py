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


def tmdb_get_rating(api_key, type_, tmdb_id):
    if type_ == "movie":
        url = f"https://api.themoviedb.org/3/movie/{tmdb_id}/release_dates"
        r = requests.get(url, params={"api_key": api_key}, timeout=15)
        if r.status_code != 200:
            return None

        for c in r.json().get("results", []):
            if c.get("iso_3166_1") in ("IT", "US"):
                for rel in c.get("release_dates", []):
                    cert = rel.get("certification")
                    if cert:
                        return cert

    else:  # TV
        url = f"https://api.themoviedb.org/3/tv/{tmdb_id}/content_ratings"
        r = requests.get(url, params={"api_key": api_key}, timeout=15)
        if r.status_code != 200:
            return None

        for c in r.json().get("results", []):
            if c.get("iso_3166_1") in ("IT", "US"):
                return c.get("rating")

    return None


def map_to_pegi(cert):
    if not cert:
        return None

    cert = cert.upper()

    if cert in ("G", "TV-G"):
        return "3"
    if cert in ("PG"):
        return "7"
    if cert in ("PG-13", "TV-14"):
        return "12"
    if cert in ("R", "TV-MA", "18"):
        return "18"

    return cert


    
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

<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@500;600;700&display=swap" rel="stylesheet">


<style>
body {
  margin:0;
  background:#000;
  color:#fff;
  font-family:Arial,sans-serif;
}

.row-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 10px;
}

.browse-all {
  background: none;
  border: none;
  color: #bbb;
  font-size: 14px;
  letter-spacing: 1px;
  cursor: pointer;
  opacity: 0;
  transition: opacity .25s, color .25s;
}

/* appare quando la riga è attiva (hover o focus TV) */
.row:hover .browse-all,
.row:focus-within .browse-all {
  opacity: 1;
}

/* focus telecomando */
.browse-all:focus {
  outline: 2px solid #dc2626;
  border-radius: 6px;
  color: #fff;
}


.row {
  margin:20px 10px;
  position:relative;
}

.row h2 {
  font-family: "Oswald", "Arial Narrow", Arial, sans-serif;
}

.row:first-of-type h2 {
  font-size: 26px;
  color: #fff;
  text-shadow:
    0 3px 10px rgba(0,0,0,0.9),
    0 0 18px rgba(220,38,38,0.6);
}


.topbar {
  position: relative;   /* ← FONDAMENTALE */
  z-index: 10;
  background: rgba(0,0,0,.95);
  padding: 12px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}


/* 🔥 quando ci vai col telecomando */
.topbar:focus-within {
  z-index: 999;
}

.topbar input:focus,
.topbar select:focus,
.topbar button:focus {
  outline: 3px solid #dc2626;
  box-shadow: 0 0 10px rgba(220,38,38,.8);
  border-radius: 8px;
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

.genre-dropdown {
  position: relative;
}

#genreBtn {
  padding:8px 14px;
  border-radius:10px;
  border:none;
  background:#1f2933;
  color:#fff;
  cursor:pointer;
}

#content {
  margin-top: 10px;
}


.genre-menu {
  position:absolute;
  top:110%;
  left:0;
  background:#111;
  border-radius:10px;
  padding:10px;
  max-height:260px;
  overflow:auto;
  display:none;
  z-index:200;
  box-shadow:0 10px 30px rgba(0,0,0,.6);
}

.genre-menu label {
  display:flex;
  align-items:center;
  gap:8px;
  font-size:15px;
  padding:6px 8px;
  border-radius:6px;
}

.genre-menu label:focus {
  outline: 3px solid #dc2626;
  background: rgba(220,38,38,.25);
}


.genre-menu label {
  display:flex;
  align-items:center;
  gap:8px;
  font-size:14px;
  cursor:pointer;
  padding:4px 0;
}

.genre-menu input {
  pointer-events: auto;
}

.genre-menu label:focus-within {
  outline: 2px solid #dc2626;
  border-radius: 6px;
}



.row h2 {
  margin: 10px 10px 6px;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 1.2px;
  text-transform: uppercase;
  color: #f5f5f5;
  text-shadow:
    0 2px 6px rgba(0,0,0,0.8),
    0 0 12px rgba(220,38,38,0.35);
  position: relative;
}

/* linea cinematografica sotto il titolo */
.row h2::after {
  content: "";
  display: block;
  width: 60px;
  height: 3px;
  margin-top: 6px;
  background: linear-gradient(
    90deg,
    #dc2626,
    rgba(220,38,38,0.2)
  );
  border-radius: 3px;
}


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

.poster:focus {
  outline: 4px solid #dc2626;
  transform: scale(1.08);
  z-index: 10;
}


.pegi {
  position:absolute;
  top:6px;
  left:6px;
  background:#dc2626;
  color:#fff;
  font-weight:bold;
  font-size:13px;
  padding:4px 6px;
  border-radius:6px;
  z-index:5;
}


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
  <div class="genre-dropdown">
   <button id="genreBtn" tabindex="0">🎭 Generi ▼</button>
   <div id="genreMenu" class="genre-menu"></div>
  </div>


  <button id="randomPick">🎲 Cosa guardiamo stasera?</button>
</div>

<div id="playerOverlay" style="
  position:fixed;
  inset:0;
  background:#000;
  display:none;
  z-index:2000;
">
  <iframe id="playerFrame"
    allow="autoplay; fullscreen"
    allowfullscreen
    style="width:100%;height:100%;border:none">
  </iframe>
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
const playerOverlay = document.getElementById("playerOverlay");
const playerFrame = document.getElementById("playerFrame");

function openPlayer(item, push=true){
  let url;

  if(item.type==="tv"){
    url = `https://vixsrc.to/tv/${item.id}/${seasonSel.value}/${episodeSel.value}?autoplay=1`;
  } else {
    url = `https://vixsrc.to/movie/${item.id}?autoplay=1`;
  }

  playerFrame.src = url;
  playerOverlay.style.display = "block";

  if (playerOverlay.requestFullscreen) {
    playerOverlay.requestFullscreen();
  }

  if(push){
    history.pushState({page:"player", id:item.id}, "", "#player-"+item.id);
  }
}

function closePlayer(push=true){
  playerFrame.src="";
  playerOverlay.style.display="none";

  if (document.fullscreenElement) {
    document.exitFullscreen();
  }

  if(push && currentItem){
    history.pushState({page:"info", id:currentItem.id}, "", "#info-"+currentItem.id);
  }
}

const content = document.getElementById("content");
const search = document.getElementById("searchBox");
const typeSelect = document.getElementById("typeSelect");
const genreBtn = document.getElementById("genreBtn");
const genreMenu = document.getElementById("genreMenu");
const randomPickBtn = document.getElementById("randomPick");

let favorites = JSON.parse(localStorage.getItem("fav") || "[]");
let recent = JSON.parse(localStorage.getItem("recent") || "[]");
let currentItem = null;

/* generi */
const GENRES = [...new Set(DATA.flatMap(x=>x.genres||[]))].sort();

GENRES.forEach(g => {
  const label = document.createElement("label");
  label.tabIndex = 0;
  label.innerHTML = `<input type="checkbox" value="${g}" tabindex="-1"> ${g}`;


  const checkbox = label.querySelector("input");

  

  // 🔥 QUANDO CLICCHI UN GENERE → RICOSTRUISCE LA GRIGLIA
  checkbox.addEventListener("change", rebuild);

  label.addEventListener("keydown", e => {
  if (e.key === "Enter") {
    checkbox.checked = !checkbox.checked;
    rebuild();
  }
});


  

  genreMenu.appendChild(label);
});



function poster(item) {
  return `
    <div class="poster"
         tabindex="0"
         onclick="openInfoById('${item.id}')"
         onkeydown="if(event.key==='Enter'){openInfoById('${item.id}')}"
         style="position:relative">

      ${item.pegi ? `<div class="pegi">PEGI ${item.pegi}</div>` : ""}
      <img loading="lazy" src="${item.poster}">
    </div>`;
}

function addRow(title, items) {
  if(!items.length) return;
  content.innerHTML += `
    <div class="row">
      <div class="row-title">
  <h2>${title}</h2>
  <button class="browse-all"
    onclick="browseGenre('${title}')"
    tabindex="0">
    Sfoglia tutti →
  </button>
</div>


      <div class="row-content">
        ${items.slice(0,25).map(poster).join("")}
      </div>
    </div>`;
}


function buildHome(list) {
  content.innerHTML="";
  addRow(
  "🎬 Ultime uscite",
  [...list]
    .filter(x => x.added)
    .sort((a,b)=>b.added.localeCompare(a.added))
);

  [...new Set(list.flatMap(x=>x.genres||[]))].forEach(g=>{
    addRow(g,list.filter(x=>x.genres?.includes(g)));
  });
}

genreBtn.onclick = () => {
  const open = genreMenu.style.display === "block";
  genreMenu.style.display = open ? "none" : "block";

  if (!open) {
    // 🔥 focus automatico sul primo genere
    const first = genreMenu.querySelector("input");
    if (first) first.focus();
  }
};

document.addEventListener("keydown", e => {
  if (e.key === "Backspace" || e.key === "Escape") {
    if (genreMenu.style.display === "block") {
      genreMenu.style.display = "none";
      genreBtn.focus();
    }
  }
});


document.addEventListener("focusin", e => {
  const el = e.target;
  if (el.classList.contains("poster")) {
    el.scrollIntoView({
      behavior: "smooth",
      block: "nearest",
      inline: "center"
    });
  }
});


document.addEventListener("click", e => {
  if (!e.target.closest(".genre-dropdown")) {
    genreMenu.style.display = "none";
  }
});

function getSelectedGenres() {
  return [...genreMenu.querySelectorAll("input:checked")]
    .map(x => x.value);
}


function buildGrid(list) {
  content.innerHTML=`<div class="grid">${list.map(poster).join("")}</div>`;
}

function browseGenre(genre) {
  search.value = "";

  // 🔥 CASO SPECIALE: ULTIME USCITE
  if (genre.includes("Ultime")) {
    buildGrid(
      DATA
        .filter(x => x.type === typeSelect.value && x.added)
        .sort((a, b) => b.added.localeCompare(a.added))
    );
    return;
  }

  // reset dropdown generi
  genreMenu.querySelectorAll("input").forEach(c => {
    c.checked = (c.value === genre);
  });

  // vista griglia per generi normali
  buildGrid(
    DATA.filter(x =>
      x.type === typeSelect.value &&
      x.genres?.includes(genre)
    )
  );
}



function rebuild() {
  const q = search.value.toLowerCase();
  const t = typeSelect.value;
  const selectedGenres = getSelectedGenres();

  let list = DATA;

  if (t === "favorites") list = DATA.filter(x => favorites.includes(x.id));
  else if (t === "recent") list = DATA.filter(x => recent.includes(x.id));
  else list = DATA.filter(x => x.type === t);

  if (q) list = list.filter(x => x.title.toLowerCase().includes(q));

  if (selectedGenres.length) {
    list = list.filter(item =>
      selectedGenres.every(g => item.genres?.includes(g))
    );
  }

  // 🔥 LOGICA CORRETTA
  if (q || selectedGenres.length || t !== "movie") {
    buildGrid(list);
  } else {
    buildHome(list);
  }
}


function randomPick() {
  const q = search.value.toLowerCase();
  const selectedGenres = getSelectedGenres();
  const t = typeSelect.value;

  let list = DATA;

  if (t === "favorites") list = DATA.filter(x => favorites.includes(x.id));
  else if (t === "recent") list = DATA.filter(x => recent.includes(x.id));
  else list = DATA.filter(x => x.type === t);

  if (q) list = list.filter(x => x.title.toLowerCase().includes(q));
  if (selectedGenres.length) {
  list = list.filter(item =>
    selectedGenres.every(g => item.genres?.includes(g))
  );
}

  if (!list.length) {
    alert("Nessun titolo disponibile con questi filtri 😅");
    return;
  }

  const pick = list[Math.floor(Math.random() * list.length)];
  openInfoById(pick.id);
}

function closeInfoCard() {
  const card = document.getElementById("infoCard");
  if (card && card.style.display === "block") {
    card.style.display = "none";
    currentItem = null;
    return true; // dice ad Android: "ho gestito io il back"
  }
  return false;
}



function openInfoById(id){
  const item = DATA.find(x=>x.id===id);
  if(!item) return;
  currentItem=item;

  document.getElementById("infoBackdrop").style.backgroundImage=`url(${item.poster})`;
  infoTitle.textContent=item.title;
  infoOverview.textContent=item.overview;
  let meta = item.genres.join(" • ");

  if (item.pegi) {
  meta += ` • <span class="pegi">VM${item.pegi}</span>`;
}

infoMeta.innerHTML = meta;


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

  playBtn.onclick = () => openPlayer(item);


  favBtn.onclick=()=>toggleFav(item.id);
  document.getElementById("infoCard").style.display="block";
  history.pushState(
  { page: "info", id: item.id },
  "",
  "#info-" + item.id
);

}

function toggleFav(id){
  favorites=favorites.includes(id)?favorites.filter(x=>x!==id):[...favorites,id];
  localStorage.setItem("fav",JSON.stringify(favorites));
}

document.getElementById("closeBtnBottom").onclick = closeInfoCard;
document.addEventListener("keydown", e => {
  if (e.key === "Escape") closeInfoCard();
});


search.oninput=rebuild;
typeSelect.onchange=rebuild;
randomPickBtn.onclick = randomPick;
rebuild();
setTimeout(() => {
  const firstPoster = document.querySelector(".poster");
  if (firstPoster) firstPoster.focus();
}, 300);
window.addEventListener("popstate", e => {
  const s = e.state;

  // se stavo guardando un video → torna a infocard
  if (s && s.page === "player") {
    openPlayer(currentItem, false);
    return;
  }

  // se stavo in infocard → chiudi player e mostra info
  if (s && s.page === "info") {
    closePlayer(false);
    openInfoById(s.id);
    return;
  }

  // fallback → home
  closePlayer(false);
  closeInfoCard();
});

</script>

</body>
</html>
"""

    return html.replace("__DATA__", entries_json)


# ================= MAIN =================

def main():
    api_key = get_api_key()

    # 🔥 CARICA ARCHIVIO E SISTEMA added SE MANCA
    old = {}
    for e in load_archive():
        if "added" not in e:
            e["added"] = datetime.utcnow().isoformat()
        old[e["id"]] = e

    new = []

    for t, url in SRC_URLS.items():
        data = fetch_list(url)
        for tmdb_id in extract_ids(data):
            info = tmdb_get(api_key, t, tmdb_id)
            raw_rating = tmdb_get_rating(api_key, t, tmdb_id)
            pegi = map_to_pegi(raw_rating)

            if not info:
                continue

            poster_path = info.get("poster_path")
            if not poster_path:
                continue  # salta titoli senza locandina

            existing = old.get(tmdb_id)

            new.append({
                "id": tmdb_id,
                "title": info.get("title") or info.get("name") or "",
                "poster": TMDB_IMAGE + poster_path,
                "overview": info.get("overview", ""),
                "pegi": pegi,
                "type": t,
                "genres": [g["name"] for g in info.get("genres", [])],
                "link": f"https://vixsrc.to/{t}/{tmdb_id}/",
                # 🔥 mantiene la data se già esiste
                "added": existing["added"] if existing else datetime.utcnow().isoformat()
            })

    # 🔁 MERGE DEFINITIVO
    for e in new:
        old[e["id"]] = e

    entries = list(old.values())
    save_archive(entries)

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(build_html(entries))

    print(f"✅ {OUTPUT_HTML} generato con {len(entries)} titoli")



if __name__ == "__main__":
    main()
