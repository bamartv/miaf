import requests
import json
import time

TMDB_API_KEY = "tuo_tmdb_api_key"  # mantieni il secret su GitHub
SRC_URLS = {
    "movie": "https://vixsrc.to/api/list/movie?lang=it",
    "tv": "https://vixsrc.to/api/list/tv?lang=it"
}

def fetch_list(url, page=1):
    r = requests.get(url, params={"page": page}, timeout=20)
    r.raise_for_status()
    return r.json()

def extract_ids(data):
    ids = []
    for item in data.get("data", []):
        tmdb_id = item.get("tmdb_id")
        if tmdb_id:
            ids.append(tmdb_id)
    return ids

def fetch_tmdb_info(tmdb_id, type_):
    url = f"https://api.themoviedb.org/3/{type_}/{tmdb_id}?api_key={TMDB_API_KEY}&language=it-IT"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except:
        return None

def main():
    entries = []
    latest_entries = []

    for type_, base_url in SRC_URLS.items():
        print(f"[VIX] Scarico lista {type_}")
        first = fetch_list(base_url, page=1)
        ids = extract_ids(first)
        last_page = first.get("last_page", 1)
        print(f"[VIX] {type_}: {last_page} pagine totali")

        for page in range(2, last_page + 1):
            try:
                data = fetch_list(base_url, page=page)
                ids.extend(extract_ids(data))
                print(f"[VIX] {type_} pagina {page} scaricata, tot ID: {len(ids)}")
                time.sleep(0.2)
            except Exception as e:
                print(f"[VIX] Errore pagina {page}: {e}")
                break

        ids = list(dict.fromkeys(ids))  # rimuove duplicati
        print(f"[VIX] {type_}: {len(ids)} ID totali")

        for idx, tmdb_id in enumerate(ids):
            info = fetch_tmdb_info(tmdb_id, type_)
            if not info:
                continue
            poster = f"https://image.tmdb.org/t/p/w780{info.get('poster_path')}" if info.get('poster_path') else ""
            genres = [g['name'] for g in info.get('genres', [])]
            vote = info.get("vote_average", 0)
            overview = info.get("overview", "")
            year = info.get("release_date", info.get("first_air_date", ""))[:4]
            duration = info.get("runtime", 0) if type_=="movie" else 0
            cast = [c['name'] for c in info.get("credits", {}).get("cast", [])] if info.get("credits") else []
            directors = [d['name'] for d in info.get("credits", {}).get("crew", []) if d['job']=="Director"] if info.get("credits") else []

            entry = {
                "id": str(tmdb_id),
                "title": info.get("title", info.get("name", "")),
                "poster": poster,
                "genres": genres,
                "vote": vote,
                "overview": overview,
                "year": year,
                "duration": duration,
                "cast": cast,
                "directors": directors,
                "type": type_,
                "link": f"https://vixsrc.to/{type_}/{tmdb_id}/?"
            }
            entries.append(entry)
            if idx < 20:  # ultimi aggiunti per "Aggiunti di recente"
                latest_entries.append(entry)
            time.sleep(0.2)  # evita blocco TMDB

    # Genera HTML finale usando f-string come nel tuo script
    html_content = f"""<!doctype html>
<html lang='it'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Movies & Series</title>
<style>
/* TODO: qui inserire il CSS completo originale con doppie {{ }} dove servono */
</style>
</head>
<body>
<h1>Aggiunti di recente</h1>
<div id='latest'>
{"".join([f"<img class='poster' src='{e['poster']}' alt='{e['title']}' title='{e['title']}'>" for e in latest_entries])}
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
<div id='moviesGrid' class='grid'>
{"".join([f"<div class='card'><img class='poster' src='{e['poster']}' alt='{e['title']}' title='{e['title']}'></div>" for e in entries])}
</div>
<div id="bottomControls">
 <button id='loadMore'>Carica altri</button>
 <button id='randomPick'>🎲 Cosa guardiamo stasera?</button>
 </div>

<!-- Player e infoCard rimangono uguali al tuo script originale -->

</body>
</html>
"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("[OK] index.html aggiornato")

if __name__ == "__main__":
    main()
