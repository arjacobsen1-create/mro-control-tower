#!/usr/bin/env python3
"""
Tools exposed to the Claude agent. Every tool is read-only. Quantities come
only from availability.py (code), grounding only from retrieval.py (index).
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ingest"))
import availability  # noqa: E402
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
    return {"error": f"unknown tool {name}"}
