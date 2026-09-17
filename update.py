import os, re, subprocess, time
D = "/opt/agent-panel"
rep = []
mp = os.path.join(D, "main.py")
s = open(mp, errors="ignore").read()

# 1) пустой проект: движок сам решает, какой файл создать первым
anchor = '        names_order = sorted(contents.keys(),'
seed = '''        if not contents:
            default = "index.html" if any(w in t["task"].lower() for w in ("игр", "сайт", "ленд", "админ", "html", "симул", "game")) else "main.py"
            contents = {os.path.join(pdir, default): ""}
            log.append("проект пуст: создаю " + default + " с нуля")
        names_order = sorted(contents.keys(),'''
if 'проект пуст: создаю' not in s:
    assert anchor in s, "не найден якорь names_order"
    s = s.replace(anchor, seed, 1)
    rep.append("main: пустой проект создаётся с нуля")

# 2) промпт для файла, которого ещё нет (иначе KeyError на contents[f])
pat = r'f"\\nТекущее полное содержимое файла \{rel\}:\\n```\\n\{contents\[f\]\}\\n```\\n"'
new = '(f"\\nТекущее полное содержимое файла {rel}:\\n```\\n{others.get(f, "")}\\n```\\n" if others.get(f) else f"\\nФайла {rel} ещё нет — создай его с нуля, целым и рабочим.\\n")'
s2 = re.sub(pat, lambda m: new, s, count=1)
if s2 != s:
    s = s2
    rep.append("main: промпт «файла ещё нет — создай»")
else:
    rep.append("main: ВНИМАНИЕ, строка промпта не найдена")
open(mp, "w").write(s)

with open(os.path.join(D, "CHANGELOG.md"), "a") as f:
    f.write("\n### " + time.strftime("%d.%m %H:%M") + " — github-обновление\nv14: " + "; ".join(rep) + "\n")
subprocess.run(["git", "add", "-A"], cwd=D)
subprocess.run(["git", "commit", "-m", "update from github: v14 empty project fix"], cwd=D)
print("СДЕЛАНО:")
print("\n".join(rep))
print("UPDATE OK: v14")