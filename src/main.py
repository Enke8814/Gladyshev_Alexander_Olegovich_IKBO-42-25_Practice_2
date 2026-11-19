"""Command-line entry point for the npm dependency graph tool."""

import argparse
import sys
from pathlib import Path

from dependency_graph.config import ConfigError, load_config


def main(argv=None):
    """Read XML configuration and print the stage-one settings."""
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

    for key, value in config.items():
        print(f"{key} = {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
