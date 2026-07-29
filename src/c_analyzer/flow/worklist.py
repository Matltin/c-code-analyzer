"""Reusable deterministic fixed-point worklist solvers."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from c_analyzer.flow.cfg import ControlFlowGraph

State = frozenset[str]
Transfer = Callable[[str, State], State]
Meet = Callable[[tuple[State, ...]], State]


@dataclass(frozen=True, slots=True)
class WorklistResult:
    in_state: dict[str, State]
    out_state: dict[str, State]
    iterations: int


def solve_forward(
    cfg: ControlFlowGraph,
    *,
    entry_state: State,
    bottom: State,
    transfer: Transfer,
    meet: Meet,
) -> WorklistResult:
    """Solve a forward problem in stable block order until a fixed point."""
    in_state = {block.id: bottom for block in cfg.blocks}
    out_state = {block.id: bottom for block in cfg.blocks}
    in_state[cfg.entry_block] = entry_state
    order = [block.id for block in cfg.blocks]
    iterations = 0
    changed = True
    while changed:
        changed = False
        for block_id in order:
            iterations += 1
            block = cfg.block(block_id)
            incoming = (
                entry_state
                if block_id == cfg.entry_block
                else meet(tuple(out_state[item] for item in block.predecessors))
                if block.predecessors
                else bottom
            )
            outgoing = transfer(block_id, incoming)
            if incoming != in_state[block_id] or outgoing != out_state[block_id]:
                in_state[block_id] = incoming
                out_state[block_id] = outgoing
                changed = True
    return WorklistResult(in_state, out_state, iterations)


def solve_backward(
    cfg: ControlFlowGraph,
    *,
    exit_state: State,
    bottom: State,
    transfer: Transfer,
    meet: Meet,
) -> WorklistResult:
    """Solve a backward problem in stable reverse block order."""
    in_state = {block.id: bottom for block in cfg.blocks}
    out_state = {block.id: bottom for block in cfg.blocks}
    out_state[cfg.exit_block] = exit_state
    order = [block.id for block in reversed(cfg.blocks)]
    iterations = 0
    changed = True
    while changed:
        changed = False
        for block_id in order:
            iterations += 1
            block = cfg.block(block_id)
            outgoing = (
                exit_state
                if block_id == cfg.exit_block
                else meet(tuple(in_state[item] for item in block.successors))
                if block.successors
                else bottom
            )
            incoming = transfer(block_id, outgoing)
            if incoming != in_state[block_id] or outgoing != out_state[block_id]:
                in_state[block_id] = incoming
                out_state[block_id] = outgoing
                changed = True
    return WorklistResult(in_state, out_state, iterations)


def union_states(states: tuple[State, ...]) -> State:
    return frozenset().union(*states)


def intersect_states(states: tuple[State, ...]) -> State:
    if not states:
        return frozenset()
    result = set(states[0])
    for state in states[1:]:
        result.intersection_update(state)
    return frozenset(result)

