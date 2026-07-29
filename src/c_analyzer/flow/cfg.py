"""Control-flow graph models, validation, and deterministic renderers."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import json

from c_analyzer.ast import ASTNode
from c_analyzer.core import SourceSpan


class EdgeKind(Enum):
    FALLTHROUGH = "fallthrough"
    TRUE_BRANCH = "true_branch"
    FALSE_BRANCH = "false_branch"
    LOOP_BACK = "loop_back"
    BREAK = "break"
    CONTINUE = "continue"
    RETURN = "return"


@dataclass(frozen=True, slots=True)
class CFGEdge:
    source: str
    target: str
    kind: EdgeKind


@dataclass(slots=True)
class BasicBlock:
    id: str
    nodes: list[ASTNode]
    span: SourceSpan
    predecessors: list[str] = field(default_factory=list)
    successors: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ControlFlowGraph:
    function_symbol_id: str
    entry_block: str
    exit_block: str
    blocks: tuple[BasicBlock, ...]
    edges: tuple[CFGEdge, ...]

    def block(self, block_id: str) -> BasicBlock:
        for block in self.blocks:
            if block.id == block_id:
                return block
        raise KeyError(block_id)

    def reachable_blocks(self) -> frozenset[str]:
        known = {block.id for block in self.blocks}
        if self.entry_block not in known:
            return frozenset()
        reachable: set[str] = set()
        pending = [self.entry_block]
        while pending:
            block_id = pending.pop(0)
            if block_id in reachable:
                continue
            reachable.add(block_id)
            pending.extend(
                edge.target
                for edge in self.edges
                if edge.source == block_id
                and edge.target in known
                and edge.target not in reachable
            )
        return frozenset(reachable)

    def to_dict(self) -> dict[str, object]:
        reachable = self.reachable_blocks()
        return {
            "function_symbol_id": self.function_symbol_id,
            "entry_block": self.entry_block,
            "exit_block": self.exit_block,
            "blocks": [
                {
                    "id": block.id,
                    "nodes": [type(node).__name__ for node in block.nodes],
                    "span": {
                        "file": block.span.start.file,
                        "line": block.span.start.line,
                        "column": block.span.start.column,
                        "length": block.span.length,
                    },
                    "predecessors": list(block.predecessors),
                    "successors": list(block.successors),
                    "reachable": block.id in reachable,
                }
                for block in self.blocks
            ],
            "edges": [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "kind": edge.kind.value,
                }
                for edge in self.edges
            ],
        }


def validate_cfg(cfg: ControlFlowGraph) -> tuple[str, ...]:
    errors: list[str] = []
    ids = [block.id for block in cfg.blocks]
    known = set(ids)
    if len(ids) != len(known):
        errors.append("duplicate block id")
    if cfg.entry_block not in known:
        errors.append("missing entry block")
    if cfg.exit_block not in known:
        errors.append("missing exit block")
    if cfg.entry_block == cfg.exit_block:
        errors.append("entry and exit must be distinct")

    edges = {(edge.source, edge.target) for edge in cfg.edges}
    for edge in cfg.edges:
        if edge.source not in known or edge.target not in known:
            errors.append(f"edge references unknown block: {edge.source}->{edge.target}")
    for block in cfg.blocks:
        for successor in block.successors:
            if (block.id, successor) not in edges:
                errors.append(f"missing edge for successor: {block.id}->{successor}")
            if successor not in known:
                errors.append(
                    f"successor references unknown block: {block.id}->{successor}"
                )
            elif block.id not in cfg.block(successor).predecessors:
                errors.append(f"asymmetric successor: {block.id}->{successor}")
        for predecessor in block.predecessors:
            if (predecessor, block.id) not in edges:
                errors.append(f"missing edge for predecessor: {predecessor}->{block.id}")
            if predecessor not in known:
                errors.append(
                    f"predecessor references unknown block: {predecessor}->{block.id}"
                )
            elif block.id not in cfg.block(predecessor).successors:
                errors.append(f"asymmetric predecessor: {predecessor}->{block.id}")
    if cfg.entry_block in known:
        cfg.reachable_blocks()
    return tuple(dict.fromkeys(errors))


def cfg_to_text(cfg: ControlFlowGraph) -> str:
    reachable = cfg.reachable_blocks()
    lines = [
        f"CFG {cfg.function_symbol_id}",
        f"entry: {cfg.entry_block}",
        f"exit: {cfg.exit_block}",
    ]
    for block in cfg.blocks:
        nodes = ", ".join(type(node).__name__ for node in block.nodes) or "-"
        status = "reachable" if block.id in reachable else "unreachable"
        lines.append(f"{block.id} [{status}]: {nodes}")
    for edge in cfg.edges:
        lines.append(f"{edge.source} -{edge.kind.value}-> {edge.target}")
    return "\n".join(lines)


def cfg_to_json(cfg: ControlFlowGraph) -> str:
    return json.dumps(cfg.to_dict(), ensure_ascii=False, indent=2)


def cfg_to_dot(cfg: ControlFlowGraph) -> str:
    lines = ["digraph cfg {"]
    reachable = cfg.reachable_blocks()
    for block in cfg.blocks:
        nodes = "\\n".join(type(node).__name__ for node in block.nodes) or block.id
        style = "" if block.id in reachable else ', style="dashed"'
        lines.append(f'  "{block.id}" [label="{nodes}"{style}];')
    for edge in cfg.edges:
        lines.append(
            f'  "{edge.source}" -> "{edge.target}" '
            f'[label="{edge.kind.value}"];'
        )
    lines.append("}")
    return "\n".join(lines)
