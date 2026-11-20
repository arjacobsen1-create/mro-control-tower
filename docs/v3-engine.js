/* ============================================================================
   MRO Control Tower — V3 scenario engine
   Scenario: "Promised to the Wrong Airplane" (see v3-scenario-spec-2026-11-19.md)

   Structure follows the architecture stack, bottom to top:
     1. DATA LAYER      — the fixed scenario dataset (module-private).
     2. CONTEXT LAYER   — the knowledge graph + semantics. The ONLY doorway
                          to the data. Agents call this, never the data.
     3. AGENT LAYER     — Scout, Stock, Dispatch. Each receives the context
                          object and nothing else (governed path).
     4. GUARDRAILS      — the gate rules (STATUS_ACTIONS + Gate.decide).
     5. HUMAN GATE      — the decision log the planner UI writes to.

   UMD: loads as a browser global (window.MRO_V3) and as a Node module
   (module.exports) so the acceptance tests run the exact code the page runs.
   ============================================================================ */
(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.MRO_V3 = api;
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  /* ============================ 1. DATA LAYER ============================
     Fixed scenario dataset. Small on purpose: every run tells the same
     story. Never exported directly; read it through the context layer
     (agents) or exportDataset() (documentation/tests only).            */
  const SCENARIO = {
    scenario_id: "V3-AOG-001",
    scenario_name: "Promised to the Wrong Airplane",
    reference_date: "2026-11-19",
    synthetic: true,
    part: {
      part_id: "P101",
      part_name: "Fuel metering unit",
      fits: ["FIN-214", "FIN-318"], // same fleet type
    },
    aircraft: [
      {
        aircraft_id: "FIN-214", short: "A", status: "AOG", // aircraft on ground
        situation: "Grounded awaiting parts",
        needs: { part_id: "P101", qty: 3, by_date: "2026-11-21", wait_days: 2 },
      },
      {
        aircraft_id: "FIN-318", short: "B", status: "PLANNED",
        situation: "C-check starts 2026-12-08",
        work_order: "WO-2207",
        needs: { part_id: "P101", qty: 3, by_date: "2026-12-14", wait_days: 25 },
      },
    ],
    stock: {
      part_id: "P101", site: "YUL-H1", qty_on_hand: 4,
      committed_to: "WO-2207", committed_qty: 4,
    },
    purchase_order: {
      po_id: "PO-3310", part_id: "P101", qty: 1, eta: "2026-12-10", lead_time_days: 21,
    },
    new_order: { lead_time_days: 21 },
    second_part: {
      part_id: "P102", part_name: "Ignition exciter", aircraft_id: "FIN-214",
      records: [
        { system: "Stores ledger", qty: 1 },
        { system: "Line maintenance count", qty: 3 },
      ],
    },
    gate_lines: [
      {
        line_id: "L-A", aircraft_id: "FIN-214", part_id: "P101",
        status: "COVERED_BY_TRANSFER",
        summary:
          "Move 3 of the 4 committed units from WO-2207 to Aircraft A. " +
          "A is covered in full and returns to service.",
        procurement_need: null,
      },
      {
        line_id: "L-B", aircraft_id: "FIN-318", part_id: "P101",
        status: "SHORT_UNCOVERED", shortage_qty: 1,
        summary:
          "After the move, Aircraft B is short 1 unit for WO-2207 " +
          "(2 of 3 covered: 1 remaining unit + PO-3310). The shortage is " +
          "real and uncovered; the gate cannot approve it away.",
        procurement_need: {
          action: "ORDER", qty: 1, part_id: "P101", order_by: "2026-11-23",
          basis:
            "Documented procurement need. Per the E006/P011 principle, a " +
            "covered line elsewhere never suppresses a documented need.",
        },
      },
      {
        line_id: "L-C", aircraft_id: "FIN-214", part_id: "P102",
        status: "INSUFFICIENT_DATA",
        summary:
          "P102 stock records disagree (stores ledger 1, line count 3). " +
          "Nobody can say what is actually on the shelf, so no approval " +
          "can rest on this line until it is physically counted.",
        procurement_need: null,
      },
    ],
  };

  /* ==================== 2. CONTEXT LAYER (the doorway) ====================
     Knowledge graph + semantics over the data layer. This is the single
     governed path: agents receive a context object and may only ask it
     questions. The raw dataset never leaves this layer.                  */
  function buildGraph(data) {
    const A = data.aircraft[0], B = data.aircraft[1];
    const nodes = [
      { id: A.aircraft_id, label: A.aircraft_id, sub: "Aircraft A · AOG", kind: "aircraft-a", x: 118, y: 64 },
      { id: data.part.part_id, label: data.part.part_id, sub: data.part.part_name, kind: "part", x: 380, y: 52 },
      { id: B.aircraft_id, label: B.aircraft_id, sub: "Aircraft B · planned", kind: "aircraft-b", x: 642, y: 64 },
      { id: "PO", label: data.purchase_order.po_id, sub: "1 unit · ETA 2026-12-10", kind: "po", x: 76, y: 196 },
      { id: "STOCK", label: "Stock · " + data.stock.site, sub: data.stock.qty_on_hand + " × " + data.part.part_id + " on hand", kind: "stock", x: 280, y: 258 },
      { id: "WO", label: B.work_order, sub: "B's C-check work order", kind: "wo", x: 516, y: 252 },
    ];
    const edges = [
      { id: "e-grounded", from: A.aircraft_id, to: data.part.part_id, label: "grounded pending" },
      { id: "e-fits-b", from: data.part.part_id, to: B.aircraft_id, label: "fits" },
      { id: "e-priority", from: A.aircraft_id, to: B.aircraft_id, label: "priority over (AOG > planned)" },
      { id: "e-po", from: "PO", to: "STOCK", label: "replenishes" },
      { id: "e-wo-b", from: "WO", to: B.aircraft_id, label: "belongs to" },
    ];
    // The commitment edge exists only while the stock is actually committed.
    if (data.stock.committed_to) {
      edges.push({ id: "e-committed", from: "STOCK", to: "WO", label: "committed to" });
    }
    return { nodes, edges };
  }

  function createContext(data) {
    const d = data || SCENARIO;
    const graph = buildGraph(d);
    const A = d.aircraft[0], B = d.aircraft[1];
    const hasEdge = (id) => graph.edges.some((e) => e.id === id);

    function coverage(unitsToA) {
      const toA = Math.max(0, Math.min(d.stock.qty_on_hand, unitsToA));
      const aPct = Math.round((Math.min(toA, A.needs.qty) / A.needs.qty) * 100);
      // For B, the PO unit counts: it lands 2026-12-10, before B's 2026-12-14 date.
      // For A it never counts: A's window is 2 days, the lead time is 21.
      const bUnits = d.stock.qty_on_hand - toA + d.purchase_order.qty;
      const bPct = Math.round((Math.min(bUnits, B.needs.qty) / B.needs.qty) * 100);
      return {
        unitsToA: toA,
        a: { pct: aPct, covered: Math.min(toA, A.needs.qty), needed: A.needs.qty },
        b: { pct: bPct, covered: Math.min(bUnits, B.needs.qty), needed: B.needs.qty, short: Math.max(0, B.needs.qty - bUnits) },
      };
    }

    return Object.freeze({
      /* --- graph rendering + reasoning paths --- */
      graphSnapshot() {
        return JSON.parse(JSON.stringify(graph));
      },
      /* --- Scout's question: who is grounded, pending what? --- */
      groundedAircraft() {
        if (!hasEdge("e-grounded")) return [];
        const freeStock = d.stock.qty_on_hand - (d.stock.committed_to ? d.stock.committed_qty : 0);
        return [{
          aircraft_id: A.aircraft_id, part_id: A.needs.part_id,
          qty_needed: A.needs.qty, by_date: A.needs.by_date, wait_days: A.needs.wait_days,
          available_now: freeStock,
          shortage_qty: Math.max(0, A.needs.qty - freeStock),
        }];
      },
      /* --- Stock's questions --- */
      commitmentsFor(partId) {
        if (partId !== d.part.part_id || !d.stock.committed_to) return [];
        return [{
          from_stock_site: d.stock.site, to_work_order: d.stock.committed_to,
          to_aircraft: B.aircraft_id, qty: d.stock.committed_qty,
        }];
      },
      alternativesFor(partId, forAircraft) {
        const committed = d.stock.committed_to != null;
        return [
          {
            type: committed ? "MOVE_COMMITMENT" : "ALLOCATE_STOCK", feasible: true,
            detail: committed
              ? "Move units from " + d.stock.committed_to + " to " + forAircraft + "."
              : "Stock is uncommitted; allocate units to " + forAircraft + " directly.",
          },
          {
            type: "EXPEDITE_PO", feasible: false,
            detail: "New-order lead time is " + d.new_order.lead_time_days + " days; " +
              forAircraft + " can wait " + A.needs.wait_days + ". Too slow to help A.",
          },
          {
            type: "CANNIBALISE", feasible: false, excluded: true,
            detail: "Out of scope by policy. Never offered.",
          },
        ];
      },
      /* --- Dispatch's questions --- */
      priorityWinner() {
        return hasEdge("e-priority") ? A.aircraft_id : null;
      },
      coverage,
      procurementNeedFor(aircraftId) {
        const line = d.gate_lines.find((l) => l.aircraft_id === aircraftId && l.procurement_need);
        return line ? JSON.parse(JSON.stringify(line.procurement_need)) : null;
      },
      /* --- the gate's question --- */
      lines() {
        return JSON.parse(JSON.stringify(d.gate_lines));
      },
      scenarioMeta() {
        return {
          scenario_id: d.scenario_id, scenario_name: d.scenario_name,
          reference_date: d.reference_date, synthetic: d.synthetic,
        };
      },
    });
  }

  /* ============================ 3. AGENT LAYER ============================
     Each agent receives ONLY the context object. No agent touches the
     data layer; that is the governed path, and the tests prove it.      */
  const Agents = {
    Scout: {
      id: "scout", name: "Scout", job: "Watches events. Detects the shortage and wakes the run.",
      run(ctx) {
        const grounded = ctx.groundedAircraft();
        const g = grounded[0];
        return {
          agent: "Scout",
          highlight: ["e-grounded", "e-priority"],
          message:
            "Event: " + g.aircraft_id + " is on the ground pending " + g.part_id + ". " +
            "It needs " + g.qty_needed + " by " + g.by_date + " and can wait " + g.wait_days +
            " days. Free stock available to it right now: " + g.available_now +
            ". Shortage: " + g.shortage_qty + ". Waking Stock.",
          finding: { type: "SHORTAGE_DETECTED", ...g },
        };
      },
    },
    Stock: {
      id: "stock", name: "Stock", job: "Reads the graph. Finds the commitment conflict and the alternatives.",
      run(ctx, event) {
        const commitments = ctx.commitmentsFor(event.finding.part_id);
        const alternatives = ctx.alternativesFor(event.finding.part_id, event.finding.aircraft_id);
        if (!commitments.length) {
          return {
            agent: "Stock",
            highlight: ["e-grounded"],
            message:
              "No commitment conflict: the stock is not promised to anyone. " +
              "Free stock can be allocated to " + event.finding.aircraft_id + " directly.",
            finding: { type: "FREE_STOCK", commitments, alternatives },
          };
        }
        const c = commitments[0];
        return {
          agent: "Stock",
          highlight: ["e-committed", "e-wo-b", "e-fits-b", "e-po"],
          message:
            "The stock exists, but all " + c.qty + " units at " + c.from_stock_site +
            " are committed to " + c.to_work_order + " for " + c.to_aircraft + ". " +
            "Expedite cannot help (21-day lead against a 2-day window) and " +
            "cannibalising is out of scope. One feasible lever: move the commitment.",
          finding: { type: "COMMITMENT_CONFLICT", commitments, alternatives },
        };
      },
    },
    Dispatch: {
      id: "dispatch", name: "Dispatch", job: "Builds the recommendation, with the cost stated plainly.",
      run(ctx, event, stockFinding) {
        const partId = event.finding.part_id;
        if (stockFinding.finding.type === "FREE_STOCK") {
          return {
            agent: "Dispatch",
            highlight: ["e-grounded"],
            message:
              "Recommendation: allocate " + event.finding.qty_needed + " units of " +
              partId + " to " + event.finding.aircraft_id + " from free stock. No cost to any other aircraft.",
            recommendation: {
              action: "ALLOCATE_STOCK", units: event.finding.qty_needed,
              to_aircraft: event.finding.aircraft_id, cost_to_b: "None — the stock was uncommitted.",
            },
          };
        }
        const need = ctx.procurementNeedFor("FIN-318");
        const cov = ctx.coverage(event.finding.qty_needed);
        return {
          agent: "Dispatch",
          highlight: ["e-committed", "e-wo-b", "e-grounded", "e-priority"],
          message:
            "Recommendation: move " + event.finding.qty_needed + " of the 4 committed units to " +
            event.finding.aircraft_id + " (AOG outranks planned work). Cost to Aircraft B, stated plainly: " +
            "B's coverage falls to " + cov.b.pct + "%, short " + cov.b.short + " unit for WO-2207. " +
            "A procurement need is raised for B: order " + need.qty + " × " + need.part_id +
            " by " + need.order_by + ". The decision itself belongs to the human at the gate.",
          recommendation: {
            action: "MOVE_COMMITMENT", units: event.finding.qty_needed,
            from_work_order: stockFinding.finding.commitments[0].to_work_order,
            to_aircraft: event.finding.aircraft_id,
            cost_to_b:
              "Aircraft B coverage falls to " + cov.b.pct + "% (short " + cov.b.short +
              " unit). Procurement need raised: order " + need.qty + " × " + need.part_id +
              " by " + need.order_by + ".",
          },
        };
      },
    },
  };

  function runScenario(ctx) {
    const s1 = Agents.Scout.run(ctx);
    const s2 = Agents.Stock.run(ctx, s1);
    const s3 = Agents.Dispatch.run(ctx, s1, s2);
    return { steps: [s1, s2, s3], recommendation: s3.recommendation };
  }

  /* ============================== 4. GUARDRAILS ==============================
     The standing gate rules, identical in spirit to planner_v2:
       - The decision is on the recommended action, never acceptance of a
         shortage: SHORT_UNCOVERED lines offer escalations only.
       - INSUFFICIENT_DATA lines offer investigation only.
       - Gate.decide refuses an approval on either status even if a caller
         asks for one directly (defence in depth: the UI hides the button,
         the engine refuses the call).                                     */
  const STATUS_ACTIONS = {
    OK: ["acknowledged"],
    COVERED_BY_PO: ["approve_monitor_po"],
    COVERED_BY_TRANSFER: ["approve_transfer"],
    COVERED_BY_ALTERNATE: ["approve_alternate"],
    SHORT_UNCOVERED: ["escalate_expedite", "escalate_defer"],
    INSUFFICIENT_DATA: ["escalate_investigate"],
  };
  const LABELS = {
    acknowledged: "Acknowledge — no action",
    approve_monitor_po: "Approve — monitor PO",
    approve_transfer: "Approve transfer",
    approve_alternate: "Approve alternate use",
    escalate_expedite: "Escalate — expedite / emergency source",
    escalate_defer: "Escalate — defer event",
    escalate_investigate: "Escalate — investigate / physical count",
    sent_back: "Send back for review",
    place_order: "Decide: place the order",
  };
  const BLOCKED_STATUSES = ["SHORT_UNCOVERED", "INSUFFICIENT_DATA"];

  function allowedPrimary(line) {
    return [...(STATUS_ACTIONS[line.status] || []), "sent_back"];
  }
  function isApproval(decision) {
    return typeof decision === "string" && decision.startsWith("approve");
  }

  const Gate = {
    STATUS_ACTIONS, LABELS, allowedPrimary, isApproval,
    decide(line, decision, opts) {
      opts = opts || {};
      if (isApproval(decision) && BLOCKED_STATUSES.includes(line.status)) {
        return {
          ok: false, refused: true,
          reason: "Gate rule: approval never applies to a " + line.status +
            " line. The decision is on the recommended action, never acceptance of a shortage.",
        };
      }
      if (!allowedPrimary(line).includes(decision)) {
        return {
          ok: false, refused: true,
          reason: "Decision '" + decision + "' is not an allowed action for a " +
            line.status + " line. Allowed: " + allowedPrimary(line).join(", ") + ".",
        };
      }
      return {
        ok: true,
        record: {
          line_id: line.line_id,
          decision,
          label: LABELS[decision] || decision,
          decided_at: new Date().toISOString(),
          status: line.status,
          // V2 pattern: a procurement decision is recorded alongside a
          // primary decision, and the need itself rides with the record.
          procurement_decision: opts.procurement_decision || null,
          procurement_need: opts.procurement_decision ? (line.procurement_need || null) : null,
        },
      };
    },
  };

  /* ============================== 5. HUMAN GATE ==============================
     The decision log. The planner UI persists these records (localStorage,
     key mro_planner_v3_decisions, following planner_v2); records can be
     changed or undone, and every record carries its timestamp.          */
  function createDecisionLog() {
    const records = new Map();
    return {
      decide(line, decision, opts) {
        const res = Gate.decide(line, decision, opts);
        if (res.ok) records.set(line.line_id, res.record);
        return res;
      },
      undo(lineId) { records.delete(lineId); },
      get(lineId) { return records.get(lineId) || null; },
      all() { return [...records.values()]; },
      count() { return records.size; },
    };
  }

  return {
    createContext,
    Agents,
    runScenario,
    Gate,
    createDecisionLog,
    // Documentation/tests only: agents never see this.
    exportDataset() { return JSON.parse(JSON.stringify(SCENARIO)); },
  };
});
