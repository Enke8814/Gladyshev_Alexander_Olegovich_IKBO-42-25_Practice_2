"""Command-line entry point for the npm dependency graph tool."""

import argparse
import sys
from pathlib import Path

from dependency_graph.config import ConfigError, load_config
from dependency_graph.graph import GraphError, format_graph, graph_from_config
from dependency_graph.registry import RegistryError


def main(argv=None):
    """Read settings and print the reachable dependency graph."""
    parser = argparse.ArgumentParser(
        description="Визуализация зависимостей npm (вариант 7)"
    )
    parser.add_argument(
        "--config", type=Path, default=Path("config.example.xml"),
        help="путь к XML-файлу конфигурации",
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

    print(f"Граф зависимостей {config.package} "
          f"(максимальная глубина {config.max_depth}):")
    print(format_graph(graph))
    return 0


if __name__ == "__main__":
    sys.exit(main())
