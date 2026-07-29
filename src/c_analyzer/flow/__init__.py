"""Control-flow graph construction, validation, and output."""

from c_analyzer.flow.builder import CFGBuilder, build_cfg
from c_analyzer.flow.cfg import (
    BasicBlock,
    CFGEdge,
    ControlFlowGraph,
    EdgeKind,
    cfg_to_dot,
    cfg_to_json,
    cfg_to_text,
    validate_cfg,
)
from c_analyzer.flow.dataflow import (
    CodeFinding,
    DataFlowResult,
    DeadCodeReport,
    analyze_dataflow,
    render_dataflow,
    render_dead_code,
)
from c_analyzer.flow.worklist import (
    WorklistResult,
    intersect_states,
    solve_backward,
    solve_forward,
    union_states,
)

__all__ = [
    "BasicBlock",
    "CFGBuilder",
    "CFGEdge",
    "CodeFinding",
    "ControlFlowGraph",
    "DataFlowResult",
    "DeadCodeReport",
    "EdgeKind",
    "WorklistResult",
    "analyze_dataflow",
    "build_cfg",
    "cfg_to_dot",
    "cfg_to_json",
    "cfg_to_text",
    "intersect_states",
    "render_dataflow",
    "render_dead_code",
    "solve_backward",
    "solve_forward",
    "union_states",
    "validate_cfg",
]
