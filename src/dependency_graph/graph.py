"""Breadth-first traversal of npm or test dependency repositories."""

from collections import deque
from dataclasses import dataclass
import json
from pathlib import Path
import re

from dependency_graph.registry import direct_dependencies


TEST_NAME = re.compile(r"[A-Z]+")


class GraphError(ValueError):
    """The test repository is unreadable or has an invalid graph."""


@dataclass
class Graph:
    """Reachable packages, their direct edges, and shortest root distances."""

    edges: dict[str, dict[str, str]]
    depths: dict[str, int]
    load_order: tuple[str, ...]


def load_test_repository(path):
    """Read a JSON adjacency list of upper-case package names."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        raise GraphError(
            f"не удалось прочитать тестовый репозиторий: {error}"
        ) from error
    if not isinstance(data, dict):
        raise GraphError("тестовый репозиторий должен быть JSON-объектом")
    result = {}
    for name, dependencies in data.items():
        if not TEST_NAME.fullmatch(name):
            raise GraphError(f"неверное имя тестового пакета: {name}")
        if not isinstance(dependencies, list):
            raise GraphError(f"зависимости {name} должны быть списком")
        if any(not isinstance(dep, str) or not TEST_NAME.fullmatch(dep)
               for dep in dependencies):
            raise GraphError(f"неверное имя зависимости пакета {name}")
        if len(dependencies) != len(set(dependencies)):
            raise GraphError(f"повторная зависимость пакета {name}")
        result[name] = {dep: "" for dep in dependencies}
    return result


def build_graph(root, max_depth, dependencies_for):
    """Collect reachable edges with an iterative breadth-first search."""
    depths = {root: 0}
    edges = {}
    load_order = []
    queue = deque([root])
    while queue:
        package = queue.popleft()
        load_order.append(package)
        depth = depths[package]
        if depth == max_depth:
            edges[package] = {}
            continue
        dependencies = dependencies_for(package)
        edges[package] = dict(sorted(dependencies.items()))
        for child in edges[package]:
            if child not in depths:
                depths[child] = depth + 1
                queue.append(child)
    return Graph(edges, depths, tuple(load_order))


def graph_from_config(config):
    """Select the local test graph or npm registry as the edge source."""
    if config.test_mode:
        repository = load_test_repository(config.repository)
        if config.package not in repository:
            raise GraphError(f"пакет {config.package} отсутствует в файле")
        provider = lambda package: repository.get(package, {})
    else:
        provider = lambda package: direct_dependencies(
            config.repository, package
        )
    return build_graph(config.package, config.max_depth, provider)


def format_graph(graph):
    """Display packages by BFS distance and their collected edges."""
    lines = []
    for name in sorted(graph.depths, key=lambda key: (graph.depths[key], key)):
        dependencies = graph.edges[name]
        children = ", ".join(
            f"{child} ({spec})" if spec else child
            for child, spec in dependencies.items()
        )
        lines.append(f"{name} [глубина {graph.depths[name]}]: "
                     f"{children or '(нет зависимостей в пределах глубины)'}")
    return "\n".join(lines)
