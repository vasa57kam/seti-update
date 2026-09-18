import os, re, json, shutil, subprocess, time, sys
D = "/opt/agent-panel"
rep = []
mp = os.path.join(D, "main.py")
shutil.copy2(mp, "/tmp/main.py.preupd")
s = open(mp, errors="ignore").read()
orig = s

# 1) сторож зависаний: до первого токена 15 минут (загрузка весов), после — 5
pat = r'(\n\s+)if beat and time\.time\(\) - beat > 300 and "ждёт" not in \(t\.get\("phase"\) or ""\):'
new = r'\1lim = 900 if not t.get("first_chunk") else 300\1if beat and time.time() - beat > lim and "ждёт" not in (t.get("phase") or ""):'
s2 = re.sub(pat, lambda m: new, s, count=1)
if s2 != s:
    s = s2; rep.append("сторож: 15 мин на загрузку весов, потом 5 мин")
else:
    rep.append("ВНИМАНИЕ: строка сторожа не найдена")

# 2) отметка первого токена в пульсе задачи
a2 = '            def chunk(pc):\n                t["beat"] = time.time()\n'
if 'first_chunk' not in s and a2 in s:
    s = s.replace(a2, a2 + '                if not t.get("first_chunk"): t["first_chunk"] = time.time()\n', 1)
    rep.append("движок: отметка первого токена")

# 3) между файлами сбрасываем отметку (вдруг модель выгрузилась и грузится снова)
a3 = '            last_text = ollama_gen(model, prompt, on_chunk=chunk, alive=lambda: t.get("status") == "running")'
if 't.pop("first_chunk", None)' not in s and a3 in s:
    s = s.replace(a3, '            t.pop("first_chunk", None)\n' + a3, 1)
    rep.append("движок: сброс отметки между файлами")

if s != orig:
    open(mp, "w").write(s)

# версия в settings
sp = os.path.join(D, "settings.json")
st = {}
try: st = json.load(open(sp))
except Exception: pass
st["gh_ver"] = "v18"
json.dump(st, open(sp, "w"))
rep.append("settings: gh_ver=v18")

# САМОПРОВЕРКА
r = subprocess.run([sys.executable, "-m", "py_compile", mp], capture_output=True, text=True)
if r.returncode != 0:
    shutil.copy2("/tmp/main.py.preupd", mp)
    print("ЧТО СДЕЛАНО:"); print("\n".join(rep))
    print("UPDATE FAIL: синтаксис бит — main.py восстановлен, панель на старом коде")
    print(r.stderr[-400:])
    raise SystemExit(1)

with open(os.path.join(D, "CHANGELOG.md"), "a") as f:
    f.write("\n### " + time.strftime("%d.%m %H:%M") + " — github-обновление\nv18: " + "; ".join(rep) + "\n")
subprocess.run(["git", "add", "-A"], cwd=D)
subprocess.run(["git", "commit", "-m", "update from github: v18 weight-loading grace"], cwd=D)
print("ЧТО СДЕЛАНО:"); print("\n".join(rep))
print("UPDATE OK: v18")