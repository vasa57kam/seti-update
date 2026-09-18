import os, re, shutil, subprocess, time, sys
D = "/opt/agent-panel"
rep = []
mp = os.path.join(D, "main.py")
shutil.copy2(mp, "/tmp/main.py.preupd")
s = open(mp, errors="ignore").read()
orig = s

# 1) пустой проект: движок сам создаёт первый файл с нуля
anchor = '        names_order = sorted(contents.keys(),'
seed = '''        if not contents:
            default = "index.html" if any(w in t["task"].lower() for w in ("игр", "сайт", "ленд", "админ", "html", "симул", "game")) else "main.py"
            contents = {os.path.join(pdir, default): ""}
            log.append("проект пуст: создаю " + default + " с нуля")
        names_order = sorted(contents.keys(),'''
if 'проект пуст: создаю' not in s:
    if anchor in s:
        s = s.replace(anchor, seed, 1); rep.append("пустой проект: создание с нуля")
    else:
        rep.append("ВНИМАНИЕ: якорь names_order не найден")

# 2) промпт для файла, которого ещё нет (одинарные кавычки внутри f-string!)
pat = r'f"\\nТекущее полное содержимое файла \{rel\}:\\n```\\n\{contents\[f\]\}\\n```\\n"'
new = '(f"\\nТекущее полное содержимое файла {rel}:\\n```\\n{others.get(f, chr(39)+chr(39))}\\n```\\n" if others.get(f) else f"\\nФайла {rel} ещё нет — создай его с нуля, целым и рабочим.\\n")'
s2 = re.sub(pat, lambda m: new, s, count=1)
if s2 != s:
    s = s2; rep.append("промпт: файла ещё нет — создай")

# 3) защита рабочих проектов от переписывания
old = '\\n\\nРаботай автономно, не задавай вопросов.\\n'
newr = old + 'ВАЖНО: если в проекте уже есть рабочие файлы — вноси ТОЛЬКО точечные правки, сохраняя все существующие механики, интерфейс и структуру. Полное переписывание с нуля запрещено, если задача не просит об этом прямо.\\n'
if 'Полное переписывание с нуля запрещено' not in s and old in s:
    s = s.replace(old, newr, 1); rep.append("защита от переписывания рабочих проектов")

# 4) золотые копии каждого записанного файла
oldw = '            open(f, "w").write(c)\n            others[f] = c'
neww = '            open(f, "w").write(c)\n            try:\n                gd = os.path.join(pdir, ".golden"); os.makedirs(gd, exist_ok=True)\n                shutil.copy2(f, os.path.join(gd, os.path.basename(f)))\n            except Exception: pass\n            others[f] = c'
if '.golden", os.path.basename' not in s and oldw in s:
    s = s.replace(oldw, neww, 1); rep.append("золотые копии файлов")

# 5) .golden не попадает в обход проекта
oldd = '".aider.tags.cache.v4", "node_modules"'
newd = '".aider.tags.cache.v4", "node_modules", ".golden"'
if '".golden"' not in s and oldd in s:
    s = s.replace(oldd, newd, 1); rep.append(".golden исключён из обхода")

if s != orig:
    open(mp, "w").write(s)

# САМОПРОВЕРКА: битый синтаксис = откат копии, панель стартует на старом коде
r = subprocess.run([sys.executable, "-m", "py_compile", mp], capture_output=True, text=True)
if r.returncode != 0:
    shutil.copy2("/tmp/main.py.preupd", mp)
    print("ЧТО СДЕЛАНО:")
    print("\n".join(rep))
    print("UPDATE FAIL: синтаксис бит — main.py восстановлен из копии, панель поднимется на старом коде")
    print(r.stderr[-500:])
    raise SystemExit(1)

with open(os.path.join(D, "CHANGELOG.md"), "a") as f:
    f.write("\n### " + time.strftime("%d.%m %H:%M") + " — github-обновление\nv16: " + "; ".join(rep or ["всё уже было на месте"]) + "\n")
subprocess.run(["git", "add", "-A"], cwd=D)
subprocess.run(["git", "commit", "-m", "update from github: v16 safe create-from-scratch"], cwd=D)
print("ЧТО СДЕЛАНО:")
print("\n".join(rep or ["всё уже было на месте — проверено"]))
print("UPDATE OK: v16")