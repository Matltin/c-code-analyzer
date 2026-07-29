"""Deterministic project call-graph models and queries."""

from __future__ import annotations

from dataclasses import dataclass
import json

from c_analyzer.project import ProjectLocation


@dataclass(frozen=True, slots=True)
class CallGraphNode:
    symbol_id: str
    name: str
    kind: str
    definition: ProjectLocation | None


@dataclass(frozen=True, slots=True)
class CallGraphEdge:
    caller_symbol_id: str
    callee_symbol_id: str
    call_sites: tuple[ProjectLocation, ...]


@dataclass(frozen=True, slots=True)
class CallGraph:
    nodes: tuple[CallGraphNode, ...]
    edges: tuple[CallGraphEdge, ...]

    def node(self, symbol_id: str) -> CallGraphNode | None:
        return next(
            (item for item in self.nodes if item.symbol_id == symbol_id),
            None,
        )

    def symbol_id(self, name_or_id: str) -> str | None:
        if self.node(name_or_id) is not None:
            return name_or_id
        matches = [node.symbol_id for node in self.nodes if node.name == name_or_id]
        return matches[0] if len(matches) == 1 else None

    def direct_callees(self, name_or_id: str) -> tuple[CallGraphNode, ...]:
        symbol_id = self.symbol_id(name_or_id)
        if symbol_id is None:
            return ()
        ids = {
            edge.callee_symbol_id
            for edge in self.edges
            if edge.caller_symbol_id == symbol_id
        }
        return tuple(node for node in self.nodes if node.symbol_id in ids)

    def direct_callers(self, name_or_id: str) -> tuple[CallGraphNode, ...]:
        symbol_id = self.symbol_id(name_or_id)
        if symbol_id is None:
            return ()
        ids = {
            edge.caller_symbol_id
            for edge in self.edges
            if edge.callee_symbol_id == symbol_id
        }
        return tuple(node for node in self.nodes if node.symbol_id in ids)

    def reachable_callees(self, name_or_id: str) -> tuple[CallGraphNode, ...]:
        start = self.symbol_id(name_or_id)
        if start is None:
            return ()
        visited = _reachable(start, _adjacency(self.edges, reverse=False))
        visited.discard(start)
        return tuple(node for node in self.nodes if node.symbol_id in visited)

    def reaching_callers(self, name_or_id: str) -> tuple[CallGraphNode, ...]:
        start = self.symbol_id(name_or_id)
        if start is None:
            return ()
        visited = _reachable(start, _adjacency(self.edges, reverse=True))
        visited.discard(start)
        return tuple(node for node in self.nodes if node.symbol_id in visited)

    def strongly_connected_components(self) -> tuple[tuple[str, ...], ...]:
        """Return stable Tarjan SCCs."""
        adjacency = _adjacency(self.edges, reverse=False)
        for node in self.nodes:
            adjacency.setdefault(node.symbol_id, ())
        index = 0
        stack: list[str] = []
        on_stack: set[str] = set()
        indices: dict[str, int] = {}
        lowlinks: dict[str, int] = {}
        components: list[tuple[str, ...]] = []

        def strong_connect(node: str) -> None:
            nonlocal index
            indices[node] = index
            lowlinks[node] = index
            index += 1
            stack.append(node)
            on_stack.add(node)
            for neighbor in adjacency[node]:
                if neighbor not in indices:
                    strong_connect(neighbor)
                    lowlinks[node] = min(lowlinks[node], lowlinks[neighbor])
                elif neighbor in on_stack:
                    lowlinks[node] = min(lowlinks[node], indices[neighbor])
            if lowlinks[node] == indices[node]:
                members: list[str] = []
                while True:
                    member = stack.pop()
                    on_stack.remove(member)
                    members.append(member)
                    if member == node:
                        break
                components.append(tuple(sorted(members)))

        for node in (item.symbol_id for item in self.nodes):
            if node not in indices:
                strong_connect(node)
        return tuple(sorted(components, key=lambda item: item[0]))

    def recursive_components(self) -> tuple[tuple[str, ...], ...]:
        self_edges = {
            edge.caller_symbol_id
            for edge in self.edges
            if edge.caller_symbol_id == edge.callee_symbol_id
        }
        return tuple(
            component
            for component in self.strongly_connected_components()
            if len(component) > 1 or component[0] in self_edges
        )

    def dead_functions(self, entry: str = "main") -> tuple[CallGraphNode, ...]:
        entry_id = self.symbol_id(entry)
        if entry_id is None:
            return ()
        reachable = _reachable(entry_id, _adjacency(self.edges, reverse=False))
        return tuple(
            node
            for node in self.nodes
            if node.kind == "defined" and node.symbol_id not in reachable
        )

    def to_dict(self, *, entry: str = "main") -> dict[str, object]:
        entry_id = self.symbol_id(entry)
        recursive = set(self.recursive_components())
        return {
            "entry": entry,
            "entry_symbol_id": entry_id,
            "entry_found": entry_id is not None,
            "nodes": [
                {
                    "symbol_id": node.symbol_id,
                    "name": node.name,
                    "kind": node.kind,
                    "definition": (
                        node.definition.to_dict()
                        if node.definition is not None
                        else None
                    ),
                }
                for node in self.nodes
            ],
            "edges": [
                {
                    "caller": edge.caller_symbol_id,
                    "callee": edge.callee_symbol_id,
                    "call_sites": [
                        site.to_dict() for site in edge.call_sites
                    ],
                }
                for edge in self.edges
            ],
            "strongly_connected_components": [
                list(component)
                for component in self.strongly_connected_components()
            ],
            "recursive_components": [
                list(component) for component in self.recursive_components()
            ],
            "dead_functions": [
                node.symbol_id for node in self.dead_functions(entry)
            ],
        }


