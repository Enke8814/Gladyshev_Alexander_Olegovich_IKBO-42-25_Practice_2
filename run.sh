#!/usr/bin/env bash
# Запуск приложения или модульных тестов.
set -euo pipefail
cd "$(dirname "$0")"

if [[ "${1:-}" == "test" ]]; then
    exec python3 -m unittest discover -s tests -v
fi

exec python3 src/main.py "$@"
