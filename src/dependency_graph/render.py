"""Graphviz DOT generation and SVG rendering."""

import json
import subprocess


class RenderError(RuntimeError):
    """Graphviz could not create the requested image."""


def _quote(value):
    """Escape a DOT string using JSON's compatible string syntax."""
    return json.dumps(value, ensure_ascii=False)


def to_dot(graph):
    """Describe every visited node and dependency edge in Graphviz DOT."""
    lines = [
        "digraph npm_dependencies {",
        "  graph [rankdir=LR, bgcolor=transparent, "
        "nodesep=0.32, ranksep=0.9];",
        '  node [shape=box, style="rounded,filled", '
        'fillcolor="#EAF3FF", color="#3973B9", '
        'fontname="DejaVu Sans", fontsize=12, margin="0.18,0.12"];',
        '  edge [color="#64748B", fontname="DejaVu Sans", '
        'fontsize=10];',
    ]
    for name in graph.load_order:
        label = f"{name}\nглубина {graph.depths[name]}"
        style = (
            ', fillcolor="#1D4ED8", fontcolor="white"'
            if graph.depths[name] == 0 else ""
        )
        lines.append(f"  {_quote(name)} [label={_quote(label)}{style}];")
    for parent in graph.load_order:
        for child, version in graph.edges[parent].items():
            label = f" [label={_quote(version)}]" if version else ""
            lines.append(f"  {_quote(parent)} -> {_quote(child)}{label};")
    lines.append("}")
    return "\n".join(lines) + "\n"


def save_svg(dot_source, destination):
    """Render DOT with Graphviz and write the resulting SVG file."""
    try:
        result = subprocess.run(
            ["dot", "-Tsvg"], input=dot_source.encode("utf-8"),
            capture_output=True, check=True,
        )
    except FileNotFoundError as error:
        raise RenderError("установите Graphviz (команда dot)") from error
    except subprocess.CalledProcessError as error:
        detail = error.stderr.decode("utf-8", errors="replace").strip()
        raise RenderError(f"ошибка Graphviz: {detail}") from error
    except OSError as error:
        raise RenderError(f"не удалось запустить Graphviz: {error}") from error
    try:
        destination.write_bytes(result.stdout)
    except OSError as error:
        raise RenderError(f"не удалось сохранить SVG: {error}") from error
