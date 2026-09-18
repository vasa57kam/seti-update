import os, json, shutil, subprocess, time, sys
D = "/opt/agent-panel"
rep = []
mp = os.path.join(D, "main.py")
pp = os.path.join(D, "page.html")
shutil.copy2(mp, "/tmp/main.py.preupd")
s = open(mp, errors="ignore").read()
orig = s

# 1) сторож зависаний: 15 мин до первого токена (построчно, без regex-магии)
if 'lim = 900 if not t.get' not in s:
    lines = s.split('\n')
    for i, ln in enumerate(lines):
        if 'time.time() - beat > 300' in ln:
            ind = ln[:len(ln) - len(ln.lstrip())]
            lines[i] = ln.replace('> 300', '> lim')
            lines.insert(i, ind + 'lim = 900 if not t.get("first_chunk") else 300')
            rep.append("сторож: 15 мин на загрузку весов, потом 5 мин")
            break
    else:
        rep.append("ВНИМАНИЕ: строка сторожа снова не найдена")
    s = '\n'.join(lines)

# 2) эндпоинт сохранения источника обновления
if '@app.post("/api/ghset")' not in s and '@app.get("/api/tasks")' in s:
    s = s.replace('@app.get("/api/tasks")',
        '@app.post("/api/ghset")\nasync def api_ghset(req: Request):\n    d = await req.json()\n    SETTINGS["gh_url"] = d.get("url", "") or SETTINGS.get("gh_url", "")\n    SETTINGS["gh_token"] = d.get("token", "") or SETTINGS.get("gh_token", "")\n    save_settings()\n    return {"ok": True}\n\n@app.get("/api/tasks")', 1)
    rep.append("main: кнопка сохранения источника (/api/ghset)")

# 3) автозапоминание адреса при каждом протягивании (если ещё нет)
a3 = '    if not url.startswith("https://"): return JSONResponse({"error": "need https:// raw-URL"}, 400)'
if 'SETTINGS["gh_url"]' not in s and a3 in s:
    s = s.replace(a3, a3 + '\n    SETTINGS["gh_url"] = url; SETTINGS["gh_token"] = token; save_settings()', 1)
    rep.append("main: адрес запоминается при протягивании")

if s != orig:
    open(mp, "w").write(s)

# 4) страница: автоподстановка адреса + кнопка «💾 Сохранить источник» (без якорей)
pg = open(pp, errors="ignore").read()
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
    open(pp, "w").write(pg)
    rep.append("page: автоподстановка адреса + кнопка сохранить")

# 5) версия
sp = os.path.join(D, "settings.json")
st = {}
try: st = json.load(open(sp))
except Exception: pass
st["gh_ver"] = "v19"
json.dump(st, open(sp, "w"))
rep.append("settings: gh_ver=v19")

# САМОПРОВЕРКА
r = subprocess.run([sys.executable, "-m", "py_compile", mp], capture_output=True, text=True)
if r.returncode != 0:
    shutil.copy2("/tmp/main.py.preupd", mp)
    print("ЧТО СДЕЛАНО:"); print("\n".join(rep))
    print("UPDATE FAIL: синтаксис бит — main.py восстановлен, панель на старом коде")
    print(r.stderr[-400:])
    raise SystemExit(1)

with open(os.path.join(D, "CHANGELOG.md"), "a") as f:
    f.write("\n### " + time.strftime("%d.%m %H:%M") + " — github-обновление\nv19: " + "; ".join(rep) + "\n")
subprocess.run(["git", "add", "-A"], cwd=D)
subprocess.run(["git", "commit", "-m", "update from github: v19 save-source + grace fix"], cwd=D)
print("ЧТО СДЕЛАНО:"); print("\n".join(rep))
print("UPDATE OK: v19")