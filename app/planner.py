#!/usr/bin/env python3
"""
Stage 4 — planner screen (repo version). Local only, read-only against the
project data; the ONLY thing it writes is the planner's own decision file.

Behaviour mirrors the "MRO Planner Screen" web artifact: pick one of the 6
maintenance events, see every demand line's rule-engine verdict, read the 10
stored agent assessments (from the Stage 5/6 evaluations — no live API calls
are made from this screen), and record Approve / Reject per assessed line.
Decisions can be undone or changed; every decision is shown in a decision
log with its timestamp.

How to run:
    python3 app/planner.py            # then open http://127.0.0.1:8765
    python3 app/planner.py 9000       # custom port

Data in:   evals/planner_data.json   (generated from the rule engine + the
                                      stored evaluation assessments)
Data out:  monitoring/planner_decisions.json  (local only, gitignored —
                                      the human gate's record; never commit)

Python standard library only. The reference date stays pinned to 2026-11-02
via the data file; decision timestamps are real wall-clock times, because a
decision log is an audit record, not a simulation input.
"""
import json, os, sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(ROOT, "evals", "planner_data.json")
DECISIONS_PATH = os.path.join(ROOT, "monitoring", "planner_decisions.json")


def load_data():
    with open(DATA_PATH) as f:
        return json.load(f)


def load_decisions():
    if os.path.exists(DECISIONS_PATH):
        with open(DECISIONS_PATH) as f:
            return json.load(f)
    return {}


def save_decision(event_id, part_id, decision):
    """decision: 'approved', 'rejected', or None (undo). Returns the log."""
    decisions = load_decisions()
    key = f"{event_id}/{part_id}"
    if decision is None:
        decisions.pop(key, None)
    else:
        decisions[key] = {"event_id": event_id, "part_id": part_id,
                          "decision": decision,
                          "decided_at": datetime.now(timezone.utc).isoformat()}
    os.makedirs(os.path.dirname(DECISIONS_PATH), exist_ok=True)
    with open(DECISIONS_PATH, "w") as f:
        json.dump(decisions, f, indent=2)
    return decisions


def assessed_keys(data):
    return {f"{e['event_id']}/{l['part_id']}"
            for e in data["events"] for l in e["lines"] if l.get("assessed")}


