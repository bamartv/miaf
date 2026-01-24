#!/usr/bin/env python3
import os, sys, json, requests
from datetime import datetime

# ================= CONFIG =================

FORCE_PEGI_REFRESH = True
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


def tmdb_get(api_key, type_, tmdb_id):
    try:
        r = requests.get(
            TMDB_BASE.format(type=type_, id=tmdb_id),
            params={"api_key": api_key, "language": "it-IT"},
            timeout=30
        )
        return r.json() if r.status_code == 200 else None
    except requests.exceptions.RequestException as e:
        print(f"⚠️ TMDB timeout / errore su ID {tmdb_id}: {e}")
        return None


def tmdb_get_pegi(api_key, type_, tmdb_id):
    try:
        if type_ == "tv":
            url = f"https://api.themoviedb.org/3/tv/{tmdb_id}/content_ratings"
            r = requests.get(url, params={"api_key": api_key}, timeout=15)
            if r.status_code == 200:
                for c in r.json().get("results", []):
                    if c.get("iso_3166_1") == "IT":
                        return c.get("rating") or None

        else:  # movie
            url = f"https://api.themoviedb.org/3/movie/{tmdb_id}/release_dates"
            r = requests.get(url, params={"api_key": api_key}, timeout=15)
            if r.status_code == 200:
                for c in r.json().get("results", []):
                    if c.get("iso_3166_1") == "IT":
                        for rel in c.get("release_dates", []):
                            if rel.get("certification"):
                                return rel.get("certification") or None
    except:
        pass

    return None



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
  font-size:14px;
  cursor:pointer;
  padding:4px 0;
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
.poster:focus {
  outline: 3px solid #dc2626;
  transform: scale(1.12);
  z-index: 10;
}
.poster img { width:100%; display:block; }

.pegi {
  position:absolute;
  bottom:8px;
  left:8px;
  background:#dc2626;
  color:#fff;
  font-size:13px;
  font-weight:bold;
  padding:4px 8px;
  border-radius:6px;
  box-shadow:0 2px 6px rgba(0,0,0,.6);
}
.poster {
  position:relative;
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

#genreSelect {
  padding:8px;
  font-size:16px;
  background:#111;
  color:#fff;
  border-radius:8px;
}

#playerOverlay {
  position: fixed;
  inset: 0;
  background: #000;
  z-index: 2000;
}

#playerFrame {
  width: 100%;
  height: 100%;
  border: none;
}

#playerClose {
  position: absolute;
  top: 16px;
  right: 20px;
  z-index: 2100;
  font-size: 26px;
  color: white;
  cursor: pointer;
  background: rgba(0,0,0,.6);
  padding: 6px 12px;
  border-radius: 10px;
}



.actions button {
  padding:10px 16px;
  border:none;
  border-radius:8px;
  font-size:16px;
  margin-right:10px;
  cursor:pointer;
}

.vote-circle {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  font-size: 14px;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  background: #444;
  box-shadow: 0 2px 6px rgba(0,0,0,.6);
}

