"""Generate docs/banner.svg: the BE-01 banner, animated (pure SVG + CSS, loops, no JS).

The right side plays the A3 persistence proof: `docker compose up` brings the stack up, a task is created,
`docker compose down` removes every container, `up` brings them back, and the row is still there because it lives
on the volume. Under prefers-reduced-motion the finished state is shown as a still image.

    python docs/make_banner.py docs/banner.svg
"""
import sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "docs/banner.svg"
W, H, LOOP = 1280, 640, 16.0
FADE = (93.0, 98.0)
MONO = 'Consolas,"SF Mono",Menlo,monospace'

css = []


def appear(name: str, at: float, until: float = FADE[0]) -> str:
    """Keyframes: hidden until `at`%, visible until `until`%, then fade out with the loop."""
    end = FADE[1] if until == FADE[0] else until + 1.5
    css.append(f"@keyframes {name}{{0%,{at:.1f}%{{opacity:0}}{at + 1.8:.1f}%,{until:.1f}%{{opacity:1}}{end:.1f}%,100%{{opacity:0}}}}"
               f".{name}{{animation:{name} {LOOP}s linear infinite}}")
    return name


# ---------------------------------------------------------------- terminal card (top right)
# (text pieces as (class, text), start %)
LINES = [
    ([("prompt", "$ "), ("cmd", "docker compose up")], 2),
    ([("ok", "✓ "), ("p", "db     "), ("ok", "postgres:17 (healthy)")], 7),
    ([("ok", "✓ "), ("p", "redis  "), ("ok", "redis:7 (healthy)")], 10),
    ([("ok", "✓ "), ("p", "api    "), ("mut", "→ localhost:8000")], 13),
    ([("m", "POST "), ("p", "/tasks "), ("mut", '"Survive the restart" '), ("ok", "→ 201")], 21),
    ([("prompt", "$ "), ("cmd", "docker compose down"), ("mut", "   # containers gone")], 33),
    ([("prompt", "$ "), ("cmd", "docker compose up")], 47),
    ([("m", "GET "), ("p", "/tasks/5 "), ("ok", "→ 200  still there ✓")], 57),
]
term = []
for i, (parts, at) in enumerate(LINES):
    y = 150 + i * 31
    tspans = "".join(f'<tspan class="{c}">{t}</tspan>' for c, t in parts)
    term.append(f'<text x="730" y="{y}" class="mono {appear(f"t{i}", at)}">{tspans}</text>')
# blinking cursor that follows the newest line
cur_kf = []
for i, (_, at) in enumerate(LINES):
    cur_kf.append(f"{at:.1f}%{{transform:translateY({i * 31}px)}}")
css.append("@keyframes cur{0%{transform:translateY(0)}" + "".join(cur_kf) + "100%{transform:translateY(" + str((len(LINES) - 1) * 31) + "px)}}"
           ".curpos{animation:cur " + str(LOOP) + "s steps(1,end) infinite}"
           "@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}.blink{animation:blink 1s steps(1,end) infinite}")

# ---------------------------------------------------------------- database card (bottom right)
DOWN_AT, UP_AT = 34.0, 49.0
css.append(f"@keyframes dim{{0%,{DOWN_AT:.1f}%{{opacity:1}}{DOWN_AT + 2:.1f}%,{UP_AT:.1f}%{{opacity:.28}}{UP_AT + 2:.1f}%,100%{{opacity:1}}}}"
           f".dim{{animation:dim {LOOP}s linear infinite}}")
appear("stup1", 0, DOWN_AT)            # status: up (before down)
appear("stdown", DOWN_AT, UP_AT)       # status: removed
appear("stup2", UP_AT)                 # status: up again
appear("row5", 22)                     # the new row appears after the POST
css.append(f"@keyframes glow{{0%,22%{{opacity:0}}24%{{opacity:.55}}30%{{opacity:0}}{UP_AT + 8:.1f}%{{opacity:0}}{UP_AT + 10:.1f}%{{opacity:.55}}{UP_AT + 16:.1f}%,100%{{opacity:0}}}}"
           f".glow{{animation:glow {LOOP}s linear infinite}}")

