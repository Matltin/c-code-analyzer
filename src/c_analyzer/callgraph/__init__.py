"""Project call-graph construction, queries, and stable outputs."""

from c_analyzer.callgraph.builder import build_call_graph
from c_analyzer.callgraph.model import (
    CallGraph,
    CallGraphEdge,
    CallGraphNode,
    callgraph_to_dot,
    callgraph_to_json,
    callgraph_to_text,
)

__all__ = [
    "CallGraph",
    "CallGraphEdge",
    "CallGraphNode",
    "build_call_graph",
    "callgraph_to_dot",
    "callgraph_to_json",
    "callgraph_to_text",
]

