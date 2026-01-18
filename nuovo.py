#!/usr/bin/env python3
import os, sys, json, requests
from datetime import datetime

# ================= CONFIG =================
SRC_URLS = {
    "movie": "https://vixsrc.to/api/list/movie?lang=it",
    "tv": "https://vixsrc.to/api/list/tv?lang=it"
}

TMDB_BASE = "https://api.themoviedb.org/3/{type}/{id}"
TMDB_POSTER = "https://image.tmdb.org/t/p/w500"  # LOCANDINE

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

.row { margin:20px 10px; }
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
  background-size:cover;
  background-position:center;
  filter:blur(12px) brightness(.35);
}

#infoOverlay {
  position:absolute;
  inset:0;
  background:rgba(0,0,0,.75);
}

#infoBox {
  position:relative;
  max-width:900px;
  width:90%;
  margin:auto;
  padding:30px;
  z-index:2;
}

#closeBig {
  margin-top:30px;
  padding:14px 40px;
  font-size:20px;
  background:#dc2626;
  border:none;
  color:#fff;
  border-radius:10px;
  cursor:pointer;
}
</style>
</head>

<body>

<div class="topbar">
  <input id="searchBox" placeholder="Cerca titolo...">
  <select id="typeSelect">
    <option value="movie">🎬 Film</option>
    <option value="tv">📺 Serie TV</option>
  </select>
  <button id="randomPick">🎲 Cosa guardiamo stasera?</button>
</div>

<div id="content"></div>

<div id="infoCard">
  <div id="infoBackdrop"></div>
  <div id="infoOverlay"></div>
  <div id="infoBox">
    <h1 id="infoTitle"></h1>
    <p id="infoOverview"></p>
    <button id="closeBig">CHIUDI</button>
  </div>
</div>

<script>
const DATA = __DATA__;
const content = document.getElementById("content");

function poster(item) {
  return `
    <div class="poster" onclick="openInfo('${item.id}')">
      <img loading="lazy" src="${item.poster}">
    </div>`;
}

function build() {
  content.innerHTML = `
    <div class="row">
      <h2>Ultimi aggiunti</h2>
      <div class="row-content">
        ${DATA.slice(0,30).map(poster).join("")}
      </div>
    </div>`;
}

function openInfo(id){
  const item = DATA.find(x=>x.id===id);
  if(!item) return;

  infoBackdrop.style.backgroundImage=`url(${item.poster})`;
  infoTitle.textContent=item.title;
  infoOverview.textContent=item.overview;
  infoCard.style.display="block";
}

closeBig.onclick=()=>infoCard.style.display="none";
build();
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
        for tmdb_id in extract_ids(fetch_list(url)):
            info = tmdb_get(api_key, t, tmdb_id)
            if not info:
                continue

            poster_path = info.get("poster_path")
            if not poster_path:
                continue  # NIENTE IMMAGINI A CASO

            new.append({
                "id": tmdb_id,
                "title": info.get("title") or info.get("name") or "",
                "poster": TMDB_POSTER + poster_path,
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

    print(f"✅ {OUTPUT_HTML} generato con {len(entries)} titoli")


if __name__ == "__main__":
    main()
