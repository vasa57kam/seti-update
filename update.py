import os, re, json, shutil, subprocess, time, sys
D = "/opt/agent-panel"
rep = []
mp = os.path.join(D, "main.py")
pp = os.path.join(D, "page.html")
shutil.copy2(mp, "/tmp/main.py.preupd")
s = open(mp, errors="ignore").read()
orig = s

# 1) импорт StreamingResponse (если его ещё нет)
if 'StreamingResponse' not in s:
    s = s.replace('from fastapi.responses import HTMLResponse, JSONResponse, FileResponse',
                  'from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse', 1)
    rep.append("main: StreamingResponse")

# 2) заменяем /api/ask на стриминг-эндпоинт с лимитом 6000
old_ask = '''@app.post("/api/ask")
def api_ask(d: AskModel):
    q = (d.text or "").strip()
    if not q:
        return JSONResponse({"error": "пустой вопрос"}, 400)
    model = d.model or ACTIVE_MODEL
    out = ollama_gen(model, q, num_predict=2000, timeout=1800)
    return {"ok": True, "text": out.strip()}'''
new_ask = '''@app.post("/api/ask")
def api_ask(d: AskModel):
    q = (d.text or "").strip()
    if not q:
        return JSONResponse({"error": "пустой вопрос"}, 400)
    model = d.model or ACTIVE_MODEL
    import queue
    Q = queue.Queue()
    def producer():
        try:
            ollama_gen(model, q, num_predict=6000, timeout=1800,
                       on_chunk=lambda pc: Q.put(pc))
            Q.put("__DONE__")
        except Exception as e:
            Q.put("__ERR__:" + str(e)[:200])
    import threading
    threading.Thread(target=producer, daemon=True).start()
    def stream():
        while True:
            try:
                piece = Q.get(timeout=30)
            except Exception:
                yield 'data: __TO__\n\n'
                return
            if piece == "__DONE__":
                yield 'data: [DONE]\n\n'
                return
            if isinstance(piece, str) and piece.startswith("__ERR__:"):
                yield ('data: ' + json.dumps({"err": piece[6:]}) + '\n\n')
                return
            yield ('data: ' + json.dumps({"c": piece}) + '\n\n')
    return StreamingResponse(stream(), media_type="text/event-stream")'''
if old_ask in s:
    s = s.replace(old_ask, new_ask, 1)
    rep.append("main: /api/ask → стриминг SSE, 6000 токенов")
else:
    rep.append("ВНИМАНИЕ: старый /api/ask не найден")

if s != orig:
    open(mp, "w").write(s)

# 3) фронт: стриминг-вывод + индикатор «модель печатает…»
pg = open(pp, errors="ignore").read()
o = pg
old_fn = '''async function askNow(){const q=document.getElementById('askq').value.trim();if(!q)return;
 document.getElementById('askst').innerText='⏳ думаю…';document.getElementById('aska').style.display='none';
 try{const r=await fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:q})}).then(x=>x.json());
 document.getElementById('askst').innerText='';document.getElementById('aska').style.display='block';
 document.getElementById('aska').innerText=r.ok?r.text:('ошибка: '+r.error);}
 catch(e){document.getElementById('askst').innerText='⚠ '+e;}}'''
new_fn = '''async function askNow(){const q=document.getElementById('askq').value.trim();if(!q)return;
 const st=document.getElementById('askst'), out=document.getElementById('aska');
 st.innerText='⏳ модель думает и печатает…'; out.style.display='block'; out.innerText='';
 try{
  const r=await fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:q})});
  const rd=r.body.getReader(); const dec=new TextDecoder(); let buf='';
  while(true){
   const {value,done}=await rd.read(); if(done)break;
   buf+=dec.decode(value,{stream:true});
   const lines=buf.split('\\n'); buf=lines.pop();
   for(const ln of lines){
    if(!ln.startsWith('data: '))continue;
    const p=ln.slice(6);
    if(p==='[DONE]'){st.innerText='✅ готово';return;}
    if(p==='__TO__'){st.innerText='⚠ таймаут';return;}
    try{const j=JSON.parse(p);
     if(j.err){st.innerText='⚠ '+j.err;return;}
     if(j.c){out.innerText+=j.c;out.scrollTop=out.scrollHeight;}
    }catch(e){}
   }
  }
 }catch(e){st.innerText='⚠ '+e;}
}'''
if old_fn in pg:
    pg = pg.replace(old_fn, new_fn, 1)
    rep.append("page: стриминг-вывод ответа")
elif 'function askNow' in pg:
    rep.append("ВНИМАНИЕ: askNow уже другой версии — стриминг не применён")

if pg != o:
    open(pp, "w").write(pg)

# 4) версия
sp = os.path.join(D, "settings.json")
st = {}
try: st = json.load(open(sp))
except Exception: pass
st["gh_ver"] = "v22"
json.dump(st, open(sp, "w"))
rep.append("settings: gh_ver=v22")

# САМОПРОВЕРКА
r = subprocess.run([sys.executable, "-m", "py_compile", mp], capture_output=True, text=True)
if r.returncode != 0:
    shutil.copy2("/tmp/main.py.preupd", mp)
    print("ЧТО СДЕЛАНО:"); print("\n".join(rep))
    print("UPDATE FAIL: синтаксис бит — main.py восстановлен, панель на старом коде")
    print(r.stderr[-400:])
    raise SystemExit(1)

with open(os.path.join(D, "CHANGELOG.md"), "a") as f:
    f.write("\n### " + time.strftime("%d.%m %H:%M") + " — github-обновление\nv22: " + "; ".join(rep) + "\n")
subprocess.run(["git", "add", "-A"], cwd=D)
subprocess.run(["git", "commit", "-m", "update from github: v22 streaming ask + 6k tokens"], cwd=D)
print("ЧТО СДЕЛАНО:"); print("\n".join(rep))
print("UPDATE OK: v22")