.vote-good { background: #16a34a; }   /* verde */
.vote-mid  { background: #f59e0b; }   /* giallo */
.vote-bad  { background: #dc2626; }   /* rosso */


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
  <option value="" disabled>🎭 Generi</option>
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


<div id="playerOverlay" style="display:none">
  <iframe
    id="playerFrame"
    allowfullscreen
    allow="autoplay; fullscreen"
  ></iframe>
</div>
    

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
const GENRES = [...new Set(DATA.flatMap(x=>x.genres||[]))].sort();

GENRES.forEach(g => {
  const opt = document.createElement("option");
  opt.value = g;
  opt.textContent = g;
  genreSelect.appendChild(opt);
});




function poster(item) {
  let voteBadge = "";

  if (item.vote && item.vote > 0) {
    let cls = "vote-mid";
    if (item.vote >= 7.5) cls = "vote-good";
    else if (item.vote < 5.5) cls = "vote-bad";

    voteBadge = `
      <div class="vote-circle ${cls}">
        ${item.vote}
      </div>`;
  }

  return `
    <div class="poster" tabindex="0" onclick="openInfoById('${item.id}')">
      <img loading="lazy" src="${item.poster}">
      ${item.pegi ? `<div class="pegi">${item.pegi}</div>` : ""}
      ${voteBadge}
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


document.addEventListener("click", e => {
  if (!e.target.closest(".genre-dropdown")) {
    genreMenu.style.display = "none";
  }
});

function getSelectedGenres() {
  return [...genreSelect.selectedOptions].map(o => o.value);
}



function buildGrid(list) {
  content.innerHTML=`<div class="grid">${list.map(poster).join("")}</div>`;
}

function browseGenre(genre) {
  // reset ricerca
  search.value = "";

  // reset dropdown generi
  genreMenu.querySelectorAll("input").forEach(c => {
    c.checked = (c.value === genre);
  });

  // forza vista griglia
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

  // HOME a righe SOLO senza filtri e SOLO film
  if (!q && !selectedGenres.length && t === "movie") {
    buildHome(list);
  } else {
    buildGrid(list);
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

  playBtn.onclick = () => {
  let url;

  if (currentItem.type === "tv") {
    url = `https://vixsrc.to/tv/${currentItem.id}/${seasonSel.value}/${episodeSel.value}`;
  } else {
    url = currentItem.link;
  }

  const overlay = document.getElementById("playerOverlay");
  const frame = document.getElementById("playerFrame");

  frame.src = url;
  overlay.style.display = "block";

  // 🔥 QUESTO È IL PUNTO CHIAVE
  history.pushState({ player: true }, "");
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

search.oninput = rebuild;
typeSelect.onchange = rebuild;
randomPickBtn.onclick = randomPick;
genreSelect.onchange = rebuild;
rebuild();

/* 🔥 BACK ANDROID → TORNA ALLA INFOCARD */
window.addEventListener("popstate", () => {
  const overlay = document.getElementById("playerOverlay");
  const frame = document.getElementById("playerFrame");

  if (overlay.style.display === "block") {
    frame.src = "";
    overlay.style.display = "none";

    // blocca ritorno alla home
    history.pushState({}, "");
  }
});
document.addEventListener("keydown", e => {
  if (e.key === "Enter" && document.activeElement.classList.contains("poster")) {
    document.activeElement.click();
  }
});

document.addEventListener("keydown", e => {
  const active = document.activeElement;
  if (!active.classList.contains("poster")) return;

  const row = active.closest(".row");
  if (!row) return;

  const posters = [...row.querySelectorAll(".poster")];
  const index = posters.indexOf(active);
  if (index === -1) return;

  // ⬇️ riga sotto
  if (e.key === "ArrowDown") {
    e.preventDefault();
    const nextRow = row.nextElementSibling;
    if (!nextRow || !nextRow.classList.contains("row")) return;

    const nextPosters = nextRow.querySelectorAll(".poster");
    if (nextPosters[index]) {
      nextPosters[index].focus();
    } else if (nextPosters.length) {
      nextPosters[nextPosters.length - 1].focus();
    }
  }

  // ⬆️ riga sopra
  if (e.key === "ArrowUp") {
    e.preventDefault();
    const prevRow = row.previousElementSibling;
    if (!prevRow || !prevRow.classList.contains("row")) return;

    const prevPosters = prevRow.querySelectorAll(".poster");
    if (prevPosters[index]) {
      prevPosters[index].focus();
    } else if (prevPosters.length) {
      prevPosters[prevPosters.length - 1].focus();
    }
  }
});



</script>

</body>
</html>
"""

    return html.replace("__DATA__", entries_json)


# ================= MAIN =================

def main():
    api_key = get_api_key()

    # 🔥 carica archivio
    old = {}
    for e in load_archive():
        if "added" not in e:
            e["added"] = datetime.utcnow().isoformat()
        old[e["id"]] = e

    new = []

    for t, url in SRC_URLS.items():
        print(f"➡️ Scarico lista {t}")
        data = fetch_list(url)

        for tmdb_id in extract_ids(data):

            # ✅ già presente
            if tmdb_id in old and not FORCE_PEGI_REFRESH:
                continue


            info = tmdb_get(api_key, t, tmdb_id)
            if not info:
                continue

            poster_path = info.get("poster_path")
            if not poster_path:
                continue

            existing = old.get(tmdb_id, {})

            pegi = tmdb_get_pegi(api_key, t, tmdb_id)

            new.append({
                "id": tmdb_id,
                "title": info.get("title") or info.get("name") or "",
                "poster": TMDB_IMAGE + poster_path,
                "overview": info.get("overview", ""),
                "type": t,
                "genres": [g["name"] for g in info.get("genres", [])],
                "pegi": pegi,
                "vote": round(info.get("vote_average", 0), 1),
                "link": f"https://vixsrc.to/{t}/{tmdb_id}/",
                "added": existing.get("added", datetime.utcnow().isoformat())
            })

    # 🔁 merge
    for e in new:
        old[e["id"]] = e

    entries = list(old.values())
    save_archive(entries)

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(build_html(entries))

    print(f"✅ {OUTPUT_HTML} generato con {len(entries)} titoli")




if __name__ == "__main__":
    main()
