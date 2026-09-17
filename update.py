import os, subprocess, time
D = "/opt/agent-panel"

def patch(path, old, new):
    p = os.path.join(D, path)
    s = open(p, errors="ignore").read()
    if new.split("\n")[0] in s:
        return
    assert old in s, "не найден якорь в " + path + ": " + old[:60]
    open(p, "w").write(s.replace(old, new, 1))

# 1) сервер запоминает РЕЗУЛЬТАТ каждого обновления
patch("main.py",
 '    r = subprocess.run([sys.executable, os.path.join(DIR, "update_recv.py")], capture_output=True, text=True, cwd=DIR)',
 '    r = subprocess.run([sys.executable, os.path.join(DIR, "update_recv.py")], capture_output=True, text=True, cwd=DIR)\n    SETTINGS["gh_last"] = {"ts": time.time(), "msg": ("OK: " if r.returncode == 0 else "FAIL: ") + (r.stdout + r.stderr)[-150:]}\n    save_settings()')

# 2) /api/gh отдаёт источник + последний результат (или создаётся, если его нет)
mp = os.path.join(D, "main.py")
s = open(mp, errors="ignore").read()
if '@app.get("/api/gh")' not in s:
    s = s.replace('@app.get("/api/tasks")',
        '@app.get("/api/gh")\ndef api_gh():\n    return {"url": SETTINGS.get("gh_url", ""), "token": SETTINGS.get("gh_token", ""), "gh_last": SETTINGS.get("gh_last")}\n\n@app.get("/api/tasks")', 1)
    open(mp, "w").write(s)
else:
    patch("main.py",
     '    return {"url": SETTINGS.get("gh_url", ""), "token": SETTINGS.get("gh_token", "")}',
     '    return {"url": SETTINGS.get("gh_url", ""), "token": SETTINGS.get("gh_token", ""), "gh_last": SETTINGS.get("gh_last")}')

# 3) плашка в шапке с датой и итогом последнего обновления
patch("page.html",
 '<span class="chip" id="stats"></span>',
 '<span class="chip" id="stats"></span><span class="chip" id="ghchip"></span>')

# 4) понятный оверлей + автоперезагрузка браузера после рестарта панели
patch("page.html",
 """function ghPull(){j('/api/ghupdate',{method:'POST',headers:{'Content-Type':'application/json'},
 body:JSON.stringify({url:$('ghurl').value,token:$('ghtoken').value})}).then(r=>alert(r.ok?('применяю…\\n'+(r.out||'').slice(-400)):('ошибка: '+r.error)));}""",
 """function updOverlay(h){let o=document.getElementById('updov');if(!o){o=document.createElement('div');o.id='updov';
 o.style.cssText='position:fixed;inset:0;background:#000000dd;z-index:99;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:14px;padding:20px;text-align:center';document.body.appendChild(o);}o.innerHTML=h;}
async function ghPull(){
 updOverlay('<h2>⬇️ Тяну обновление с GitHub…</h2><div class="hint">не закрывай страницу</div>');
 let r;
 try{ r=await j('/api/ghupdate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:$('ghurl').value,token:$('ghtoken').value})}); }
 catch(e){ updOverlay('<h2>❌ Сеть недоступна</h2><pre>'+e+'</pre><button onclick="location.reload()">Перезагрузить</button>'); return; }
 if(!r.ok){ updOverlay('<h2>❌ Обновление НЕ применилось</h2><pre>'+(r.error||'')+'</pre><button onclick="location.reload()">Вернуться в панель</button>'); return; }
 updOverlay('<h2>🔄 Обновление применилось, панель перезапускается…</h2><pre style="max-height:40vh;overflow:auto">'+(r.out||'').slice(-700)+'</pre><div class="hint">страница перезагрузится сама</div>');
 for(let i=0;i<40;i++){ await new Promise(s=>setTimeout(s,2000)); try{ await fetch('/api/stats'); break; }catch(e){} }
 await new Promise(s=>setTimeout(s,1500));
 location.reload();
}
async function loadGh(){try{const g=await j('/api/gh');
 if(g.url){$('ghurl').value=g.url;$('ghtoken').value=g.token||'';}
 if(g.gh_last){$('ghchip').innerText='обновление '+new Date(g.gh_last.ts*1000).toLocaleString().slice(6,16)+' '+(g.gh_last.msg||'').slice(0,26);}
 }catch(e){}}""")

# 5) старт опроса плашки
patch("page.html",
 'setInterval(loadAll,4000);setInterval(loadBench,60000);',
 'setInterval(loadAll,4000);setInterval(loadBench,60000);loadGh();setInterval(loadGh,10000);')

# 6) метка версии
p = os.path.join(D, "page.html")
s = open(p, errors="ignore").read()
s = s.replace("v11 · канал GitHub", "v12 · видимые обновления").replace("v10 «с нуля»", "v12 · видимые обновления")
open(p, "w").write(s)

with open(os.path.join(D, "CHANGELOG.md"), "a") as f:
    f.write("\n### " + time.strftime("%d.%m %H:%M") + " — github-обновление\nv12: понятный оверлей обновления + автоперезагрузка страницы + плашка в шапке\n")
subprocess.run(["git", "add", "-A"], cwd=D)
subprocess.run(["git", "commit", "-m", "update from github: v12 visible updates"], cwd=D)
print("UPDATE OK: v12")