PAGE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MRO Control Tower — Planner Screen</title>
<style>
 body{font-family:system-ui,sans-serif;margin:0;background:#0f1420;color:#e8ecf3}
 header{padding:16px 20px;background:#182136;border-bottom:1px solid #2a3550}
 header h1{margin:0 0 4px;font-size:20px} header p{margin:0;color:#9fb0cc;font-size:13px}
 #stats{padding:10px 20px;background:#141b2c;color:#cfe0ff;font-size:14px}
 main{display:flex;gap:16px;padding:16px 20px;align-items:flex-start;flex-wrap:wrap}
 #events{min-width:210px} #events button{display:block;width:100%;text-align:left;margin:0 0 8px;
   padding:10px;border:1px solid #2a3550;border-radius:8px;background:#182136;color:#e8ecf3;cursor:pointer}
 #events button.sel{border-color:#5b8cff;background:#1d2c4d}
 #detail{flex:1;min-width:320px}
 .card{background:#182136;border:1px solid #2a3550;border-radius:10px;padding:14px;margin:0 0 12px}
 .status{font-weight:700;padding:2px 8px;border-radius:6px;font-size:12px}
 .SHORT_UNCOVERED{background:#5a1f1f;color:#ff9c9c}.INSUFFICIENT_DATA{background:#5a431f;color:#ffd29c}
 .COVERED_BY_PO,.COVERED_BY_TRANSFER,.COVERED_BY_ALTERNATE{background:#1f4d3a;color:#9ce8bf}
 .OK{background:#243650;color:#bcd2f5}
 .btn{padding:10px 18px;border-radius:8px;border:0;font-size:15px;cursor:pointer;margin-right:8px}
 .approve{background:#2e9e5b;color:#fff}.reject{background:#c0392b;color:#fff}
 .ghost{background:#243650;color:#cfe0ff}
 .decided{font-weight:700}.small{color:#9fb0cc;font-size:13px}
 #log{background:#141b2c;border-top:1px solid #2a3550;padding:14px 20px}
</style></head><body>
<header><h1>MRO Control Tower — Planner Screen</h1>
<p>Synthetic data only · Reference date 2026-11-02 · The agent recommends; you decide.</p></header>
<div id="stats">Loading…</div>
<main><div id="events"></div><div id="detail"></div></main>
<div id="log"><h3>Decision log</h3><div id="logrows" class="small">No decisions yet.</div></div>
<script>
let DATA=null, DEC={}, SEL=null;
async function refresh(){
  const r=await fetch('/api/state'); const s=await r.json();
  DATA=s.data; DEC=s.decisions; if(!SEL) SEL=DATA.events[0].event_id;
  render();
}
function lines(){ return DATA.events.find(e=>e.event_id===SEL).lines; }
function stats(){
  let total=0,dec=0,ap=0,rj=0;
  for(const e of DATA.events) for(const l of e.lines) if(l.assessed){
    total++; const d=DEC[e.event_id+'/'+l.part_id];
    if(d){dec++; if(d.decision==='approved')ap++; else rj++;}
  }
  document.getElementById('stats').textContent =
    `${total} assessed lines · ${total-dec} pending · ${ap} approved · ${rj} rejected`;
}
function render(){
  stats();
  const ev=document.getElementById('events'); ev.innerHTML='';
  for(const e of DATA.events){
    const n=e.lines.filter(l=>l.assessed).length;
    const d=e.lines.filter(l=>l.assessed && DEC[e.event_id+'/'+l.part_id]).length;
    const b=document.createElement('button');
    b.className = e.event_id===SEL?'sel':'';
    b.innerHTML=`<b>${e.event_id}</b> — ${e.check_type}<br><span class="small">${e.aircraft} ${e.tail} · ${e.site} · ${e.start} → ${e.end}<br>${d}/${n} decided</span>`;
    b.onclick=()=>{SEL=e.event_id; render();};
    ev.appendChild(b);
  }
  const dt=document.getElementById('detail'); dt.innerHTML='';
  for(const l of lines()){
    const key=SEL+'/'+l.part_id, d=DEC[key];
    const c=document.createElement('div'); c.className='card';
    let h=`<div><b>${l.part_id} — ${l.part_name}</b> &nbsp;<span class="status ${l.status}">${l.status.replaceAll('_',' ')}</span></div>
      <p class="small">Required: ${l.required}${l.shortage?` · Shortage: <b>${l.shortage}</b>`:''}</p>`;
    if(l.assessed){
      h+=`<p>${l.coverage_summary}</p><p><b>Recommendation:</b> ${l.recommendation}</p>
          <p class="small">Policy notes cited: ${l.notes_cited.length?l.notes_cited.join(', '):'—'}</p>`;
      if(d) h+=`<p class="decided">${d.decision==='approved'?'✅ Approved by you':'❌ Rejected by you'} <span class="small">${d.decided_at}</span></p>
               <button class="btn ghost" onclick="decide('${key}','undo')">Undo</button>
               <button class="btn ${d.decision==='approved'?'reject':'approve'}" onclick="decide('${key}','${d.decision==='approved'?'rejected':'approved'}')">Change to ${d.decision==='approved'?'Reject':'Approve'}</button>`;
      else h+=`<button class="btn approve" onclick="decide('${key}','approved')">Approve</button>
               <button class="btn reject" onclick="decide('${key}','rejected')">Reject</button>`;
    } else {
      h+=`<p class="small">Rule-engine verdict only (not one of the 10 evaluated agent assessments) — no decision required.</p>`;
    }
    c.innerHTML=h; dt.appendChild(c);
  }
  const rows=Object.values(DEC).sort((a,b)=>a.decided_at<b.decided_at?-1:1);
  document.getElementById('logrows').innerHTML = rows.length
    ? rows.map(d=>`${d.decided_at} — ${d.event_id}/${d.part_id}: <b>${d.decision}</b>`).join('<br>')
    : 'No decisions yet.';
}
async function decide(key, decision){
  const [event_id, part_id]=key.split('/');
  await fetch('/api/decide',{method:'POST',headers:{'content-type':'application/json'},
    body: JSON.stringify({event_id, part_id, decision: decision==='undo'?null:decision})});
  refresh();
}
refresh();
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # keep the console quiet
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/state":
            self._json({"data": load_data(), "decisions": load_decisions()})
        elif self.path in ("/", "/index.html"):
            body = PAGE.encode()
            self.send_response(200)
            self.send_header("content-type", "text/html; charset=utf-8")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        if self.path != "/api/decide":
            return self._json({"error": "not found"}, 404)
        req = json.loads(self.rfile.read(int(self.headers.get("content-length", 0))))
        key = f"{req.get('event_id')}/{req.get('part_id')}"
        if key not in assessed_keys(load_data()):
            return self._json({"error": "not an assessed line"}, 400)
        if req.get("decision") not in ("approved", "rejected", None):
            return self._json({"error": "decision must be approved, rejected, or null"}, 400)
        self._json({"decisions": save_decision(req["event_id"], req["part_id"], req.get("decision"))})


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    print(f"Planner screen: http://127.0.0.1:{port}  (Ctrl+C to stop)")
    print(f"Decisions file: {DECISIONS_PATH}")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
