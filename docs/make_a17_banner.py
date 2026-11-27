"""Generate docs/a17-triage.svg: POST /tasks/triage as an animated pipeline (pure SVG + CSS, loops, no JS).

    python docs/make_a17_banner.py docs/a17-triage.svg
"""
import sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "docs/a17-triage.svg"
W, H, LOOP = 1280, 640, 14.0
END = (93.0, 98.0)
MONO = "Consolas,Menlo,monospace"
css = []


def appear(name: str, at: float) -> str:
    css.append(f"@keyframes {name}{{0%,{at:.1f}%{{opacity:0}}{at + 2:.1f}%,{END[0]}%{{opacity:1}}{END[1]}%,100%{{opacity:0}}}}"
               f".{name}{{animation:{name} {LOOP}s linear infinite}}")
    return name


def lit(name: str, at: float, color: str) -> str:
    css.append(f"@keyframes {name}{{0%,{at:.1f}%{{fill:#0B2B2D}}{at + 1.5:.1f}%,{END[0]}%{{fill:{color}}}{END[1]}%,100%{{fill:#0B2B2D}}}}"
               f".{name}{{animation:{name} {LOOP}s linear infinite}}")
    return name


# (step, what happens, failure path shown next to it, start %)
STEPS = [
    ("VALIDATE", "TriageIn: 1-1000 chars", "400 · no model call", 6),
    ("PROMPT", "prompts/triage-v1.md", "injection → stays data", 17),
    ("MODEL", "llama3.2:3b · 30 s timeout", "504 · 502 · retry 429/5xx", 28),
    ("PARSE", "find JSON · Pydantic schema", "off-list value → repair", 41),
    ("REPAIR", "once, with its own error", "422 + quarantine", 52),
    ("LOG", "tokens · ms · prompt version", "kill switch → fallback", 62),
]
rows = []
for i, (name, what, fail, at) in enumerate(STEPS):
    y = 132 + i * 62
    rows.append(
        f'<circle cx="724" cy="{y - 5}" r="8" class="{lit(f"l{i}", at, "#6FDCA4")}" stroke="#6FDCA4" stroke-width="2"/>'
        + (f'<line x1="724" y1="{y + 4}" x2="724" y2="{y + 49}" stroke="#2B4A44" stroke-width="2"/>' if i < len(STEPS) - 1 else "")
        + f'<text x="746" y="{y}" class="step">{name}</text>'
        + f'<text x="746" y="{y + 21}" class="what {appear(f"w{i}", at + 1)}">{what}</text>'
        + f'<text x="1196" y="{y + 8}" text-anchor="end" class="fail {appear(f"f{i}", at + 2)}">{fail}</text>'
    )

