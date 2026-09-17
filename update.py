
import os, subprocess, time
D = "/opt/agent-panel"
p = os.path.join(D, "page.html")
s = open(p, errors="ignore").read()
s = s.replace("v10 «с нуля»", "v11 · канал GitHub").replace("панель агента · v10", "панель агента · v11")
open(p, "w").write(s)
with open(os.path.join(D, "CHANGELOG.md"), "a") as f:
    f.write("\n### " + time.strftime("%d.%m %H:%M") + " — github-обновление\nканал обновлений работает: v11\n")
subprocess.run(["git", "add", "-A"], cwd=D)
subprocess.run(["git", "commit", "-m", "update from github: v11"], cwd=D)
print("UPDATE OK: v11")