def _adjacency(
    edges: tuple[CallGraphEdge, ...],
    *,
    reverse: bool,
) -> dict[str, tuple[str, ...]]:
    values: dict[str, set[str]] = {}
    for edge in edges:
        source = edge.callee_symbol_id if reverse else edge.caller_symbol_id
        target = edge.caller_symbol_id if reverse else edge.callee_symbol_id
        values.setdefault(source, set()).add(target)
    return {key: tuple(sorted(items)) for key, items in values.items()}


def _reachable(start: str, adjacency: dict[str, tuple[str, ...]]) -> set[str]:
    visited: set[str] = set()
    pending = [start]
    while pending:
        node = pending.pop(0)
        if node in visited:
            continue
        visited.add(node)
        pending.extend(
            item for item in adjacency.get(node, ()) if item not in visited
        )
    return visited


def callgraph_to_text(graph: CallGraph, *, entry: str = "main") -> str:
    entry_id = graph.symbol_id(entry)
    lines = [
        f"Call graph (entry: {entry})",
        f"entry: {entry_id if entry_id is not None else 'not found'}",
    ]
    for node in graph.nodes:
        lines.append(f"{node.symbol_id} {node.kind} {node.name}")
    for edge in graph.edges:
        lines.append(
            f"{edge.caller_symbol_id} -> {edge.callee_symbol_id} "
            f"[sites={len(edge.call_sites)}]"
        )
    for component in graph.recursive_components():
        lines.append(f"recursive: {', '.join(component)}")
    for node in graph.dead_functions(entry):
        lines.append(f"dead: {node.symbol_id} {node.name}")
    return "\n".join(lines)


def callgraph_to_json(graph: CallGraph, *, entry: str = "main") -> str:
    return json.dumps(graph.to_dict(entry=entry), ensure_ascii=False, indent=2)


def callgraph_to_dot(graph: CallGraph) -> str:
    lines = ["digraph callgraph {"]
    for node in graph.nodes:
        lines.append(
            f'  "{node.symbol_id}" [label="{node.name}", shape="box"];'
        )
    for edge in graph.edges:
        lines.append(
            f'  "{edge.caller_symbol_id}" -> "{edge.callee_symbol_id}" '
            f'[label="{len(edge.call_sites)}"];'
        )
    lines.append("}")
    return "\n".join(lines)