appear("note", 1)
appear("out", 72)
css.append("@media (prefers-reduced-motion: reduce){*{animation:none!important}"
           + "".join(f".w{i},.f{i}{{opacity:1}}.l{i}{{fill:#6FDCA4}}" for i in range(len(STEPS))) + ".note,.out{opacity:1}}")

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">
<title id="t">POST /tasks/triage: an LLM behind the Task API</title>
<desc id="d">Animated pipeline: a messy note is validated (400 before any model call), sent with a versioned prompt
file to llama3.2:3b with a 30 second timeout and retries only on 429 and 5xx, parsed and validated against a schema,
repaired once (422 and quarantine if it fails twice), and logged with tokens and duration. The result is clean JSON:
title, category, priority, confidence, reason, source.</desc>
<defs>
 <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="#FFFFFF" stroke-opacity=".035"/></pattern>
 <radialGradient id="g1" cx="85%" cy="15%" r="45%"><stop offset="0" stop-color="#2ECC80" stop-opacity=".18"/><stop offset="1" stop-color="#2ECC80" stop-opacity="0"/></radialGradient>
 <radialGradient id="g2" cx="10%" cy="95%" r="50%"><stop offset="0" stop-color="#1A7A4A" stop-opacity=".35"/><stop offset="1" stop-color="#1A7A4A" stop-opacity="0"/></radialGradient>
 <style>
  text{{font-family:"Segoe UI",-apple-system,Roboto,Helvetica,Arial,sans-serif}}
  .eyebrow{{font-size:17px;letter-spacing:3px;font-weight:600;fill:#6FDCA4}}
  .h1{{font-family:{MONO};font-size:46px;font-weight:700;fill:#fff}}
  .sub{{font-size:23px;fill:#B9D3C8}}
  .mono{{font-family:{MONO}}}
  .step{{font-family:{MONO};font-size:16px;font-weight:700;letter-spacing:1px;fill:#6FDCA4}}
  .what{{font-family:{MONO};font-size:14px;fill:#E8F3EE}}
  .fail{{font-family:{MONO};font-size:13px;font-weight:700;fill:#FF8A8E}}
  .k{{fill:#8FB8FF}} .v{{fill:#F2C66D}} .p{{fill:#E8F3EE}}
  {"".join(css)}
 </style>
</defs>
<rect width="{W}" height="{H}" fill="#051F21"/><rect width="{W}" height="{H}" fill="url(#g2)"/>
<rect width="{W}" height="{H}" fill="url(#g1)"/><rect width="{W}" height="{H}" fill="url(#grid)"/>

<text x="72" y="98" class="eyebrow">FLYRANK AI INTERNSHIP · A17 · WEEK 7</text>
<text x="70" y="166" class="h1">POST /tasks/triage</text>
<text x="72" y="214" class="sub">One endpoint, one judgement, an answer your code</text>
<text x="72" y="246" class="sub">can trust: schema, timeout, retries, kill switch.</text>

<g class="note">
 <rect x="72" y="282" width="560" height="62" rx="12" fill="#0B2B2D" stroke="#8FB8FF" stroke-opacity=".6"/>
 <text x="92" y="308" class="mono" font-size="13" fill="#6E8F85">{{"text":</text>
 <text x="92" y="330" class="mono" font-size="16" fill="#E8F3EE">"ring mum re sunday lunch + pick up her meds!!"}}</text>
</g>
<g class="out">
 <rect x="72" y="362" width="560" height="196" rx="12" fill="#020E0F" fill-opacity=".85" stroke="#6FDCA4" stroke-opacity=".5"/>
 <text x="92" y="390" class="mono" font-size="14" fill="#6FDCA4">200 OK</text>
 <text x="92" y="418" class="mono" font-size="15"><tspan class="k">"title"</tspan><tspan class="p">: </tspan><tspan class="v">"Call mum about Sunday lunch and…"</tspan></text>
 <text x="92" y="444" class="mono" font-size="15"><tspan class="k">"category"</tspan><tspan class="p">: </tspan><tspan class="v">"health"</tspan><tspan class="p">,  </tspan><tspan class="k">"priority"</tspan><tspan class="p">: </tspan><tspan class="v">"normal"</tspan></text>
 <text x="92" y="470" class="mono" font-size="15"><tspan class="k">"confidence"</tspan><tspan class="p">: </tspan><tspan class="v">0.8</tspan><tspan class="p">,  </tspan><tspan class="k">"source"</tspan><tspan class="p">: </tspan><tspan class="v">"model"</tspan></text>
 <text x="92" y="502" class="mono" font-size="13" fill="#6E8F85">eval: 18/25 category · 14/14 easy · 0.55 s median</text>
 <text x="92" y="526" class="mono" font-size="13" fill="#6E8F85">741 tokens in · 59 out · $0 on local Ollama</text>
</g>
<text x="72" y="598" font-size="20" font-weight="600" fill="#fff">Azizul Abedin Azmi</text>
<text x="268" y="598" font-size="15" fill="#6E8F85">· FastAPI · Pydantic · Ollama</text>

<rect x="688" y="64" width="528" height="512" rx="18" fill="#020E0F" fill-opacity=".78" stroke="#6FDCA4" stroke-opacity=".22"/>
<circle cx="712" cy="88" r="6" fill="#2B4A44"/><circle cx="732" cy="88" r="6" fill="#2B4A44"/><circle cx="752" cy="88" r="6" fill="#2B4A44"/>
<text x="1196" y="93" text-anchor="end" class="mono" font-size="13" fill="#6E8F85">llm/triage.py · failure path →</text>
{"".join(rows)}
</svg>
'''
open(OUT, "w", encoding="utf-8", newline="\n").write(svg)
print("wrote", OUT, len(svg), "bytes")