rows = [("2", "Build a CRUD API", "f", ""), ("3", "Push to GitHub", "f", ""), ("4", "Buy milk", "f", ""),
        ("5", "Survive the restart", "f", "row5")]
table = []
for i, (rid, title, done, cls) in enumerate(rows):
    y = 497 + i * 26
    table.append(f'<g class="{cls}"><text x="730" y="{y}" class="mono v">{rid}</text>'
                 f'<text x="772" y="{y}" class="mono p">{title}</text>'
                 f'<text x="1000" y="{y}" class="mono v">{done}</text></g>')

# reduced motion: the finished state, still
final = "".join(f".t{i}{{opacity:1}}" for i in range(len(LINES)))
css.append("@media (prefers-reduced-motion: reduce){*{animation:none!important}" + final +
           ".row5,.stup2{opacity:1}.stup1,.stdown,.glow{opacity:0}.dim{opacity:1}.curpos{transform:translateY(" +
           str((len(LINES) - 1) * 31) + "px)}}")

# ---------------------------------------------------------------- left side (same design as the old PNG banner)
chips, x = "", 72
for text, bg, outline in [("GET", "#2F80ED", 0), ("POST", "#1FA971", 0), ("PUT", "#E59A1A", 0), ("DELETE", "#E5484D", 0),
                          ("Postgres", "#6FDCA4", 1), ("Docker", "#6FDCA4", 1)]:
    w = 22 + 11 * len(text)
    if outline:
        chips += (f'<rect x="{x + 1}" y="404" width="{w - 2}" height="36" rx="8" fill="none" stroke="{bg}" stroke-width="2"/>'
                  f'<text x="{x + w / 2}" y="428" text-anchor="middle" class="chip" fill="{bg}">{text}</text>')
    else:
        chips += (f'<rect x="{x}" y="404" width="{w}" height="36" rx="8" fill="{bg}"/>'
                  f'<text x="{x + w / 2}" y="428" text-anchor="middle" class="chip" fill="#fff">{text}</text>')
    x += w + 10

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">
<title id="t">Task API: a hand-built CRUD REST API in Python and FastAPI, running on PostgreSQL in Docker</title>
<desc id="d">Animated: docker compose up starts db, redis and api; a task "Survive the restart" is created (201);
docker compose down removes the containers; docker compose up brings them back and GET /tasks/5 returns 200 because the
row lives on the Docker volume. By Azizul Abedin Azmi, FlyRank verified.</desc>
<defs>
 <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="#FFFFFF" stroke-opacity=".035"/></pattern>
 <radialGradient id="g1" cx="85%" cy="15%" r="45%"><stop offset="0" stop-color="#2ECC80" stop-opacity=".18"/><stop offset="1" stop-color="#2ECC80" stop-opacity="0"/></radialGradient>
 <radialGradient id="g2" cx="10%" cy="95%" r="50%"><stop offset="0" stop-color="#1A7A4A" stop-opacity=".35"/><stop offset="1" stop-color="#1A7A4A" stop-opacity="0"/></radialGradient>
 <style>
  text{{font-family:"Segoe UI",-apple-system,Roboto,Helvetica,Arial,sans-serif}}
  .mono{{font-family:{MONO};font-size:17px}}
  .eyebrow{{font-size:17px;letter-spacing:3px;font-weight:600;fill:#6FDCA4}}
  .h1{{font-size:92px;font-weight:800;fill:#fff;letter-spacing:-2px}}
  .sub{{font-size:26px;fill:#B9D3C8}}
  .chip{{font-family:{MONO};font-size:18px;font-weight:700}}
  .name{{font-size:22px;font-weight:600;fill:#fff}}
  .prompt{{fill:#6FDCA4;font-weight:700}} .cmd{{fill:#fff}} .ok{{fill:#6FDCA4}} .p{{fill:#E8F3EE}}
  .m{{fill:#6FDCA4;font-weight:700}} .mut{{fill:#6E8F85}} .v{{fill:#F2C66D}} .th{{fill:#6E8F85;font-weight:600}}
  .pill{{font-family:{MONO};font-size:13px;font-weight:700}}
  {"".join(css)}
 </style>
</defs>
<rect width="{W}" height="{H}" fill="#051F21"/><rect width="{W}" height="{H}" fill="url(#g2)"/>
<rect width="{W}" height="{H}" fill="url(#g1)"/><rect width="{W}" height="{H}" fill="url(#grid)"/>

<text x="72" y="98" class="eyebrow">FLYRANK AI INTERNSHIP · BE-01 · BE-02 · A3</text>
<text x="66" y="200" class="h1">Task API</text>
<text x="72" y="262" class="sub">A hand-built CRUD REST API in Python &amp;</text>
<text x="72" y="298" class="sub">FastAPI, now on PostgreSQL in Docker.</text>
<text x="72" y="334" class="sub">One command starts the stack, and the</text>
<text x="72" y="370" class="sub">data survives a restart.</text>
{chips}
<text x="72" y="566" class="name">Azizul Abedin Azmi</text>
<circle cx="292" cy="559" r="3" fill="#4C7A6B"/>
<rect x="308" y="539" width="352" height="38" rx="19" fill="#fff"/>
<text x="332" y="564" font-size="17" font-weight="700" fill="#1A7A4A">✓</text>
<text x="352" y="564" font-size="16" font-weight="700" fill="#051F21">FlyRank verified</text>
<line x1="490" y1="549" x2="490" y2="567" stroke="#E4EAED"/>
<text x="500" y="563" fill="#6E7F84" style="font-family:Consolas,Menlo,monospace;font-size:13px">FR-D1-A84A9-AB526</text>

<!-- terminal -->
<rect x="706" y="64" width="504" height="324" rx="16" fill="#020E0F" fill-opacity=".78" stroke="#6FDCA4" stroke-opacity=".22"/>
<circle cx="732" cy="90" r="6" fill="#2B4A44"/><circle cx="752" cy="90" r="6" fill="#2B4A44"/><circle cx="772" cy="90" r="6" fill="#2B4A44"/>
<text x="1188" y="95" text-anchor="end" class="mono mut" font-size="13">task-api</text>
{"".join(term)}
<g class="curpos"><rect class="blink" x="1180" y="136" width="9" height="18" fill="#6FDCA4"/></g>

<!-- database -->
<rect x="706" y="404" width="504" height="210" rx="16" fill="#020E0F" fill-opacity=".78" stroke="#6FDCA4" stroke-opacity=".22"/>
<text x="730" y="440" class="mono"><tspan class="prompt">tasks=#</tspan><tspan class="cmd"> SELECT * FROM tasks;</tspan></text>
<g class="stup1"><rect x="1118" y="424" width="70" height="22" rx="11" fill="#1A7A4A"/><text x="1153" y="440" text-anchor="middle" class="pill" fill="#E8F3EE">db: up</text></g>
<g class="stdown"><rect x="1062" y="424" width="126" height="22" rx="11" fill="#3A2A2C"/><text x="1125" y="440" text-anchor="middle" class="pill" fill="#FF8A8E">db: removed</text></g>
<g class="stup2"><rect x="1078" y="424" width="110" height="22" rx="11" fill="#1A7A4A"/><text x="1133" y="440" text-anchor="middle" class="pill" fill="#E8F3EE">db: up again</text></g>
<g class="dim">
 <text x="730" y="468" class="mono th" font-size="15">id</text><text x="772" y="468" class="mono th" font-size="15">title</text><text x="1000" y="468" class="mono th" font-size="15">done</text>
 <line x1="730" y1="476" x2="1060" y2="476" stroke="#6FDCA4" stroke-opacity=".22"/>
</g>
<rect class="glow" x="722" y="555" width="350" height="26" rx="6" fill="#6FDCA4" opacity="0"/>
{"".join(table)}
<text x="730" y="600" class="mono mut" font-size="14">postgres:17 · rows live on the volume "taskdata"</text>
</svg>
'''
open(OUT, "w", encoding="utf-8", newline="\n").write(svg)
print("wrote", OUT, len(svg), "bytes")
