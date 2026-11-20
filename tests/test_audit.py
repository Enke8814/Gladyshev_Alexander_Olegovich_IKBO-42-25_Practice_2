"""Regression checks found during the full assignment audit."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dependency_graph.config import ConfigError, _validate_url
from dependency_graph.graph import GraphError, build_graph
from dependency_graph.order import dependency_order
from dependency_graph.render import RenderError, save_svg


class AuditTests(unittest.TestCase):
    """Check validation, dependency precedence and output failures."""

    def test_malformed_urls(self):
        """Malformed hosts and ports must produce a configuration error."""
        for url in ("https://[broken", "https://host:abc",
                    "https://host:99999", "https://bad host"):
            with self.subTest(url=url):
                with self.assertRaisesRegex(ConfigError, "repository"):
                    _validate_url(url)

    def test_dependency_precedence(self):
        """Every dependency precedes all its parents, including the root."""
        source = {"A": {"B": "", "C": ""},
                  "B": {"D": ""}, "C": {"D": ""}, "D": {}}
        graph = build_graph("A", 3, source.__getitem__)
        order = dependency_order(graph)
        self.assertEqual(set(order), set(source))
        for parent, children in source.items():
            for child in children:
                self.assertLess(order.index(child), order.index(parent))

    def test_cycle_and_depth_zero(self):
        """A cycle has no linear order; depth zero has just the root."""
        source = {"A": {"B": ""}, "B": {"A": ""}}
        with self.assertRaisesRegex(GraphError, "цикл"):
            dependency_order(build_graph("A", 3, source.__getitem__))
        graph = build_graph("A", 0, source.__getitem__)
        self.assertEqual(dependency_order(graph), ["A"])

    @patch("dependency_graph.render.subprocess.run")
    def test_output_directory_error(self, run):
        """A missing output directory must not be blamed on Graphviz."""
        run.return_value = SimpleNamespace(stdout=b"<svg/>")
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "missing" / "graph.svg"
            with self.assertRaisesRegex(RenderError, "сохранить SVG"):
                save_svg("digraph G {}", target)


if __name__ == "__main__":
    unittest.main()
