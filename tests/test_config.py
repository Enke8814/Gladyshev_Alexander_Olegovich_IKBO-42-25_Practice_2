"""Configuration tests for valid and invalid XML settings."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from dependency_graph.config import ConfigError, load_config


class ConfigTests(unittest.TestCase):
    """Check validation and a complete CLI invocation."""

    def setUp(self):
        """Create isolated XML and repository fixtures."""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.graph = self.root / "graph.txt"
        self.graph.write_text("A: B\nB:\n", encoding="utf-8")
        self.values = {
            "package": "A",
            "repository": "graph.txt",
            "test_mode": "true",
            "output": "graph.svg",
            "max_depth": "2",
        }

    def write_config(self, **changes):
        """Create a new configuration with selected overrides."""
        values = dict(self.values, **changes)
        body = "".join(
            f"<{key}>{value}</{key}>" for key, value in values.items()
        )
        path = self.root / "config.xml"
        path.write_text(f"<config>{body}</config>", encoding="utf-8")
        return path

    def test_valid_test_repository_and_cli(self):
        """Resolve relative paths next to XML and print every field."""
        path = self.write_config()
        config = load_config(path)
        self.assertEqual(config.repository, str(self.graph))
        self.assertEqual(config.max_depth, 2)
        result = subprocess.run(
            [sys.executable, "src/main.py", "--config", str(path)],
            cwd=PROJECT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("test_mode = true", result.stdout)
        self.assertIn("package = A", result.stdout)

    def test_valid_registry(self):
        """Allow the public npm registry in normal mode."""
        config = load_config(self.write_config(
            package="@scope/name", test_mode="false",
            repository="https://registry.npmjs.org/"
        ))
        self.assertEqual(config.repository, "https://registry.npmjs.org")

    def test_invalid_registry_url_and_output_directory(self):
        """Reject invalid live URLs and missing output directories."""
        with self.assertRaisesRegex(ConfigError, "repository"):
            load_config(self.write_config(
                package="express", test_mode="false",
                repository="not-a-url",
            ))
        with self.assertRaisesRegex(ConfigError, "output"):
            load_config(self.write_config(output="missing/graph.svg"))

    def test_each_invalid_parameter(self):
        """Name the field causing each configuration error."""
        cases = (
            ("package", "Bad Name"),
            ("repository", "missing.txt"),
            ("test_mode", "sometimes"),
            ("output", "image.png"),
            ("max_depth", "-1"),
        )
        for field, value in cases:
            with self.subTest(field=field):
                with self.assertRaisesRegex(ConfigError, field):
                    load_config(self.write_config(**{field: value}))

    def test_malformed_and_missing_xml(self):
        """Explain syntax errors and absent fields."""
        path = self.write_config()
        path.write_text("<config><package>", encoding="utf-8")
        with self.assertRaises(ConfigError):
            load_config(path)
        with self.assertRaisesRegex(ConfigError, "не удалось прочитать"):
            load_config(self.root / "missing.xml")
        path.write_text("<config><package>A</package></config>",
                        encoding="utf-8")
        with self.assertRaisesRegex(ConfigError, "отсутствует параметр"):
            load_config(path)

    def test_cli_reports_error_with_nonzero_exit(self):
        """Report a named error to stderr without a traceback."""
        path = self.write_config(max_depth="-1")
        result = subprocess.run(
            [sys.executable, "src/main.py", "--config", str(path)],
            cwd=PROJECT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("max_depth", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
