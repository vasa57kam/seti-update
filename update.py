import os, re, json, shutil, subprocess, time, sys
D = "/opt/agent-panel"
rep = []
mp = os.path.join(D, "main.py")
pp = os.path.join(D, "page.html")
shutil.copy2(mp, "/tmp/main.py.preupd")
s = open(mp, errors="ignore").read()
orig = s

# 1) страница отдаётся с живой версией {{VER}}
a = '@app.get("/", response_class=HTMLResponse)\ndef index(): return open(PAGE_FILE, errors="ignore").read()'
b = '@app.get("/", response_class=HTMLResponse)\ndef index():\n    h = open(PAGE_FILE, errors="ignore").read()\n    return h.replace("{{VER}}", SETTINGS.get("gh_ver", "v13"))'
if '{{VER}}' not in s and a in s:
    s = s.replace(a, b, 1); rep.append("main: живая версия в шапке")

# 2) /api/gh: сохранённый адрес + токен + итог последнего обновления
if '@app.get("/api/gh")' not in s and '@app.get("/api/tasks")' in s:
    s = s.replace('@app.get("/api/tasks")',
        '@app.get("/api/gh")\ndef api_gh():\n    return {"url": SETTINGS.get("gh_url", ""), "token": SETTINGS.get("gh_token", ""), "gh_last": SETTINGS.get("gh_last")}\n\n@app.get("/api/tasks")', 1)
    rep.append("main: /api/gh")

# 3) запоминать адрес/токен при каждом протягивании
a3 = '    if not url.startswith("https://"): return JSONResponse({"error": "need https:// raw-URL"}, 400)'
if 'SETTINGS["gh_url"]' not in s and a3 in s:
    s = s.replace(a3, a3 + '\n    SETTINGS["gh_url"] = url; SETTINGS["gh_token"] = token; save_settings()', 1)
    rep.append("main: адрес и токен сохраняются")

# 4) запоминать итог каждого обновления
a4 = '    r = subprocess.run([sys.executable, os.path.join(DIR, "update_recv.py")], capture_output=True, text=True, cwd=DIR)'
if 'SETTINGS["gh_last"]' not in s and a4 in s:
    s = s.replace(a4, a4 + '\n    SETTINGS["gh_last"] = {"ts": time.time(), "msg": ("OK: " if r.returncode == 0 else "FAIL: ") + (r.stdout + r.stderr)[-150:]}\n    save_settings()', 1)
    rep.append("main: итог обновления сохраняется")

# 5) пустой проект создаётся с нуля (если ещё нет)
anchor = '        names_order = sorted(contents.keys(),'
seed = '''        if not contents:
            default = "index.html" if any(w in t["task"].lower() for w in ("игр", "сайт", "ленд", "админ", "html", "симул", "game")) else "main.py"
            contents = {os.path.join(pdir, default): ""}
            log.append("проект пуст: создаю " + default + " с нуля")
        names_order = sorted(contents.keys(),'''
if 'проект пуст: создаю' not in s and anchor in s:
    s = s.replace(anchor, seed, 1); rep.append("пустой проект: создание с нуля")

if s != orig:
    open(mp, "w").write(s)

# 6) страница: метка версии becomes {{VER}} + мини-скрипт подстановки адреса (без якорей)
pg = open(pp, errors="ignore").read()
o = pg
pg = re.sub(r'панель агента · [^<]*</span>', 'панель агента · {{VER}}</span>', pg, count=1)
if 'fetch(/api/gh)' not in pg:
    k = pg.rfind('</body>')
    pg = pg[:k] + '<script>\nfetch(\'/api/gh\').then(r=>r.json()).then(g=>{\nconst u=document.getElementById(\'ghurl\'),t=document.getElementById(\'ghtoken\');\nif(u&&g.url)u.value=g.url; if(t&&g.token)t.value=g.token;\n}).catch(e=>{});\n</script>\n' + pg[k:]
if pg != o:
    open(pp, "w").write(pg); rep.append("page: живая версия + автоподстановка адреса")

# 7) номер версии в settings
sp = os.path.join(D, "settings.json")
st = {}
try: st = json.load(open(sp))
except Exception: pass
st["gh_ver"] = "v17"
json.dump(st, open(sp, "w"))
rep.append("settings: gh_ver=v17")

# САМОПРОВЕРКА
r = subprocess.run([sys.executable, "-m", "py_compile", mp], capture_output=True, text=True)
if r.returncode != 0:
    shutil.copy2("/tmp/main.py.preupd", mp)
    print("ЧТО СДЕЛАНО:"); print("\n".join(rep))
    print("UPDATE FAIL: синтаксис бит — main.py восстановлен, панель на старом коде")
    print(r.stderr[-400:])
    raise SystemExit(1)

with open(os.path.join(D, "CHANGELOG.md"), "a") as f:
    f.write("\n### " + time.strftime("%d.%m %H:%M") + " — github-обновление\nv17: " + "; ".join(rep) + "\n")
subprocess.run(["git", "add", "-A"], cwd=D)
subprocess.run(["git", "commit", "-m", "update from github: v17 live version + remembered source"], cwd=D)
print("ЧТО СДЕЛАНО:"); print("\n".join(rep))
print("UPDATE OK: v17")