import json

# ======= DATI DI INPUT =======
# Struttura attesa per ogni film:
# {
#   "title": "...",
#   "description": "...",
#   "genre": "Action",
#   "poster": "URL POSTER UFFICIALE",
#   "duration": "2h 14m",
#   "pegi": "16+"
# }

with open("movies.json", "r", encoding="utf-8") as f:
    movies = json.load(f)

# Raggruppa per genere
genres = {}
for m in movies:
    genres.setdefault(m["genre"], []).append(m)

# ======= HTML =======
html = f"""
<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<title>Streaming</title>

<style>
body {{
    margin: 0;
    background: #111;
    color: white;
    font-family: Arial, sans-serif;
}}

.genre {{
    position: relative;
    margin: 30px 20px;
}}

.genre h2 {{
    margin-left: 10px;
}}

.row {{
    display: flex;
    overflow-x: auto;
    scroll-behavior: smooth;
    gap: 18px;
    padding: 10px 40px;
}}

.row::-webkit-scrollbar {{
    display: none;
}}

.poster {{
    min-width: 200px;
    height: 300px;
    background-size: cover;
    background-position: center;
    border-radius: 10px;
    cursor: pointer;
    transition: transform 0.3s;
}}

.poster:hover {{
    transform: scale(1.1);
}}

.arrow {{
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    width: 50px;
    height: 100px;
    background: rgba(0,0,0,0.6);
    color: white;
    font-size: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    opacity: 0;
    transition: opacity 0.3s;
    z-index: 10;
}}

.genre:hover .arrow {{
    opacity: 1;
}}

.arrow.left {{
    left: 0;
}}

.arrow.right {{
    right: 0;
}}

#info {{
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.95);
    display: none;
    z-index: 100;
}}

#infoContent {{
    display: flex;
    gap: 30px;
    max-width: 1000px;
    margin: 80px auto;
}}

#infoPoster {{
    width: 300px;
    height: 450px;
    background-size: cover;
    background-position: center;
    border-radius: 12px;
}}

#infoText {{
    max-width: 600px;
}}

#closeBtn {{
    margin-top: 30px;
    padding: 15px 40px;
    font-size: 18px;
    background: #e50914;
    border: none;
    color: white;
    cursor: pointer;
    border-radius: 8px;
}}
</style>
</head>

<body>
"""

for genre, items in genres.items():
    html += f"""
    <div class="genre">
        <h2>{genre}</h2>
        <div class="arrow left" onclick="scrollRow(this, -1)">‹</div>
        <div class="arrow right" onclick="scrollRow(this, 1)">›</div>
        <div class="row">
    """

    for m in items:
        html += f"""
        <div class="poster"
             style="background-image:url('{m["poster"]}')"
             onclick='openInfo({json.dumps(m)})'>
        </div>
        """

    html += """
        </div>
    </div>
    """

html += """
<div id="info">
    <div id="infoContent">
        <div id="infoPoster"></div>
        <div id="infoText">
            <h1 id="infoTitle"></h1>
            <p id="infoDesc"></p>
            <p><b>Durata:</b> <span id="infoDur"></span></p>
            <p><b>PEGI:</b> <span id="infoPegi"></span></p>
            <button id="closeBtn" onclick="closeInfo()">CHIUDI</button>
        </div>
    </div>
</div>

<script>
function scrollRow(el, dir) {{
    const row = el.parentElement.querySelector('.row');
    row.scrollLeft += dir * 500;
}}

function openInfo(m) {{
    document.getElementById("info").style.display = "block";
    document.getElementById("infoPoster").style.backgroundImage = `url(${m.poster})`;
    document.getElementById("infoTitle").innerText = m.title;
    document.getElementById("infoDesc").innerText = m.description;
    document.getElementById("infoDur").innerText = m.duration;
    document.getElementById("infoPegi").innerText = m.pegi;
}}

function closeInfo() {{
    document.getElementById("info").style.display = "none";
}}
</script>

</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("index.html generato correttamente")
