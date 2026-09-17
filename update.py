import os, subprocess, time
D = "/opt/agent-panel"

def patch(path, old, new):
    p = os.path.join(D, path)
    s = open(p, errors="ignore").read()
    if new.split("\n")[0] in s:
        return
    assert old in s, "не найден якорь в " + path + ": " + old[:60]
    open(p, "w").write(s.replace(old, new, 1))

# 1) main.py: запоминать источник при каждом протягивании
patch("main.py",
 '    if not url.startswith("https://"): return JSONResponse({"error": "need https:// raw-URL"}, 400)',
 '    if not url.startswith("https://"): return JSONResponse({"error": "need https:// raw-URL"}, 400)\n    SETTINGS["gh_url"] = url; SETTINGS["gh_token"] = token; save_settings()')

# 2) main.py: эндпоинт, откуда страница берёт сохранённый источник
patch("main.py",
 '@app.get("/api/tasks")',
 '@app.get("/api/gh")\ndef api_gh():\n    return {"url": SETTINGS.get("gh_url", ""), "token": SETTINGS.get("gh_token", "")}\n\n@app.get("/api/tasks")')

# 3) page.html: поля подставляются с сервера, а не из памяти браузера
patch("page.html",
 "$('ghurl').value=localStorage.getItem('ghurl')||'';$('ghtoken').value=localStorage.getItem('ghtoken')||'';",
 "j('/api/gh').then(g=>{$('ghurl').value=g.url||'';$('ghtoken').value=g.token||'';});")

# 4) метка версии в шапке = видимое доказательство обновления
p = os.path.join(D, "page.html")
s = open(p, errors="ignore").read()
s = s.replace("v10 «с нуля»", "v11 · канал GitHub")
open(p, "w").write(s)

with open(os.path.join(D, "CHANGELOG.md"), "a") as f:
    f.write("\n### " + time.strftime("%d.%m %H:%M") + " — github-обновление\nv11: источник обновлений хранится на сервере (/api/gh)\n")
subprocess.run(["git", "add", "-A"], cwd=D)
subprocess.run(["git", "commit", "-m", "update from github: v11 + память источника"], cwd=D)
print("UPDATE OK: v11 + память источника")