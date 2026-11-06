#!/usr/bin/env python3
"""Build docs/planner.html — the static GitHub Pages version of the Stage 4
planner screen. Self-contained: planner data embedded, decisions kept in the
viewer's browser (localStorage). Styled with the dashboard's colour system
(docs/dashboard.html :root palette, Barlow type, per-status colour coding).
The repo Python version (app/planner.py) remains the local audit copy.
"""
import json, os

ROOT = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(os.path.join(ROOT, "evals", "planner_data.json")))
DATA_JSON = json.dumps(data)

HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
<meta name="description" content="Interactive planner screen for the MRO Control Tower prototype: the agent recommends, the human planner decides on the recommended action — covered lines can be approved, a shortage can only be escalated, never accepted. Decisions are saved in your browser only." />
<title>MRO Control Tower — Planner Screen</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=Barlow:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root{
    --bg:#f3f4f2; --surface:#ffffff; --surface2:#eef0ec; --ink:#131a1e; --muted:#5c686f; --faint:#8a959c;
    --line:#dde1dc; --line2:#cbd2cc;
    --navy:#1e3a5f; --navy2:#2a5480;
    --ok:#177245; --ok-bg:#e2f2e7;
    --po:#1d5fd1; --po-bg:#e2ebfb;
    --transfer:#0e7a8a; --transfer-bg:#dcf2f4;
    --alt:#6d4fc2; --alt-bg:#ebe6fb;
    --short:#c62828; --short-bg:#fde7e5;
    --insuff:#b45309; --insuff-bg:#fef0d3;
    --amber:#e8a317;
    --shadow:0 1px 2px rgba(18,36,46,.06),0 8px 24px rgba(18,36,46,.06);
    --radius:14px;
  }
  *{box-sizing:border-box}
  body{font-family:"Barlow",system-ui,-apple-system,"Segoe UI",sans-serif;margin:0;background:var(--bg);color:var(--ink);font-size:16px;line-height:1.5;-webkit-font-smoothing:antialiased}
  header{background:var(--navy);color:#eef4f6;padding:26px 20px 22px;border-bottom:5px solid var(--transfer);position:relative}
  .header-top{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;font-size:13px;letter-spacing:.05em;text-transform:uppercase;color:#b9c7da}
  .live-dot i{display:inline-block;width:9px;height:9px;border-radius:50%;background:var(--transfer);margin-right:7px;box-shadow:0 0 0 3px rgba(14,122,138,.35)}
  .gate-badge{background:var(--transfer);color:#fff;font-weight:700;padding:3px 12px;border-radius:999px;letter-spacing:.06em}
  header h1{font-family:"Barlow Condensed",sans-serif;font-size:clamp(38px,6vw,58px);line-height:.95;letter-spacing:.01em;text-transform:uppercase;font-weight:700;margin:14px 0 8px}
  header h1 span{color:var(--transfer);filter:brightness(1.7)}
  .byline{font-size:16px;font-weight:600;letter-spacing:.05em;color:var(--amber);margin:0 0 12px}
  header p{margin:2px 0;color:#b9c7da;font-size:14.5px}
  header a{color:var(--amber);font-weight:600;text-decoration:none}
  .meta-pills{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}
  .meta-pills span{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.22);border-radius:999px;padding:4px 12px;font-size:13px;color:#dbe6ee}
  .meta-pills b{color:#fff}
  #hdr-count{border-color:var(--transfer);background:rgba(14,122,138,.25)}
  #stats{display:flex;gap:10px;flex-wrap:wrap;padding:16px 20px 4px}
  .tile{background:var(--surface);border:1px solid var(--line);border-top:5px solid var(--navy);border-radius:var(--radius);box-shadow:var(--shadow);padding:10px 16px;min-width:128px}
  .tile b{display:block;font-family:"Barlow Condensed",sans-serif;font-size:30px;line-height:1.05}
  .tile span{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;font-weight:600}
  .tile.t-pending{border-top-color:var(--amber)} .tile.t-decided{border-top-color:var(--ok)} .tile.t-escalated{border-top-color:var(--short)}
  #legend{display:flex;gap:14px;flex-wrap:wrap;padding:10px 20px 0;font-size:13px;color:var(--muted)}
  #legend i{display:inline-block;width:11px;height:11px;border-radius:50%;margin-right:5px;vertical-align:-1px}
  #notice{margin:12px 20px 0;background:var(--insuff-bg);border:1px solid #ecd28a;border-left:6px solid var(--amber);border-radius:var(--radius);padding:10px 14px;font-size:14px}
  #notice button{margin-left:10px}
  main{display:flex;gap:16px;padding:16px 20px;align-items:flex-start;flex-wrap:wrap}
  #events{min-width:224px;flex:0 1 248px}
  #events button{display:block;width:100%;text-align:left;margin:0 0 8px;padding:11px 13px;
    border:1px solid var(--line);border-left:6px solid var(--line2);border-radius:var(--radius);background:var(--surface);color:var(--ink);cursor:pointer;font-size:14.5px;box-shadow:var(--shadow)}
  #events button.sel{background:var(--navy);color:#eef3fa;border-left-color:var(--amber)}
  #events button.sel .small{color:#aebfd2}
  #events .prog{height:6px;background:var(--surface2);border-radius:99px;margin-top:8px;overflow:hidden}
  #events .prog i{display:block;height:100%;background:var(--amber);border-radius:99px}
  #events button.done .prog i{background:var(--ok)}
  #detail{flex:1;min-width:320px}
  .card{background:var(--surface);border:1px solid var(--line);border-left:7px solid var(--line2);border-radius:var(--radius);box-shadow:var(--shadow);padding:14px 16px;margin:0 0 12px}
  .card.s-OK{border-left-color:var(--ok)} .card.s-COVERED_BY_PO{border-left-color:var(--po)}
  .card.s-COVERED_BY_TRANSFER{border-left-color:var(--transfer)} .card.s-COVERED_BY_ALTERNATE{border-left-color:var(--alt)}
  .card.s-SHORT_UNCOVERED{border-left-color:var(--short)} .card.s-INSUFFICIENT_DATA{border-left-color:var(--insuff)}
  .status{font-weight:700;padding:3px 10px;border-radius:999px;font-size:12px;white-space:nowrap;letter-spacing:.02em}
  .SHORT_UNCOVERED{background:var(--short-bg);color:var(--short)}
  .INSUFFICIENT_DATA{background:var(--insuff-bg);color:var(--insuff)}
  .COVERED_BY_PO{background:var(--po-bg);color:var(--po)}
  .COVERED_BY_TRANSFER{background:var(--transfer-bg);color:var(--transfer)}
  .COVERED_BY_ALTERNATE{background:var(--alt-bg);color:var(--alt)}
  .OK{background:var(--ok-bg);color:var(--ok)}
  .btn{padding:10px 18px;border-radius:10px;border:0;font-size:15px;font-weight:600;cursor:pointer;margin:8px 8px 0 0}
  .approve{background:var(--ok);color:#fff}.escalate{background:var(--short);color:#fff}
  .ghost{background:var(--surface2);color:var(--navy)}
  .small{color:var(--muted);font-size:13.5px}
  .decided{font-weight:700;margin-top:8px}
  #log{background:var(--surface);border-top:3px solid var(--navy);padding:14px 20px 26px}
  #log h3{font-family:"Barlow Condensed",sans-serif;font-size:22px;margin:4px 0 8px}
  footer{padding:0 20px 22px;color:var(--muted);font-size:12.5px}
</style>
</head>
<body>
<header>
  <div class="header-top">
    <span class="live-dot"><i></i> Control Tower · Planner</span>
    <span class="gate-badge">Human decision gate · Stage 4</span>
  </div>
  <h1>MRO Control Tower <span>— Planner</span></h1>
  <p class="byline">Built by Anahita Jacobsen · Weekend project</p>
  <p>The working screen: the agent recommends, <b style="color:#fff">you decide on the recommended action</b>. A shortage is never accepted — it is escalated. Synthetic data only · Reference date __REFDATE__.</p>
  <div class="meta-pills">
    <span><b>Interactive</b> — not a snapshot</span>
    <span>6 events · 33 lines · <b>10 assessed</b></span>
    <span id="hdr-count">0 of 10 decided</span>
    <span><a href="dashboard.html">← Back to the dashboard</a></span>
  </div>
</header>

<div id="stats"></div>

<div id="legend">
  <span><i style="background:var(--ok)"></i>OK / covered on site</span>
  <span><i style="background:var(--po)"></i>Covered by purchase order</span>
  <span><i style="background:var(--transfer)"></i>Covered by transfer</span>
  <span><i style="background:var(--alt)"></i>Covered by alternate part</span>
  <span><i style="background:var(--short)"></i>Short, uncovered</span>
  <span><i style="background:var(--insuff)"></i>Insufficient data</span>
</div>

<div id="notice">
  Decisions on this page are saved <b>in this browser only</b> (they are not sent anywhere and do not change the project data).
  <button class="ghost" style="padding:6px 12px;font-size:13px" onclick="exportDecisions()">Export decisions (JSON)</button>
  <button class="ghost" style="padding:6px 12px;font-size:13px" onclick="resetAll()">Reset all</button>
</div>

<main><div id="events"></div><div id="detail"></div></main>

<div id="log"><h3>Decision log</h3><div id="logrows" class="small">No decisions yet.</div></div>

<footer>The local audit copy of this screen lives in the repository as <b>app/planner.py</b>; run it on a computer and it writes the decision file <b>monitoring/planner_decisions.json</b>. This web version mirrors its behaviour for viewing and trying the human gate.</footer>

<script>
const DATA = __DATA__;
const LS_KEY = "mroPlannerDecisionsV1";
let DEC = {};
try { DEC = JSON.parse(localStorage.getItem(LS_KEY) || "{}"); } catch(e) { DEC = {}; }
let SEL = DATA.events[0].event_id;

function save(){ localStorage.setItem(LS_KEY, JSON.stringify(DEC)); }
function assessedCount(e){ return e.lines.filter(l=>l.assessed).length; }
function decidedCount(e){ return e.lines.filter(l=>l.assessed && DEC[e.event_id+"/"+l.part_id]).length; }

/* Fixed decision model (2026-11-06): the decision is on the recommended
   ACTION, by status — never on the verdict. A SHORT_UNCOVERED line has no
   approve/accept option at all: it can only be escalated. INSUFFICIENT_DATA
   likewise. Every assessed line also offers "sent_back". */
const ACTIONS = {
  "OK": [["acknowledged","Acknowledge — no action"]],
  "COVERED_BY_PO": [["approve_monitor_po","Approve — monitor PO"]],
  "COVERED_BY_TRANSFER": [["approve_transfer","Approve transfer"]],
  "COVERED_BY_ALTERNATE": [["approve_alternate","Approve alternate use"]],
  "SHORT_UNCOVERED": [["escalate_expedite","Escalate — expedite / emergency source"],
                      ["escalate_defer","Escalate — defer event"]],
  "INSUFFICIENT_DATA": [["escalate_investigate","Escalate — investigate / physical count"]]
};
const SENT_BACK = ["sent_back","Send back for review"];
const ACTION_LABELS = {};
for(const list of Object.values(ACTIONS)) for(const [v,l] of list) ACTION_LABELS[v]=l;
ACTION_LABELS[SENT_BACK[0]] = SENT_BACK[1];
ACTION_LABELS["approved"] = "Approved (legacy)"; ACTION_LABELS["rejected"] = "Rejected (legacy)";
function actionsFor(status){ return [...(ACTIONS[status]||[]), SENT_BACK]; }
function labelFor(d){ return d.label || ACTION_LABELS[d.decision] || d.decision; }
function isEscalated(d){ return typeof d.decision==="string" && d.decision.startsWith("escalate"); }

function renderStats(){
  let total=0, dec=0, esc=0;
  for(const e of DATA.events) for(const l of e.lines) if(l.assessed){
    total++; const d=DEC[e.event_id+"/"+l.part_id];
    if(d){ dec++; if(isEscalated(d)) esc++; }
  }
  const hc=document.getElementById("hdr-count"); if(hc) hc.innerHTML = `<b>${dec} of ${total}</b>&nbsp;decided`;
  const tiles=[["Assessed lines",total,"t-total"],["Pending",total-dec,"t-pending"],["Decided",dec,"t-decided"],["Escalated",esc,"t-escalated"]];
  document.getElementById("stats").innerHTML =
    tiles.map(t=>`<div class="tile ${t[2]}"><b>${t[1]}</b><span>${t[0]}</span></div>`).join("");
}

function render(){
  renderStats();
  const ev=document.getElementById("events"); ev.innerHTML="";
  for(const e of DATA.events){
    const n=assessedCount(e), d=decidedCount(e), pct=n?Math.round(100*d/n):0;
    const b=document.createElement("button");
    b.className = (e.event_id===SEL ? "sel" : "") + (n && d===n ? " done" : "");
    b.innerHTML = `<b>${e.event_id}</b> — ${e.check_type}<br><span class="small">${e.aircraft} ${e.tail} · ${e.site} · ${e.start} → ${e.end}<br>${d}/${n} decided</span><div class="prog"><i style="width:${pct}%"></i></div>`;
    b.onclick=()=>{ SEL=e.event_id; render(); };
    ev.appendChild(b);
  }
  const dt=document.getElementById("detail"); dt.innerHTML="";
  const evObj = DATA.events.find(e=>e.event_id===SEL);
  for(const l of evObj.lines){
    const key=SEL+"/"+l.part_id, d=DEC[key];
    const c=document.createElement("div"); c.className="card s-"+l.status;
    let h=`<div><b>${l.part_id} — ${l.part_name}</b> &nbsp;<span class="status ${l.status}">${l.status.replaceAll("_"," ")}</span></div>
           <p class="small">Required: ${l.required}${l.shortage?` · Shortage: <b>${l.shortage}</b>`:""}</p>`;
    if(l.assessed){
      h+=`<p>${l.coverage_summary}</p><p><b>Recommendation:</b> ${l.recommendation}</p>
          <p class="small">Policy notes cited: ${l.notes_cited.length?l.notes_cited.join(", "):"—"}</p>`;
      if(d){
        h+=`<p class="decided">${isEscalated(d)?"⚠":"✅"} ${labelFor(d)} <span class="small">${d.decided_at}</span></p>
            <button class="btn ghost" onclick="decide('${key}',null)">Undo</button>`;
        for(const [v,lbl] of actionsFor(l.status)) if(v!==d.decision)
          h+=`<button class="btn ${v.startsWith("escalate")?"escalate":(v==="sent_back"?"ghost":"approve")}" onclick="decide('${key}','${v}')">Change to ${lbl}</button>`;
      } else {
        for(const [v,lbl] of actionsFor(l.status))
          h+=`<button class="btn ${v.startsWith("escalate")?"escalate":(v==="sent_back"?"ghost":"approve")}" onclick="decide('${key}','${v}')">${lbl}</button>`;
      }
    } else {
      h+=`<p class="small">Rule-engine verdict only (not one of the 10 evaluated agent assessments) — no decision required.</p>`;
    }
    c.innerHTML=h; dt.appendChild(c);
  }
  const rows=Object.values(DEC).sort((a,b)=>a.decided_at<b.decided_at?-1:1);
  document.getElementById("logrows").innerHTML = rows.length
    ? rows.map(d=>`${d.decided_at} — ${d.event_id}/${d.part_id}: <b>${labelFor(d)}</b> (${d.decision})`).join("<br>")
    : "No decisions yet.";
}

function decide(key, decision){
  const [event_id, part_id]=key.split("/");
  if(decision===null) delete DEC[key];
  else DEC[key]={event_id, part_id, decision, label:ACTION_LABELS[decision]||decision, decided_at:new Date().toISOString()};
  save(); render();
}
function exportDecisions(){
  const blob=new Blob([JSON.stringify(DEC,null,2)],{type:"application/json"});
  const a=document.createElement("a");
  a.href=URL.createObjectURL(blob); a.download="planner_decisions.json"; a.click();
  URL.revokeObjectURL(a.href);
}
function resetAll(){
  if(confirm("Clear all planner decisions saved in this browser?")){ DEC={}; save(); render(); }
}
render();
</script>
</body>
</html>
"""

html = HTML.replace("__DATA__", DATA_JSON).replace("__REFDATE__", data.get("reference_date", "2026-11-02"))
out = os.path.join(ROOT, "docs", "planner.html")
with open(out, "w") as f:
    f.write(html)
assessed = sum(1 for e in data["events"] for l in e["lines"] if l.get("assessed"))
print(f"wrote {out} ({len(html)} bytes); events={len(data['events'])} assessed={assessed}")
