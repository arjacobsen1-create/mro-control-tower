#!/usr/bin/env python3
"""
Tools exposed to the Claude agent. Every tool is read-only. Quantities come
only from availability.py (code), grounding only from retrieval.py (index).
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ingest"))
import availability  # noqa: E402
import allocation, horizon, slippage, watchlist  # noqa: E402  (V2 rule-engine layer)
from retrieval import search_notes  # noqa: E402

TOOL_SCHEMAS = [
    {"name": "get_event",
     "description": "Get one scheduled maintenance event (site, dates, check type).",
     "input_schema": {"type": "object", "properties": {"event_id": {"type": "string"}}, "required": ["event_id"]}},
    {"name": "get_demand",
     "description": "List the parts and quantities required by one event.",
     "input_schema": {"type": "object", "properties": {"event_id": {"type": "string"}}, "required": ["event_id"]}},
    {"name": "get_part",
     "description": "Get part master data: description, criticality, lead time, approved alternate part.",
     "input_schema": {"type": "object", "properties": {"part_id": {"type": "string"}}, "required": ["part_id"]}},
    {"name": "check_availability",
     "description": "Compute the coverage breakdown for one (event, part) demand line using the documented "
                    "availability rule. This is the ONLY source of quantities and status. Always call it "
                    "before stating any status or number.",
     "input_schema": {"type": "object", "properties": {"event_id": {"type": "string"}, "part_id": {"type": "string"}},
                      "required": ["event_id", "part_id"]}},
    {"name": "search_knowledge",
     "description": "Search the MRO policy/procedure/interchangeability knowledge notes. Use to ground any "
                    "recommendation (alternates, transfers, escalation, PO coverage, insufficient data). "
                    "An empty result means no grounding exists: say so rather than inventing a rule.",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
]


# ---------------------------------------------------------------- V2 tools
# Four NEW read-only tools (Stage V2-4), alongside the five above. Every
# number they return is computed by the V2 rule-engine modules; the agent
# may state only what these tools return.
TOOL_SCHEMAS_V2 = TOOL_SCHEMAS + [
    {"name": "check_allocated_availability",
     "description": "Compute the CROSS-EVENT (allocated) coverage for one (event, part) demand line: "
                    "the physical pools are allocated to events in chronological order, so this shows "
                    "whether the line is still covered once competing events have drawn their share. "
                    "Returns the V1 single-line status AND allocated_status, allocated_shortage_qty, "
                    "contention class and the pool ledger. Use alongside check_availability.",
     "input_schema": {"type": "object", "properties": {"event_id": {"type": "string"}, "part_id": {"type": "string"}},
                      "required": ["event_id", "part_id"]}},
    {"name": "check_slippage_risk",
     "description": "Assess PO slippage risk for one (event, part) line. Returns slippage_tier "
                    "(SLIPPAGE_HIGH, SLIPPAGE_WATCH or NONE) and, per counted PO, slip_days, "
                    "margin_days, load_bearing and whether a repeat slip breaks coverage. Risk "
                    "belongs to the (line, PO) pair, never to the PO globally.",
     "input_schema": {"type": "object", "properties": {"event_id": {"type": "string"}, "part_id": {"type": "string"}},
                      "required": ["event_id", "part_id"]}},
    {"name": "check_watchlist",
     "description": "Order-by watchlist. With event_id and part_id: that line's watchlist_tier "
                    "(ORDER_BY_CLOSING, NO_ORDERING_FALLBACK or NONE) with its order-by dates. "
                    "Without arguments: the full watchlist with tier counts.",
     "input_schema": {"type": "object", "properties": {"event_id": {"type": "string"}, "part_id": {"type": "string"}},
                      "required": []}},
    {"name": "get_horizon",
     "description": "Two-clock horizon state for one (event, part) line: clock1 (order-by band: "
                    "passed, act-now, advisory or far), clock2 (event band for long-lead lines, "
                    "review points due), material-risk conditions, the procurement action with its "
                    "documented need (if raised), customer-notification eligibility with checkpoint "
                    "date, and recovery-lever feasibility for a short line. The clocks and the three "
                    "decision dimensions are separate fields; never merge them.",
     "input_schema": {"type": "object", "properties": {"event_id": {"type": "string"}, "part_id": {"type": "string"}},
                      "required": ["event_id", "part_id"]}},
]


def run_tool(name, args):
    if name == "get_event":
        return availability.get_event(args["event_id"]) or {"error": "unknown event"}
    if name == "get_demand":
        return {"event_id": args["event_id"], "lines": availability.get_demand(args["event_id"])}
    if name == "get_part":
        return availability.get_part(args["part_id"]) or {"error": "unknown part"}
    if name == "check_availability":
        return availability.check_availability(args["event_id"], args["part_id"])
    if name == "search_knowledge":
        return {"results": search_notes(args["query"], k=3)}
    if name == "check_allocated_availability":
        r = allocation.allocated_availability(args["event_id"], args["part_id"])
        if "error" in r:
            return r
        # Projected for the agent: the V1 detail already arrives via
        # check_availability; this tool's payload is the allocated view
        # itself (same computed values, no duplication).
        return {"event_id": r["event_id"], "part_id": r["part_id"],
                "v1_status": r["status"], "v1_shortage_qty": r["shortage_qty"],
                "allocated_status": r["allocated_status"],
                "allocated_shortage_qty": r["allocated_shortage_qty"],
                "contention": r["contention"],
                "allocation_policy": r["allocation_policy"],
                "pool_ledger": r["pool_ledger"],
                "pool_remaining": r["pool_remaining"]}
    if name == "check_slippage_risk":
        return slippage.slippage_risk(args["event_id"], args["part_id"])
    if name == "check_watchlist":
        if args.get("event_id") and args.get("part_id"):
            return watchlist.watchlist_line(args["event_id"], args["part_id"])
        full = watchlist.watchlist()
        return {"counts": full["counts"],
                "tier_a": [f"{w['event_id']}/{w['part_id']}" for w in full["tier_a"]],
                "tier_b": [f"{w['event_id']}/{w['part_id']}" for w in full["tier_b"]]}
    if name == "get_horizon":
        return horizon.horizon_line(args["event_id"], args["part_id"])
    return {"error": f"unknown tool {name}"}
