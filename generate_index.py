#!/usr/bin/env python3
"""
generate_index.py
"""

import os
import requests
import json

API_KEY = os.getenv("TMDB_API_KEY", "demo")  # metti la tua API key TMDB
OUTPUT_HTML = "index.html"

TMDB_BASE = "https://api.themoviedb.org/3"


def fetch_tmdb(url, params=None):
    if params is None:
        params = {}
    params["api_key"] = API_KEY
    params["language"] = "it-IT"
    r = requests.get(url, params=params)
    r.raise_for_status()
    return r.json()


def build_html(entries, latest_entries):
    return f"""<!DOCTYPE html>
<html lang=\"it\">
<head>
  <meta charset=\"UTF-8\">
  <title>Catalogo</title>
  <style>
    body {{ background:#111; color:#eee; margin:0; font-family:sans-serif; }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(150px,1fr)); gap:10px; padding:10px; }}
    .card {{ background:#222; border-radius:8px; overflow:hidden; cursor:pointer; transition:transform .2s; }}
    .card:hover {{ transform:scale(1.05); }}
    .card img {{ width:100%; display:block; }}
    .infoCard {{ display:none; position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,.9); color:#fff; padding:20px; overflow:auto; }}
    #overlay {{ display:none; position:fixed; top:0; left:0; right:0; bottom:0; background:#000; z-index:100; align-items:center; justify-content:center; }}
    #overlay iframe {{ width:100%; height:100%; border:0; }}
  </style>
</head>
<body>
  <div class=\"grid\" id=\"grid\">
    {''.join([f'<div class="card" onclick="openInfo(allData[{i}])"><img src="{e['poster']}" alt="{e['title']}"><div>{e['title']}</div></div>' for i,e in enumerate(entries)])}
  </div>

  <div class=\"infoCard\" id=\"infoCard\">
    <h2 id=\"infoTitle\"></h2>
    <p id=\"infoGenres\"></p>
    <p id=\"infoVote\"></p>
    <p id=\"infoOverview\"></p>
    <p id=\"infoYear\"></p>
    <p id=\"infoDuration\"></p>
    <p id=\"infoCast\"></p>
    <select id=\"seasonSelect\"></select>
    <select id=\"episodeSelect\"></select>
    <button id=\"playBtn\">Guarda</button>
  </div>

  <div id=\"overlay\"><iframe id=\"iframe\" allowfullscreen></iframe></div>

<script>
let allData = {json.dumps(entries)};
let currentItem = null;

const infoCard = document.getElementById('infoCard');
const overlay = document.getElementById('overlay');
const iframe = document.getElementById('iframe');
const infoTitle = document.getElementById('infoTitle');
const infoGenres = document.getElementById('infoGenres');
const infoVote = document.getElementById('infoVote');
const infoOverview = document.getElementById('infoOverview');
const infoYear = document.getElementById('infoYear');
const infoDuration = document.getElementById('infoDuration');
const infoCast = document.getElementById('infoCast');
const seasonSelect = document.getElementById('seasonSelect');
const episodeSelect = document.getElementById('episodeSelect');
const playBtn = document.getElementById('playBtn');

function openInfo(item, push=true) {{
    currentItem = item;
    infoCard.style.display='block';
    infoTitle.textContent = item.title;
    infoGenres.textContent = "Generi: " + item.genres.join(", ");
    infoVote.textContent = "★ " + item.vote;
    infoOverview.textContent = item.overview || "";
    infoYear.textContent = item.year ? "Anno: " + item.year : "";
    infoDuration.textContent = item.duration ? "Durata: " + item.duration + " min" : "";
    infoCast.textContent = item.cast && item.cast.length ? "Cast: " + item.cast.slice(0,5).join(", ") : "";

    seasonSelect.style.display = 'none';
    episodeSelect.style.display = 'none';
    if(item.type==='tv') {{
        seasonSelect.style.display = 'inline';
        episodeSelect.style.display = 'inline';
        seasonSelect.innerHTML = "";
        for(let s=1;s<=item.seasons;s++) {{
            let o = document.createElement('option');
            o.value = s;
            o.textContent = "Stagione " + s;
            seasonSelect.appendChild(o);
        }}
        seasonSelect.onchange = updateEpisodes;
        updateEpisodes();
    }}

    playBtn.onclick = () => openPlayer(item);

    if(push) {{
        history.replaceState({{page:"info", itemId:item.id}}, "", "#info-"+item.id);
    }}

    function updateEpisodes() {{
        let season = parseInt(seasonSelect.value);
        let epCount = item.episodes[season] || 1;
        episodeSelect.innerHTML = "";
        for(let e=1;e<=epCount;e++) {{
            let o = document.createElement('option');
            o.value = e;
            o.textContent = "Episodio " + e;
            episodeSelect.appendChild(o);
        }}
    }}
}}

function openPlayer(item, push=true) {{
    infoCard.style.display='none';
    overlay.style.display='flex';
    let link;
    if(item.type==='tv') {{
        let season = parseInt(seasonSelect.value) || 1;
        let episode = parseInt(episodeSelect.value) || 1;
        link = `https://vixsrc.to/tv/${{item.id}}/${{season}}/${{episode}}?lang=it&sottotitoli=off&autoplay=1`;
    }} else {{
        link = `https://vixsrc.to/movie/${{item.id}}/?lang=it&sottotitoli=off&autoplay=1`;
    }}
    iframe.src = link;
    if (overlay.requestFullscreen) overlay.requestFullscreen();

    if(push) {{
        history.pushState({{page:"player", itemId:item.id}}, "", "#player-"+item.id);
    }}
}}

function closePlayer(push=true) {{
    overlay.style.display='none';
    iframe.src='';
    if (document.fullscreenElement) document.exitFullscreen();
    if(currentItem) infoCard.style.display='block';
    if(push) {{
        history.replaceState({{page:"info", itemId:currentItem.id}}, "", "#info-"+currentItem.id);
    }}
}}

/* Gestione popstate */
window.addEventListener("popstate", function(e) {{
    const state = e.state;

    if(!state || state.page==="grid" || state.page==="home") {{
        overlay.style.display='none';
        iframe.src='';
        infoCard.style.display='none';
        history.replaceState({{page:"grid"}}, "", "#grid");
        return;
    }}

    const itemId = state.itemId;
    const item = allData.find(x => String(x.id) === String(itemId));
    if(!item) {{
        overlay.style.display='none';
        iframe.src='';
        infoCard.style.display='none';
        history.replaceState({{page:"grid"}}, "", "#grid");
        return;
    }}

    if(state.page === "player") {{
        openPlayer(item, false);
    }} else if(state.page === "info") {{
        if(overlay.style.display==='flex') closePlayer(false);
        openInfo(item, false);
    }} else {{
        overlay.style.display='none';
        iframe.src='';
        infoCard.style.display='none';
        history.replaceState({{page:"grid"}}, "", "#grid");
    }}
}});

/* stato iniziale */
history.replaceState({{page:"grid"}}, "", "#grid");
</script>
</body>
</html>
"""


