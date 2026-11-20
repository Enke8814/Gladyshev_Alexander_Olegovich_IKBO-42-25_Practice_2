"""Command-line entry point for the npm dependency graph tool."""

import argparse
import sys
from pathlib import Path

from dependency_graph.config import ConfigError, load_config
from dependency_graph.graph import GraphError, graph_from_config
from dependency_graph.registry import RegistryError
from dependency_graph.render import RenderError, save_svg, to_dot
from dependency_graph.order import dependency_order


def display_result(config, graph, load_order):
    """Print an order report or emit reusable DOT and render SVG."""
    if load_order:
        names = dependency_order(graph)
        print("Порядок в пределах заданной глубины (зависимости первыми):")
        print(" -> ".join(names))
        return
    source = to_dot(graph)
    save_svg(source, config.output)
    print(source, end="")
    print(f"SVG сохранён: {config.output}", file=sys.stderr)


def main(argv=None):
    """Read settings and print the reachable dependency graph."""
    parser = argparse.ArgumentParser(
        description="Визуализация зависимостей npm (вариант 7)"
    )
    parser.add_argument(
        "--config", type=Path, default=Path("config.example.xml"),
        help="путь к XML-файлу конфигурации",
    )
    parser.add_argument(
        "--load-order", action="store_true",
        help="показать порядок загрузки: зависимости перед пакетом",
    )
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
    except ConfigError as error:
        print(f"Ошибка конфигурации: {error}", file=sys.stderr)
        return 2

    try:
        graph = graph_from_config(config)
    except (RegistryError, GraphError) as error:
        print(f"Ошибка репозитория: {error}", file=sys.stderr)
        return 1

    try:
        display_result(config, graph, args.load_order)
    except (RenderError, GraphError) as error:
        print(f"Ошибка результата: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
