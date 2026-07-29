"""Structured, deterministic CFG construction from the Phase 1 AST."""

from __future__ import annotations

from dataclasses import dataclass

from c_analyzer.ast import (
    BlockStmt,
    BreakStmt,
    ContinueStmt,
    Declaration,
    EmptyStmt,
    ExprStmt,
    ForStmt,
    FunctionDecl,
    IfStmt,
    ReturnStmt,
    Statement,
    VarDecl,
    WhileStmt,
)
from c_analyzer.core import SourceSpan
from c_analyzer.flow.cfg import BasicBlock, CFGEdge, ControlFlowGraph, EdgeKind


@dataclass(frozen=True, slots=True)
class _Target:
    block_id: str
    edge_kind: EdgeKind


@dataclass(frozen=True, slots=True)
class _LoopContext:
    break_target: str
    continue_target: str


class CFGBuilder:
    def __init__(self, function: FunctionDecl, function_symbol_id: str) -> None:
        self._function = function
        self._function_symbol_id = function_symbol_id
        self._blocks: list[BasicBlock] = []
        self._by_id: dict[str, BasicBlock] = {}
        self._edges: list[CFGEdge] = []
        self._next_block = 0
        self._linear_blocks: set[str] = set()

    def build(self) -> ControlFlowGraph:
        entry = self._new_block([], _zero_at(self._function.span.start))
        exit_ = self._new_block([], _zero_at(self._function.span.end))
        body_entry = self._build_sequence(
            self._function.body.items,
            _Target(exit_.id, EdgeKind.FALLTHROUGH),
            None,
        )
        self._add_edge(entry.id, body_entry, EdgeKind.FALLTHROUGH)
        self._populate_neighbors()
        return ControlFlowGraph(
            function_symbol_id=self._function_symbol_id,
            entry_block=entry.id,
            exit_block=exit_.id,
            blocks=tuple(self._blocks),
            edges=tuple(
                sorted(
                    self._edges,
                    key=lambda edge: (
                        _block_number(edge.source),
                        _block_number(edge.target),
                        edge.kind.value,
                    ),
                )
            ),
        )

    def _build_sequence(
        self,
        items: list[Declaration | Statement],
        next_target: _Target,
        loop: _LoopContext | None,
    ) -> str:
        current = next_target
        for item in reversed(items):
            entry = self._build_item(item, current, loop)
            current = _Target(entry, EdgeKind.FALLTHROUGH)
        return current.block_id

    def _build_item(
        self,
        item: Declaration | Statement,
        next_target: _Target,
        loop: _LoopContext | None,
    ) -> str:
        if isinstance(item, BlockStmt):
            return self._build_sequence(item.items, next_target, loop)
        if isinstance(item, IfStmt):
            then_entry = self._build_item(item.then_branch, next_target, loop)
            else_entry = (
                self._build_item(item.else_branch, next_target, loop)
                if item.else_branch is not None
                else next_target.block_id
            )
            condition = self._new_block([item.condition], item.condition.span)
            self._add_edge(condition.id, then_entry, EdgeKind.TRUE_BRANCH)
            self._add_edge(condition.id, else_entry, EdgeKind.FALSE_BRANCH)
            return condition.id
        if isinstance(item, WhileStmt):
            condition = self._new_block([item.condition], item.condition.span)
            body_entry = self._build_item(
                item.body,
                _Target(condition.id, EdgeKind.LOOP_BACK),
                _LoopContext(
                    break_target=next_target.block_id,
                    continue_target=condition.id,
                ),
            )
            self._add_edge(condition.id, body_entry, EdgeKind.TRUE_BRANCH)
            self._add_edge(
                condition.id,
                next_target.block_id,
                EdgeKind.FALSE_BRANCH,
            )
            return condition.id
        if isinstance(item, ForStmt):
            condition_node = item.condition or item
            condition = self._new_block([condition_node], condition_node.span)
            continue_target = condition.id
            if item.update is not None:
                update = self._new_block([item.update], item.update.span)
                # Keep the for-update as a boundary: it appears before the body
                # in source order, even though control reaches it after the body.
                self._add_edge(update.id, condition.id, EdgeKind.LOOP_BACK)
                continue_target = update.id
            body_entry = self._build_item(
                item.body,
                _Target(continue_target, EdgeKind.FALLTHROUGH),
                _LoopContext(
                    break_target=next_target.block_id,
                    continue_target=continue_target,
                ),
            )
            self._add_edge(condition.id, body_entry, EdgeKind.TRUE_BRANCH)
            self._add_edge(
                condition.id,
                next_target.block_id,
                EdgeKind.FALSE_BRANCH,
            )
            if item.initializer is None:
                return condition.id
            initializer = self._new_block(
                [item.initializer],
                item.initializer.span,
            )
            self._linear_blocks.add(initializer.id)
            self._add_edge(initializer.id, condition.id, EdgeKind.FALLTHROUGH)
            return initializer.id
        if isinstance(item, ReturnStmt):
            block = self._new_block([item], item.span)
            self._add_edge(block.id, self._exit_id, EdgeKind.RETURN)
            return block.id
        if isinstance(item, BreakStmt):
            block = self._new_block([item], item.span)
            if loop is not None:
                self._add_edge(block.id, loop.break_target, EdgeKind.BREAK)
            return block.id
        if isinstance(item, ContinueStmt):
            block = self._new_block([item], item.span)
            if loop is not None:
                self._add_edge(block.id, loop.continue_target, EdgeKind.CONTINUE)
            return block.id
        if isinstance(item, (VarDecl, ExprStmt, EmptyStmt)):
            return self._prepend_linear(item, next_target)

        block = self._new_block([item], item.span)
        self._add_edge(block.id, next_target.block_id, next_target.edge_kind)
        return block.id

    @property
    def _exit_id(self) -> str:
        return self._blocks[1].id

    def _prepend_linear(self, item, next_target: _Target) -> str:
        if (
            next_target.edge_kind is EdgeKind.FALLTHROUGH
            and next_target.block_id in self._linear_blocks
        ):
            block = self._by_id[next_target.block_id]
            block.nodes.insert(0, item)
            block.span = SourceSpan(start=item.span.start, end=block.span.end)
            return block.id
        block = self._new_block([item], item.span)
        self._linear_blocks.add(block.id)
        self._add_edge(block.id, next_target.block_id, next_target.edge_kind)
        return block.id

    def _new_block(self, nodes, span: SourceSpan) -> BasicBlock:
        block = BasicBlock(
            id=f"block-{self._next_block:04d}",
            nodes=list(nodes),
            span=span,
        )
        self._next_block += 1
        self._blocks.append(block)
        self._by_id[block.id] = block
        return block

    def _add_edge(self, source: str, target: str, kind: EdgeKind) -> None:
        edge = CFGEdge(source=source, target=target, kind=kind)
        if edge not in self._edges:
            self._edges.append(edge)

    def _populate_neighbors(self) -> None:
        for edge in self._edges:
            source = self._by_id[edge.source]
            target = self._by_id[edge.target]
            if edge.target not in source.successors:
                source.successors.append(edge.target)
            if edge.source not in target.predecessors:
                target.predecessors.append(edge.source)
        for block in self._blocks:
            block.predecessors.sort(key=_block_number)
            block.successors.sort(key=_block_number)


def _block_number(block_id: str) -> int:
    return int(block_id.rsplit("-", 1)[-1])


def _zero_at(position) -> SourceSpan:
    return SourceSpan(start=position, end=position)


def build_cfg(
    function: FunctionDecl,
    function_symbol_id: str,
) -> ControlFlowGraph:
    return CFGBuilder(function, function_symbol_id).build()
