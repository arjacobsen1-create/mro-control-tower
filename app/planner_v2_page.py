#!/usr/bin/env python3
"""
The V2 planner page template — shared by app/planner_v2.py (local
server mode: decisions POST to /api/decide and are validated
server-side) and evals/../build_planner_page_v2.py (static mode: data
embedded, decisions kept in localStorage; the same decision model is
enforced client-side). __MODE__ is "server" or "static"; in static
mode __DATA__ is replaced with the planner data JSON.

The decision model implemented here (and server-side in
app/planner_v2.py) is spec §7 exactly: precedence shortage rows ->
SLIPPAGE_HIGH -> Tier A -> status row (allocated view governs);
notification and procurement are separate fields of the record;
every HIGH-line record requires a recovery path; a notification
recorded as released requires the four §4.6 verifications; a
place-order record names the documented §5.6 need.
"""

PAGE_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MRO Control Tower — Planner Screen V2 (cross-event &amp; risk)</title>
<style>
 body{font-family:system-ui,sans-serif;margin:0;background:#0f1420;color:#e8ecf3}
 header{padding:16px 20px;background:#182136;border-bottom:1px solid #2a3550}
 header h1{margin:0 0 4px;font-size:20px} header p{margin:0;color:#9fb0cc;font-size:13px}
 #stats{padding:10px 20px;background:#141b2c;color:#cfe0ff;font-size:14px}
 nav{padding:8px 20px;background:#141b2c;border-top:1px solid #2a3550}
 nav button{margin-right:8px;padding:7px 14px;border-radius:8px;border:1px solid #2a3550;background:#182136;color:#e8ecf3;cursor:pointer}
 nav button.sel{border-color:#5b8cff;background:#1d2c4d}
 main{padding:16px 20px}
 .cols{display:flex;gap:16px;align-items:flex-start;flex-wrap:wrap}
 #events{min-width:210px} #events button{display:block;width:100%;text-align:left;margin:0 0 8px;
   padding:10px;border:1px solid #2a3550;border-radius:8px;background:#182136;color:#e8ecf3;cursor:pointer}
 #events button.sel{border-color:#5b8cff;background:#1d2c4d}
 #detail{flex:1;min-width:340px}
 .card{background:#182136;border:1px solid #2a3550;border-radius:10px;padding:14px;margin:0 0 12px}
 .status{font-weight:700;padding:2px 8px;border-radius:6px;font-size:12px;white-space:nowrap}
 .SHORT_UNCOVERED{background:#5a1f1f;color:#ff9c9c}.INSUFFICIENT_DATA{background:#5a431f;color:#ffd29c}
 .COVERED_BY_PO,.COVERED_BY_TRANSFER,.COVERED_BY_ALTERNATE{background:#1f4d3a;color:#9ce8bf}
 .OK{background:#243650;color:#bcd2f5}
 .badge{display:inline-block;padding:1px 7px;border-radius:8px;font-size:11.5px;border:1px solid #3a4a6b;color:#cfe0ff;background:#1d2c4d;margin:2px 2px 2px 0}
 .badge.hot{background:#5a1f1f;color:#ffb1b1;border-color:#8a3434}
 .badge.warn{background:#5a431f;color:#ffd29c;border-color:#8a6a34}
 .badge.cool{background:#1f4d3a;color:#9ce8bf;border-color:#2e7d5b}
 .btn{padding:9px 15px;border-radius:8px;border:0;font-size:14px;cursor:pointer;margin:4px 6px 2px 0}
 .approve{background:#2e9e5b;color:#fff}.escalate{background:#c0392b;color:#fff}
 .ghost{background:#243650;color:#cfe0ff}.notify{background:#6a4a9e;color:#fff}
 .decided{font-weight:700}.small{color:#9fb0cc;font-size:13px}
 .field{margin:8px 0;padding:9px;border:1px dashed #2a3550;border-radius:8px}
 .field b.t{display:block;margin-bottom:5px;font-size:13px;color:#cfe0ff}
 select{background:#0f1420;color:#e8ecf3;border:1px solid #2a3550;border-radius:6px;padding:6px}
 label.v{display:block;font-size:13px;margin:3px 0}
 table{border-collapse:collapse;width:100%;font-size:13.5px}
 th,td{border-bottom:1px solid #2a3550;padding:6px 8px;text-align:left;vertical-align:top}
 #log{background:#141b2c;border-top:1px solid #2a3550;padding:14px 20px}
 .err{color:#ff9c9c;font-size:13px;min-height:16px}
 .clock{display:inline-block;padding:1px 7px;border-radius:8px;font-size:11.5px;margin:2px 2px 2px 0;border:1px solid #3a4a6b;background:#141b2c}
</style></head><body>
<header><h1>MRO Control Tower — Planner Screen V2</h1>
<p>Cross-event allocation · slippage risk · order-by watchlist · two-clock horizon.
Synthetic data only · Reference date 2026-11-02 · The agent recommends; you decide.
V2 evaluation: <b id="evalscore">—</b></p></header>
<div id="stats">Loading…</div>
<nav>
 <button data-view="events" class="sel">Event lines</button>
 <button data-view="alloc">Allocation ledgers</button>
 <button data-view="watch">Watchlist</button>
 <button data-view="horizon">Horizon — forward events</button>
</nav>
<main>
 <div id="view-events" class="cols"><div id="events"></div><div id="detail"></div></div>
 <div id="view-alloc" style="display:none"></div>
 <div id="view-watch" style="display:none"></div>
 <div id="view-horizon" style="display:none"></div>
</main>
<div id="log"><h3>Decision log</h3><div id="logrows" class="small">No decisions yet.</div></div>
<script>
const MODE = "__MODE__";
let DATA = __DATA__, DEC = {}, SEL = null, VIEW = "events";
const LSKEY = "mro_planner_v2_decisions";
const STATUS_ACTIONS = { "OK":["acknowledged"], "COVERED_BY_PO":["approve_monitor_po"],
  "COVERED_BY_TRANSFER":["approve_transfer"], "COVERED_BY_ALTERNATE":["approve_alternate"],
  "SHORT_UNCOVERED":["escalate_expedite","escalate_defer"], "INSUFFICIENT_DATA":["escalate_investigate"] };
const LABELS = { "acknowledged":"Acknowledge — no action", "approve_monitor_po":"Approve — monitor PO",
  "approve_transfer":"Approve transfer", "approve_alternate":"Approve alternate use",
  "escalate_expedite":"Escalate — expedite / emergency source", "escalate_defer":"Escalate — defer event",
  "escalate_investigate":"Escalate — investigate / physical count", "sent_back":"Send back for review",
  "notify_customer_at_risk":"Notify customer — at risk", "place_order":"Decide: place the order",
  "acknowledge_lapse":"Acknowledge — let the window lapse" };
const RECOVERY_PATHS = ["expedite / chase PO","exchange / rotable","transfer under allocation","re-sequence the check","defer"];
const VERIFS = ["affected_event","material_shortfall","recovery_options","proposed_communication"];
const VERIF_LABELS = { "affected_event":"Affected event verified","material_shortfall":"Material shortfall verified",
  "recovery_options":"Recovery options verified","proposed_communication":"Proposed communication verified" };
const DRAFT = {};  // key -> draft record fields

function isShort(l){ return l.allocated_status==="SHORT_UNCOVERED" || l.status==="SHORT_UNCOVERED"; }
function isInsuff(l){ return l.allocated_status==="INSUFFICIENT_DATA" || l.status==="INSUFFICIENT_DATA"; }
function isHigh(l){ return l.slippage_tier==="SLIPPAGE_HIGH" || l.contention==="CONTENDED_SHORT"; }
function tierAGoverns(l){ return !isShort(l) && !isInsuff(l) && l.slippage_tier!=="SLIPPAGE_HIGH"
  && l.watchlist_tier==="ORDER_BY_CLOSING"; }
function allowedPrimary(l){
  let base;
  if (isShort(l)) base = ["escalate_expedite","escalate_defer","notify_customer_at_risk"];
  else if (isInsuff(l)) base = ["escalate_investigate"];
  else if (l.slippage_tier==="SLIPPAGE_HIGH") base = ["escalate_expedite","notify_customer_at_risk"];
  else if (tierAGoverns(l)) base = ["place_order","acknowledge_lapse"];
  else { base = [...(STATUS_ACTIONS[l.allocated_status]||[])];
         if (l.slippage_tier==="SLIPPAGE_WATCH") base.push("escalate_expedite"); }
  return [...base, "sent_back"];
}
function notifyAllowed(l){ return isShort(l) || l.slippage_tier==="SLIPPAGE_HIGH"; }
function labelFor(d){ return d.label || LABELS[d.decision] || d.decision; }
function isEscalated(d){ return typeof d.decision==="string" && d.decision.startsWith("escalate"); }
function esc(s){ return String(s??"").replaceAll("&","&amp;").replaceAll("<","&lt;"); }

async function refresh(){
  if (MODE==="server"){
    const r = await fetch("/api/state"); const s = await r.json();
    DATA = s.data; DEC = s.decisions;
  } else {
    try { DEC = JSON.parse(localStorage.getItem(LSKEY) || "{}"); } catch(e){ DEC = {}; }
  }
  if (!SEL) SEL = DATA.events[0].event_id;
  document.getElementById("evalscore").textContent =
    DATA.v2_evaluation.score + " new scenarios · V1 regression " + DATA.v2_evaluation.v1_regression;
  render();
}
function stats(){
  let total=0, dec=0, escn=0;
  for (const e of DATA.events) for (const l of e.lines) if (l.assessed){
    total++; const d = DEC[e.event_id+"/"+l.part_id];
    if (d){ dec++; if (isEscalated(d)) escn++; }
  }
  document.getElementById("stats").textContent =
    `${total} assessed lines · ${total-dec} pending · ${dec} decided · ${escn} escalated`;
}
function badges(l){
  let h = "";
  if (l.contention!=="UNCONTENDED") h += `<span class="badge ${l.contention==="CONTENDED_SHORT"?"hot":"warn"}">${l.contention.replaceAll("_"," ")}</span>`;
  if (l.slippage_tier==="SLIPPAGE_HIGH") h += `<span class="badge hot">SLIPPAGE HIGH · checkpoint ${l.notification.checkpoint_date||l.slippage_detail.checkpoint_date||""}</span>`;
  if (l.slippage_tier==="SLIPPAGE_WATCH") h += `<span class="badge warn">SLIPPAGE WATCH</span>`;
  if (l.watchlist_tier==="ORDER_BY_CLOSING") h += `<span class="badge warn">WATCHLIST · ORDER BY ${l.order_by_date} — CLOSING</span>`;
  if (l.watchlist_tier==="NO_ORDERING_FALLBACK") h += `<span class="badge">WATCHLIST · NO ORDERING FALLBACK (order-by ${l.order_by_date} passed)</span>`;
  if (l.procurement_action==="RAISED") h += `<span class="badge cool">PROCUREMENT ACTION RAISED</span>`;
  if (l.notification.eligible) h += `<span class="badge warn">CUSTOMER NOTIFICATION ELIGIBLE · checkpoint ${l.notification.checkpoint_date}</span>`;
  h += `<span class="clock">Clock 1 (order-by): ${l.clock1.band}${l.clock1.escalated?" · ESCALATED":""}</span>`;
  if (l.clock2.applicable) h += `<span class="clock">Clock 2 (event): ${l.clock2.band} · lead ${l.clock2.lead_time_days}d</span>`;
  return h;
}
function draftFor(key, l){
  if (!DRAFT[key]) DRAFT[key] = { decision:null, recovery_path: (l.assessment&&l.assessment.recovery_path)||null,
    notify:false, released:false, verifications:{}, procurement_decision:null };
  return DRAFT[key];
}
function render(){
  stats();
  document.querySelectorAll("nav button").forEach(b=>{
    b.classList.toggle("sel", b.dataset.view===VIEW);
    b.onclick = ()=>{ VIEW=b.dataset.view; render(); };
  });
  for (const v of ["events","alloc","watch","horizon"])
    document.getElementById("view-"+v).style.display = (v===VIEW) ? "" : "none";
  if (VIEW==="events") renderEvents();
  if (VIEW==="alloc") renderAlloc();
  if (VIEW==="watch") renderWatch();
  if (VIEW==="horizon") renderHorizon();
  renderLog();
}
function renderEvents(){
  const ev = document.getElementById("events"); ev.innerHTML = "";
  for (const e of DATA.events){
    const n = e.lines.filter(l=>l.assessed).length;
    const dn = e.lines.filter(l=>l.assessed && DEC[e.event_id+"/"+l.part_id]).length;
    const b = document.createElement("button");
    b.className = e.event_id===SEL ? "sel" : "";
    b.innerHTML = `<b>${e.event_id}</b> — ${esc(e.event_name)}<br><span class="small">${esc(e.tail)} · starts ${e.start}<br>${dn}/${n} decided</span>`;
    b.onclick = ()=>{ SEL=e.event_id; render(); };
    ev.appendChild(b);
  }
  const e = DATA.events.find(x=>x.event_id===SEL);
  const dt = document.getElementById("detail"); dt.innerHTML = "";
  for (const l of e.lines) dt.appendChild(lineCard(e, l));
}
function lineCard(e, l){
  const key = e.event_id+"/"+l.part_id, d = DEC[key];
  const c = document.createElement("div"); c.className = "card";
  let h = `<div><b>${l.part_id} — ${esc(l.part_name)}</b></div>
    <p style="margin:6px 0">Single-line view: <span class="status ${l.status}">${l.status.replaceAll("_"," ")}</span>
    &nbsp; Allocated view: <span class="status ${l.allocated_status}">${l.allocated_status.replaceAll("_"," ")}</span>
    <span class="small"> · required ${l.needed}${l.allocated_shortage_qty?` · allocated shortage <b>${l.allocated_shortage_qty}</b>`:""}</span></p>
    <div>${badges(l)}</div>`;
  if (l.procurement_action==="RAISED" && l.procurement_need)
    h += `<p class="small"><b>Documented procurement need (§5.6):</b> ${esc(l.procurement_need)}</p>`;
  if (!l.assessed){
    h += `<p class="small">Rule-engine verdicts only — not one of the assessed lines; no decision required here.</p>`;
    c.innerHTML = h; return c;
  }
  const a = l.assessment, dr = draftFor(key, l);
  h += `<p>${esc(a.coverage_summary)}</p><p><b>Recommendation:</b> ${esc(a.recommendation)}</p>
        <p class="small">Policy notes cited: ${a.notes_cited.length?a.notes_cited.join(", "):"—"} · assessment source: ${esc(l.assessment_source||"")}</p>`;
  if (d){
    h += `<p class="decided">${isEscalated(d)?"⚠":"✅"} ${esc(labelFor(d))} <span class="small">${esc(d.decided_at)}</span></p>`;
    if (d.recovery_path) h += `<p class="small">Recovery path: <b>${esc(d.recovery_path)}</b></p>`;
    if (d.notification) h += `<p class="small">Customer notification: <b>recorded${d.notification.released?" · RELEASED (verifications recorded)":" · not released"}</b> · checkpoint ${esc(d.notification.checkpoint_date||"")}</p>`;
    if (d.procurement_decision) h += `<p class="small">Procurement decision: <b>${esc(LABELS[d.procurement_decision]||d.procurement_decision)}</b></p>`;
    h += `<button class="btn ghost" onclick="decideUndo('${key}')">Undo decision</button>`;
  }
  // primary decision buttons
  h += `<div class="field"><b class="t">Decision (on the recommended action — §7)</b>`;
  for (const v of allowedPrimary(l))
    h += `<button class="btn ${v.startsWith("escalate")?"escalate":(v==="sent_back"?"ghost":(v==="notify_customer_at_risk"?"notify":"approve"))}" onclick="setDraft('${key}','decision','${v}')">${LABELS[v]}</button>`;
  h += `<span class="small">selected: <b id="sel-${key}">${dr.decision?LABELS[dr.decision]:"—"}</b></span></div>`;
  if (isHigh(l) || isShort(l)){
    h += `<div class="field"><b class="t">Recovery path ${isHigh(l)?"(required on a HIGH line)":""}</b>
      <select id="rec-${key}">${RECOVERY_PATHS.map(p=>`<option ${dr.recovery_path===p?"selected":""}>${p}</option>`).join("")}</select></div>`;
  }
  if (notifyAllowed(l)){
    h += `<div class="field"><b class="t">Customer notification (§4.6 — a prepared draft, never sent by the system; checkpoint ${esc(l.notification.checkpoint_date||"")})</b>
      <label class="v"><input type="checkbox" id="ntf-${key}" ${dr.notify?"checked":""}> Record notification decision</label>
      <label class="v"><input type="checkbox" id="rel-${key}" ${dr.released?"checked":""}> Record as RELEASED (requires all four verifications)</label>
      ${VERIFS.map(v=>`<label class="v"><input type="checkbox" id="ver-${key}-${v}" ${dr.verifications[v]?"checked":""}> ${VERIF_LABELS[v]}</label>`).join("")}</div>`;
  }
  if (l.procurement_action==="RAISED" && !tierAGoverns(l)){
    h += `<div class="field"><b class="t">Procurement decision (§5.6 — separate field; the coverage decision above stands)</b>
      <button class="btn approve" onclick="setDraft('${key}','procurement_decision','place_order')">Decide: place the order</button>
      <button class="btn ghost" onclick="setDraft('${key}','procurement_decision','acknowledge_lapse')">Acknowledge — let the window lapse</button>
      <span class="small">selected: <b id="selp-${key}">${dr.procurement_decision?LABELS[dr.procurement_decision]:"—"}</b></span></div>`;
  }
  h += `<div><button class="btn approve" onclick="saveDecision('${key}')">Record decision</button>
        <span class="err" id="err-${key}"></span></div>`;
  c.innerHTML = h; return c;
}
function setDraft(key, field, value){
  const [ev, pid] = key.split("/");
  const l = DATA.events.find(e=>e.event_id===ev).lines.find(x=>x.part_id===pid);
  draftFor(key, l)[field] = value; render();
}
function collectFields(key){
  const [ev, pid] = key.split("/");
  const e = DATA.events.find(x=>x.event_id===ev), l = e.lines.find(x=>x.part_id===pid);
  const dr = draftFor(key, l);
  const recSel = document.getElementById("rec-"+key);
  const fields = { event_id: ev, part_id: pid, decision: dr.decision,
    recovery_path: recSel ? recSel.value : (dr.recovery_path || null),
    notification: null, procurement_decision: dr.procurement_decision || null };
  const ntf = document.getElementById("ntf-"+key);
  if (ntf && ntf.checked){
    const verifications = {};
    for (const v of VERIFS) verifications[v] = document.getElementById(`ver-${key}-${v}`).checked;
    fields.notification = { action: "notify_customer_at_risk",
      released: document.getElementById("rel-"+key).checked, verifications };
  }
  return fields;
}
function validateFields(l, f){
  // The §7 model. Server mode: app/planner_v2.py enforces this
  // server-side and this is only a first check. Static mode: this IS
  // the enforcement (the static page has no server).
  if (!allowedPrimary(l).includes(f.decision))
    throw new Error("decision not allowed for this line's state: " + f.decision);
  if (isHigh(l) && !f.recovery_path)
    throw new Error("a HIGH line decision must record a recovery path");
  if (f.recovery_path && !RECOVERY_PATHS.includes(f.recovery_path))
    throw new Error("unknown recovery path");
  if (f.notification){
    if (!notifyAllowed(l)) throw new Error("notification is not offered for this line's state");
    if (f.notification.released && !VERIFS.every(v=>f.notification.verifications[v]))
      throw new Error("a released notification requires all four verifications");
  }
  if (f.procurement_decision){
    if (!["place_order","acknowledge_lapse"].includes(f.procurement_decision))
      throw new Error("unknown procurement decision");
    if (l.procurement_action!=="RAISED" || !l.procurement_need)
      throw new Error("a procurement decision requires a documented need on the line");
  }
}
async function postDecision(fields){
  const key = fields.event_id+"/"+fields.part_id;
  if (MODE==="server"){
    const r = await fetch("/api/decide", {method:"POST", headers:{"content-type":"application/json"}, body: JSON.stringify(fields)});
    const s = await r.json();
    if (!r.ok) throw new Error(s.error || "rejected");
    DEC = s.decisions;
  } else {
    if (fields.decision===null){ delete DEC[key]; }
    else {
      const e = DATA.events.find(x=>x.event_id===fields.event_id), l = e.lines.find(x=>x.part_id===fields.part_id);
      validateFields(l, fields);
      DEC[key] = { event_id: fields.event_id, part_id: fields.part_id, decision: fields.decision,
        label: LABELS[fields.decision] || fields.decision, decided_at: new Date().toISOString(),
        flags: { status: l.status, allocated_status: l.allocated_status, contention: l.contention,
                 slippage_tier: l.slippage_tier, watchlist_tier: l.watchlist_tier },
        recovery_path: fields.recovery_path,
        notification: fields.notification ? { ...fields.notification, checkpoint_date: l.notification.checkpoint_date } : null,
        procurement_decision: fields.procurement_decision,
        procurement_need: fields.procurement_decision ? l.procurement_need : null };
    }
    localStorage.setItem(LSKEY, JSON.stringify(DEC));
  }
}
async function saveDecision(key){
  const err = document.getElementById("err-"+key);
  try {
    const fields = collectFields(key);
    if (!fields.decision && !fields.notification && !fields.procurement_decision)
      throw new Error("choose a decision first");
    if (!fields.decision) throw new Error("choose a primary decision (notification and procurement are recorded alongside one)");
    await postDecision(fields);
    delete DRAFT[key]; render();
  } catch(ex){ if (err) err.textContent = ex.message; }
}
async function decideUndo(key){
  const [ev, pid] = key.split("/");
  await postDecision({ event_id: ev, part_id: pid, decision: null, recovery_path: null, notification: null, procurement_decision: null });
  delete DRAFT[key]; render();
}
function renderAlloc(){
  const w = document.getElementById("view-alloc");
  let h = `<p class="small">Chronological allocation (D1): events draw on each part's pool in start-date order.
    A pool ledger for every contended part (demanded by 2+ events). The allocated view is what the gate decides on.</p>`;
  for (const [pid, led] of Object.entries(DATA.allocation_ledgers)){
    h += `<div class="card"><b>${pid} — ${esc(led.part_name)}</b>
      <span class="small"> · pool at start: ${esc(JSON.stringify(led.pool_initial.stock))} · remaining: ${esc(JSON.stringify(led.pool_remaining.stock))}</span>
      <table><tr><th>Event</th><th>Starts</th><th>Single-line</th><th>Allocated</th><th>Short</th><th>Contention</th></tr>
      ${led.rows.map(r=>`<tr><td>${r.event_id}</td><td>${r.event_start}</td><td>${r.v1_status}</td><td>${r.allocated_status}</td><td>${r.allocated_shortage_qty||""}</td><td>${r.contention}</td></tr>`).join("")}
      </table></div>`;
  }
  w.innerHTML = h;
}
function renderWatch(){
  const w = document.getElementById("view-watch");
  const lines = [];
  for (const e of DATA.events) for (const l of e.lines) if (l.watchlist_tier!=="NONE")
    lines.push({e, l});
  const a = lines.filter(x=>x.l.watchlist_tier==="ORDER_BY_CLOSING");
  const b = lines.filter(x=>x.l.watchlist_tier==="NO_ORDERING_FALLBACK");
  let h = `<div class="card"><b>Tier A — act now (${a.length})</b><p class="small">Order-by date within 21 days or just passed, line covered. A decision is required: place the order, or acknowledge the lapse.</p>
    ${a.map(x=>`<p>${x.e.event_id}/${x.l.part_id} — ${esc(x.l.part_name)} · order-by ${x.l.order_by_date} · status ${x.l.allocated_status}</p>`).join("")}</div>
    <div class="card"><b>Tier B — no ordering fallback (${b.length})</b><p class="small">Order-by date passed with no counting PO. No action of its own; decided under the line's status row, shown as context.</p>
    ${b.map(x=>`<p>${x.e.event_id}/${x.l.part_id} — ${esc(x.l.part_name)} · order-by ${x.l.order_by_date} · status ${x.l.allocated_status}</p>`).join("")}</div>`;
  w.innerHTML = h;
}
function renderHorizon(){
  const w = document.getElementById("view-horizon");
  let h = `<p class="small">Forward events (D5 annex) on the two clocks. Clock 1 warns procurement (order-by);
    Clock 2 warns on coverage/customer risk for long-lead lines, with scheduled reviews at 6 and 3 months.
    The two clocks are never merged into one state.</p>`;
  for (const e of DATA.forward_events){
    h += `<div class="card"><b>${e.event_id} — ${esc(e.event_name)}</b> <span class="small">${esc(e.tail)} · ${e.start} → ${e.end}</span>`;
    for (const l of e.lines){
      h += `<p style="margin:8px 0 2px"><b>${l.part_id} — ${esc(l.part_name)}</b>
        <span class="status ${l.allocated_status}">${l.allocated_status.replaceAll("_"," ")}</span></p><div>${badges(l)}</div>`;
      if (l.clock2.applicable) h += `<p class="small">Clock 2 reviews: 6-month ${l.clock2.review_points["6-month"]} · 3-month ${l.clock2.review_points["3-month"]}${l.clock2.reviews_due.length?` · DUE NOW: ${l.clock2.reviews_due.join(", ")}`:""}</p>`;
    }
    h += `</div>`;
  }
  w.innerHTML = h;
}
function renderLog(){
  const rows = Object.values(DEC).sort((x,y)=>x.decided_at<y.decided_at?-1:1);
  document.getElementById("logrows").innerHTML = rows.length
    ? rows.map(d=>`${esc(d.decided_at)} — ${d.event_id}/${d.part_id}: <b>${esc(labelFor(d))}</b> (${esc(d.decision||"notification/procurement record")})`
        + (d.recovery_path?` · recovery: ${esc(d.recovery_path)}`:"")
        + (d.notification?` · notification recorded${d.notification.released?" (released, verifications recorded)":""}`:"")
        + (d.procurement_decision?` · procurement: ${esc(LABELS[d.procurement_decision]||d.procurement_decision)}`:"")).join("<br>")
    : "No decisions yet.";
}
refresh();
</script></body></html>
"""
