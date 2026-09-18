import os, re, json, shutil, subprocess, time, sys
D = "/opt/agent-panel"
rep = []
mp = os.path.join(D, "main.py")
pp = os.path.join(D, "page.html")
shutil.copy2(mp, "/tmp/main.py.preupd")
s = open(mp, errors="ignore").read()
orig = s

# 1) живая версия: сервер подставляет {{VER}} из settings при отдаче страницы
a = '@app.get("/", response_class=HTMLResponse)\ndef index(): return open(PAGE_FILE, errors="ignore").read()'
b = '@app.get("/", response_class=HTMLResponse)\ndef index():\n    h = open(PAGE_FILE, errors="ignore").read()\n    return h.replace("{{VER}}", SETTINGS.get("gh_ver", "v13"))'
if '{{VER}}' not in s and a in s:
    s = s.replace(a, b, 1); rep.append("main: живая версия в шапке")

if s != orig:
    open(mp, "w").write(s)

pg = open(pp, errors="ignore").read()
o = pg

# 2) статичная метка версии -> токен {{VER}}
pg2 = re.sub(r'панель агента · [^<]*</span>', 'панель агента · {{VER}}</span>', pg, count=1)
if pg2 != pg:
    pg = pg2; rep.append("page: метка версии стала живой")

# 3) перенос блока «Спросить нейронку» сразу после «Новая задача»
i = pg.find('<h2>💬 Спросить нейронку</h2>')
j = pg.find('<h2>📋 Задачи</h2>')
if i != -1 and j != -1 and i < j:
    block = pg[i:j]
    pg = pg[:i] + pg[j:]
    k = pg.find('<h2>📁 Проекты</h2>')
    if k != -1:
        pg = pg[:k] + block + pg[k:]
    else:
        pg = pg + block
    rep.append("page: вопрос переехал к «Новая задача»")

if pg != o:
    open(pp, "w").write(pg)

# 4) версия
sp = os.path.join(D, "settings.json")
st = {}
try: st = json.load(open(sp))
except Exception: pass
st["gh_ver"] = "v21"
json.dump(st, open(sp, "w"))
rep.append("settings: gh_ver=v21")

# САМОПРОВЕРКА
r = subprocess.run([sys.executable, "-m", "py_compile", mp], capture_output=True, text=True)
if r.returncode != 0:
    shutil.copy2("/tmp/main.py.preupd", mp)
    print("ЧТО СДЕЛАНО:"); print("\n".join(rep))
    print("UPDATE FAIL: синтаксис бит — main.py восстановлен, панель на старом коде")
    print(r.stderr[-400:])
    raise SystemExit(1)

with open(os.path.join(D, "CHANGELOG.md"), "a") as f:
    f.write("\n### " + time.strftime("%d.%m %H:%M") + " — github-обновление\nv21: " + "; ".join(rep) + "\n")
subprocess.run(["git", "add", "-A"], cwd=D)
subprocess.run(["git", "commit", "-m", "update from github: v21 live version + ask position"], cwd=D)
print("ЧТО СДЕЛАНО:"); print("\n".join(rep))
print("UPDATE OK: v21")