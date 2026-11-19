"""Command-line entry point for the npm dependency graph tool."""

import argparse
import sys
from pathlib import Path

from dependency_graph.config import ConfigError, load_config
from dependency_graph.registry import RegistryError, direct_dependencies


def main(argv=None):
    """Read settings and show the package's direct dependencies."""
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

    if config.test_mode:
        print("Тестовый репозиторий будет добавлен на этапе 3", file=sys.stderr)
        return 2
    try:
        dependencies = direct_dependencies(config.repository, config.package)
    except RegistryError as error:
        print(f"Ошибка репозитория: {error}", file=sys.stderr)
        return 1

    print(f"Прямые зависимости {config.package} (версия latest):")
    if not dependencies:
        print("(нет зависимостей)")
    for name, version_range in dependencies.items():
        print(f"{name}: {version_range}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
