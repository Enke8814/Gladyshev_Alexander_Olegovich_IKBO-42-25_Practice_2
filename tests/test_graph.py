"""BFS and local repository integration tests."""

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from dependency_graph.config import load_config
from dependency_graph.graph import (
    GraphError, build_graph, format_graph, graph_from_config,
    load_test_repository,
)


class GraphTests(unittest.TestCase):
    """Cover branching, cycles, depth limits, and broken fixtures."""

    def test_branching_graph_and_shortest_depth(self):
        """Visit a shared child once and retain both incoming edges."""
        source = {
            "A": {"B": "", "C": ""},
            "B": {"D": ""},
            "C": {"D": ""},
            "D": {},
        }
        calls = []

        def dependencies_for(name):
            """Record each requested package."""
            calls.append(name)
            return source[name]

        graph = build_graph("A", 3, dependencies_for)
        self.assertEqual(calls, ["A", "B", "C", "D"])
        self.assertEqual(graph.load_order, ("A", "B", "C", "D"))
        self.assertEqual(graph.depths, {"A": 0, "B": 1, "C": 1, "D": 2})
        self.assertIn("D", graph.edges["B"])
        self.assertIn("D", graph.edges["C"])

    def test_cycle_does_not_repeat_fetch(self):
        """Keep a back edge without looping indefinitely."""
        source = {"A": {"B": ""}, "B": {"C": ""}, "C": {"A": ""}}
        calls = []

        def dependencies_for(name):
            """Record visited nodes in BFS order."""
            calls.append(name)
            return source[name]

        graph = build_graph("A", 8, dependencies_for)
        self.assertEqual(calls, ["A", "B", "C"])
        self.assertEqual(graph.load_order, ("A", "B", "C"))
        self.assertEqual(graph.edges["C"], {"A": ""})

    def test_depth_zero_and_one(self):
        """Do not fetch dependencies past the configured depth."""
        source = {"A": {"B": ""}, "B": {"C": ""}}
        shallow = build_graph("A", 0, source.__getitem__)
        self.assertEqual(shallow.edges, {"A": {}})
        self.assertEqual(shallow.load_order, ("A",))
        one = build_graph("A", 1, source.__getitem__)
        self.assertEqual(one.edges, {"A": {"B": ""}, "B": {}})
        self.assertNotIn("C", one.depths)
        self.assertEqual(one.load_order, ("A", "B"))

    def test_real_test_fixture(self):
        """Load the checked-in JSON graph through the XML configuration."""
        config = load_config(PROJECT / "examples" / "branching.xml")
        graph = graph_from_config(config)
        self.assertEqual(graph.depths["D"], 2)
        self.assertIn("A [глубина 0]: B, C", format_graph(graph))

    def test_bad_json_and_missing_root(self):
        """Explain invalid JSON, names, duplicate edges, and root errors."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "repository.json"
            for data in ("[1, 2]", '{"a": []}', '{"A": ["B", "B"]}'):
                path.write_text(data, encoding="utf-8")
                with self.assertRaises(GraphError):
                    load_test_repository(path)
            path.write_text(json.dumps({"A": []}), encoding="utf-8")
            with self.assertRaisesRegex(GraphError, "отсутствует"):
                graph_from_config(self._config_for_missing_root(path))

    def _config_for_missing_root(self, path):
        """Create a test configuration whose root is absent from the JSON."""
        xml = path.with_suffix(".xml")
        xml.write_text(
            "<config><package>B</package>"
            f"<repository>{path.name}</repository>"
            "<test_mode>true</test_mode><output>graph.svg</output>"
            "<max_depth>2</max_depth></config>",
            encoding="utf-8",
        )
        return load_config(xml)


if __name__ == "__main__":
    unittest.main()
