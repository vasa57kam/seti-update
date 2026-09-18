import os, json, shutil, subprocess, time, sys
D = "/opt/agent-panel"
rep = []
mp = os.path.join(D, "main.py")
pp = os.path.join(D, "page.html")
shutil.copy2(mp, "/tmp/main.py.preupd")
s = open(mp, errors="ignore").read()
orig = s

# 1) прямой вопрос модели: sync-эндпоинт в тредпуле (панель не виснет)
if '/api/ask' not in s and '@app.get("/api/tasks")' in s:
    if 'from pydantic import BaseModel' not in s:
        s = s.replace('import uvicorn', 'import uvicorn\nfrom pydantic import BaseModel', 1)
    s = s.replace('@app.get("/api/tasks")', '''class AskModel(BaseModel):
    text: str = ""
    model: str = ""

@app.post("/api/ask")
def api_ask(d: AskModel):
    q = (d.text or "").strip()
    if not q:
        return JSONResponse({"error": "пустой вопрос"}, 400)
    model = d.model or ACTIVE_MODEL
    out = ollama_gen(model, q, num_predict=2000, timeout=1800)
    return {"ok": True, "text": out.strip()}

@app.get("/api/tasks")''', 1)
    rep.append("main: /api/ask — прямой вопрос модели (в тредпуле)")

# 2) сторож: 15 мин на загрузку весов до первого токена, потом 5 мин
if 'lim = 900 if not t.get' not in s:
    lines = s.split('\n')
    for i, ln in enumerate(lines):
        if 'time.time() - beat > 300' in ln:
            ind = ln[:len(ln) - len(ln.lstrip())]
            lines[i] = ln.replace('> 300', '> lim')
            lines.insert(i, ind + 'lim = 900 if not t.get("first_chunk") else 300')
            rep.append("сторож: 15 мин на загрузку весов")
            break
    else:
        rep.append("ВНИМАНИЕ: строка сторожа не найдена")
    s = '\n'.join(lines)

# 3) сохранение источника обновления на сервере
if '@app.post("/api/ghset")' not in s and '@app.get("/api/tasks")' in s:
    s = s.replace('@app.get("/api/tasks")',
        '@app.post("/api/ghset")\nasync def api_ghset(req: Request):\n    d = await req.json()\n    SETTINGS["gh_url"] = d.get("url", "") or SETTINGS.get("gh_url", "")\n    SETTINGS["gh_token"] = d.get("token", "") or SETTINGS.get("gh_token", "")\n    save_settings()\n    return {"ok": True}\n\n@app.get("/api/tasks")', 1)
    rep.append("main: /api/ghset — сохранить источник")
a3 = '    if not url.startswith("https://"): return JSONResponse({"error": "need https:// raw-URL"}, 400)'
if 'SETTINGS["gh_url"]' not in s and a3 in s:
    s = s.replace(a3, a3 + '\n    SETTINGS["gh_url"] = url; SETTINGS["gh_token"] = token; save_settings()', 1)
    rep.append("main: адрес запоминается при протягивании")

if s != orig:
    open(mp, "w").write(s)

# 4) страница: раздел вопроса + автоподстановка адреса + кнопка сохранить
pg = open(pp, errors="ignore").read()
o = pg
if 'id="askq"' not in pg:
    sec = '''<h2>💬 Спросить нейронку</h2>
<div class="card">
<textarea id="askq" rows="3" placeholder="Любой вопрос: совет, объяснение, идея, расчёт, текст…"></textarea>
<button onclick="askNow()">💬 Спросить</button>
<span class="hint" id="askst"></span>
<pre id="aska" style="display:none;max-height:50vh;overflow:auto;white-space:pre-wrap"></pre>
</div>
'''
    if '<h2>📋 Задачи</h2>' in pg:
        pg = pg.replace('<h2>📋 Задачи</h2>', sec + '<h2>📋 Задачи</h2>', 1)
        rep.append("page: раздел «Спросить нейронку»")
    else:
        rep.append("ВНИМАНИЕ: некуда вставить раздел вопроса")
if 'function askNow' not in pg:
    k = pg.rfind('</body>')
    pg = pg[:k] + '''<script>
async function askNow(){const q=document.getElementById('askq').value.trim();if(!q)return;
 document.getElementById('askst').innerText='⏳ думаю…';document.getElementById('aska').style.display='none';
 try{const r=await fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:q})}).then(x=>x.json());
 document.getElementById('askst').innerText='';document.getElementById('aska').style.display='block';
 document.getElementById('aska').innerText=r.ok?r.text:('ошибка: '+r.error);}
 catch(e){document.getElementById('askst').innerText='⚠ '+e;}}
</script>
''' + pg[k:]
    rep.append("page: скрипт вопроса")
if 'ghset-hook' not in pg:
    k = pg.rfind('</body>')
    pg = pg[:k] + '''<script id="ghset-hook">
fetch('/api/gh').then(r=>r.json()).then(g=>{
 const u=document.getElementById('ghurl'),t=document.getElementById('ghtoken');
 if(u&&g.url)u.value=g.url; if(t&&g.token)t.value=g.token;
 const pull=[...document.querySelectorAll('button')].find(b=>b.textContent.includes('Тянуть обновление'));
 if(pull&&!document.getElementById('ghsave')){
  const sb=document.createElement('button');sb.id='ghsave';sb.className='mini';sb.textContent='💾 Сохранить источник';
  sb.onclick=()=>{fetch('/api/ghset',{method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({url:u?u.value:'',token:t?t.value:''})}).then(r=>r.json()).then(()=>alert('источник сохранён на сервере: больше вводить не надо'));};
  pull.parentNode.insertBefore(sb,pull.nextSibling);
 }
}).catch(e=>{});
</script>
''' + pg[k:]
    rep.append("page: автоподстановка адреса + кнопка сохранить")
if pg != o:
    open(pp, "w").write(pg)

# 5) версия — везде v20
sp = os.path.join(D, "settings.json")
st = {}
try: st = json.load(open(sp))
except Exception: pass
st["gh_ver"] = "v20"
json.dump(st, open(sp, "w"))
rep.append("settings: gh_ver=v20")

# САМОПРОВЕРКА
r = subprocess.run([sys.executable, "-m", "py_compile", mp], capture_output=True, text=True)
if r.returncode != 0:
    shutil.copy2("/tmp/main.py.preupd", mp)
    print("ЧТО СДЕЛАНО:"); print("\n".join(rep))
    print("UPDATE FAIL: синтаксис бит — main.py восстановлен, панель на старом коде")
    print(r.stderr[-400:])
    raise SystemExit(1)

with open(os.path.join(D, "CHANGELOG.md"), "a") as f:
    f.write("\n### " + time.strftime("%d.%m %H:%M") + " — github-обновление\nv20: " + "; ".join(rep) + "\n")
subprocess.run(["git", "add", "-A"], cwd=D)
subprocess.run(["git", "commit", "-m", "update from github: v20 ask + grace + save-source"], cwd=D)
print("ЧТО СДЕЛАНО:"); print("\n".join(rep))
print("UPDATE OK: v20")