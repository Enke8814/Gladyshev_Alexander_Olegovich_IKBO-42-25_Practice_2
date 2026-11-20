"""Graphviz text generation and SVG integration tests."""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as ET


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from dependency_graph.graph import Graph
from dependency_graph.render import RenderError, save_svg, to_dot


class RenderTests(unittest.TestCase):
    """Check complete edges, cycles, and the actual SVG file."""

    def test_dot_includes_cycle_and_version(self):
        """Preserve edges back to the root and escape version labels."""
        graph = Graph(
            {"A": {"B": '>=1"x'}, "B": {"A": ""}},
            {"A": 0, "B": 1}, ("A", "B"),
        )
        source = to_dot(graph)
        self.assertIn('"A" -> "B" [label=">=1\\"x"]', source)
        self.assertIn('"B" -> "A";', source)
        self.assertIn('"A" [label="A\\nглубина 0",', source)

    @unittest.skipUnless(shutil.which("dot"), "Graphviz не установлен")
    def test_svg_is_valid_xml(self):
        """Render a graph and parse the generated SVG as XML."""
        graph = Graph({"A": {"B": ""}, "B": {}},
                      {"A": 0, "B": 1}, ("A", "B"))
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "graph.svg"
            save_svg(to_dot(graph), destination)
            root = ET.parse(destination).getroot()
            self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
            self.assertIn("A", destination.read_text(encoding="utf-8"))

    @patch("dependency_graph.render.subprocess.run")
    def test_missing_graphviz_is_explained(self, run):
        """Report a missing Graphviz executable without a traceback."""
        run.side_effect = FileNotFoundError("dot")
        with self.assertRaisesRegex(RenderError, "Graphviz"):
            save_svg("digraph G {}", Path("unused.svg"))


if __name__ == "__main__":
    unittest.main()
