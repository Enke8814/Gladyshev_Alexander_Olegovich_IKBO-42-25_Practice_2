"""Dependency-first loading order for the collected graph."""

from collections import deque

from dependency_graph.graph import GraphError


def dependency_order(graph):
    """Use Kahn's algorithm; reject cycles without inventing an order."""
    remaining = {name: len(edges) for name, edges in graph.edges.items()}
    parents = _parents(graph)
    ready = deque(sorted(name for name in remaining if not remaining[name]))
    result = []
    while ready:
        name = ready.popleft()
        result.append(name)
        for parent in sorted(parents[name]):
            remaining[parent] -= 1
            if not remaining[parent]:
                ready.append(parent)
    if len(result) != len(remaining):
        raise GraphError(
            "цикл: порядок «зависимости перед пакетом» невозможен"
        )
    return result


def _parents(graph):
    """Map every package to the packages that directly require it."""
    parents = {name: [] for name in graph.edges}
    for parent, children in graph.edges.items():
        for child in children:
            parents[child].append(parent)
    return parents