def main():
    entries = []
    latest_entries = ""
    for type_, endpoint in [("movie", "movie/popular"), ("tv", "tv/popular")]:
        data = fetch_tmdb(f"{TMDB_BASE}/{endpoint}")
        for idx, item in enumerate(data["results"][:20]):
            tmdb_id = item["id"]
            info = fetch_tmdb(f"{TMDB_BASE}/{type_}/{tmdb_id}", params={"append_to_response": "credits"})

            title = info.get("title") or info.get("name") or "Senza titolo"
            poster = "https://image.tmdb.org/t/p/w300" + info.get("poster_path") if info.get("poster_path") else ""
            genres = [g["name"] for g in info.get("genres", [])]
            vote = info.get("vote_average", 0)
            overview = info.get("overview", "")
            link = "#"
            seasons = info.get("number_of_seasons", 1) if type_=="tv" else None
            episodes = {str(s["season_number"]): s.get("episode_count", 1) for s in info.get("seasons", [])} if type_=="tv" else {}
            year = (info.get("release_date") or info.get("first_air_date") or "")[:4]
            runtime = info.get("runtime") if type_=="movie" else None
            cast = [c["name"] for c in info.get("credits", {}).get("cast", [])[:10]]

            entry = {
                "id": str(tmdb_id),
                "title": title,
                "poster": poster,
                "genres": genres,
                "vote": round(vote,1),
                "overview": overview,
                "link": link,
                "type": type_,
                "seasons": seasons,
                "episodes": episodes,
                "year": year,
                "duration": runtime,
                "cast": cast
            }
            entries.append(entry)

            if idx < 20:
                latest_entries += f"<img class='poster' src='{poster}' alt='{title}'>"

    html = build_html(entries, latest_entries)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)


if __name__ == "__main__":
    main()
