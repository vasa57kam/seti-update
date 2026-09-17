import os, re, subprocess, time
D = "/opt/agent-panel"
rep = []

# ---------- main.py ----------
mp = os.path.join(D, "main.py")
s = open(mp, errors="ignore").read()
a = '    r = subprocess.run([sys.executable, os.path.join(DIR, "update_recv.py")], capture_output=True, text=True, cwd=DIR)'
if 'SETTINGS["gh_last"]' not in s:
    if a in s:
        s = s.replace(a, a + '\n    SETTINGS["gh_last"] = {"ts": time.time(), "msg": ("OK: " if r.returncode == 0 else "FAIL: ") + (r.stdout + r.stderr)[-150:]}\n    save_settings()', 1)
        rep.append("main: запоминание результата обновления")
    else:
        rep.append("main: ВНИМАНИЕ, якорь gh_last не найден")
if '@app.get("/api/gh")' not in s:
    if '@app.get("/api/tasks")' in s:
        s = s.replace('@app.get("/api/tasks")', '@app.get("/api/gh")\ndef api_gh():\n    return {"url": SETTINGS.get("gh_url", ""), "token": SETTINGS.get("gh_token", ""), "gh_last": SETTINGS.get("gh_last")}\n\n@app.get("/api/tasks")', 1)
        rep.append("main: эндпоинт /api/gh создан")
    else:
        rep.append("main: ВНИМАНИЕ, некуда вставить /api/gh")
else:
    oldr = '    return {"url": SETTINGS.get("gh_url", ""), "token": SETTINGS.get("gh_token", "")}'
    if oldr in s:
        s = s.replace(oldr, '    return {"url": SETTINGS.get("gh_url", ""), "token": SETTINGS.get("gh_token", ""), "gh_last": SETTINGS.get("gh_last")}', 1)
        rep.append("main: /api/gh отдаёт и результат")
open(mp, "w").write(s)

# ---------- page.html ----------
pp = os.path.join(D, "page.html")
s = open(pp, errors="ignore").read()
NEWJS = '''function updOverlay(h){let o=document.getElementById('updov');if(!o){o=document.createElement('div');o.id='updov';
o.style.cssText='position:fixed;inset:0;background:#000000dd;z-index:99;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:14px;padding:20px;text-align:center';document.body.appendChild(o);}o.innerHTML=h;}
async function ghPull(){
 updOverlay('<h2>⬇️ Тяну обновление с GitHub…</h2><div class="hint">не закрывай страницу</div>');
 let r;
 try{ r=await j('/api/ghupdate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:$('ghurl').value,token:$('ghtoken').value})}); }
 catch(e){ updOverlay('<h2>❌ Сеть недоступна</h2><pre>'+e+'</pre><button onclick="location.reload()">Перезагрузить</button>'); return; }
 if(!r.ok){ updOverlay('<h2>❌ Обновление НЕ применилось</h2><pre>'+(r.error||'')+'</pre><button onclick="location.reload()">Вернуться в панель</button>'); return; }
 updOverlay('<h2>🔄 Применено, панель перезапускается…</h2><pre style="max-height:40vh;overflow:auto">'+(r.out||'').slice(-700)+'</pre><div class="hint">страница перезагрузится сама</div>');
 for(let i=0;i<40;i++){ await new Promise(x=>setTimeout(x,2000)); try{ await fetch('/api/stats'); break; }catch(e){} }
 await new Promise(x=>setTimeout(x,1500));
 location.reload();
}
async function loadGh(){try{const g=await j('/api/gh');
 if(g.url){$('ghurl').value=g.url;$('ghtoken').value=g.token||'';}
 if(g.gh_last){const el=$('ghchip');if(el)el.innerText='обновление '+new Date(g.gh_last.ts*1000).toLocaleString().slice(6,16)+' '+(g.gh_last.msg||'').slice(0,26);}
 }catch(e){}}
'''
if 'function loadGh' not in s:
    i = s.find('function ghPull(')
    if i >= 0:
        j2 = s.find('function clAdd(', i)
        if j2 < 0:
            j2 = s.find('function clLoad(', i)
        if j2 < 0:
            j2 = s.find('\n', i) + 1
        s = s[:i] + NEWJS + s[j2:]
        rep.append("page: ghPull заменён на оверлей-версию")
    else:
        k = s.rfind('</script>')
        s = s[:k] + NEWJS + s[k:]
        rep.append("page: JS вставлен перед </script>")
if 'id="ghchip"' not in s:
    if '<span class="chip" id="stats"></span>' in s:
        s = s.replace('<span class="chip" id="stats"></span>', '<span class="chip" id="stats"></span><span class="chip" id="ghchip"></span>', 1)
        rep.append("page: плашка обновления в шапке")
    else:
        s2 = re.sub(r'(<div class="topbar">)', r'\1<span class="chip" id="ghchip"></span>', s, count=1)
        if s2 != s:
            s = s2; rep.append("page: плашка добавлена в начало шапки")
if 'loadGh()' not in s:
    k = s.rfind('</script>')
    s = s[:k] + 'loadGh();setInterval(loadGh,10000);\n' + s[k:]
    rep.append("page: опрос /api/gh включён")
s = s.replace("v12 · видимые обновления", "v13 · обновления с отчётом").replace("v11 · канал GitHub", "v13 · обновления с отчётом").replace("v10 «с нуля»", "v13 · обновления с отчётом")
open(pp, "w").write(s)

with open(os.path.join(D, "CHANGELOG.md"), "a") as f:
    f.write("\n### " + time.strftime("%d.%m %H:%M") + " — github-обновление\nv13: " + "; ".join(rep) + "\n")
subprocess.run(["git", "add", "-A"], cwd=D)
subprocess.run(["git", "commit", "-m", "update from github: v13"], cwd=D)
print("ЧТО СДЕЛАНО:")
print("\n".join(rep))
print("UPDATE OK: v13")