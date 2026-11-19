"""Tests for direct dependency collection from npm metadata."""

from contextlib import redirect_stdout
from io import BytesIO, StringIO
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from dependency_graph.registry import RegistryError, direct_dependencies
from main import main


class Response(BytesIO):
    """An in-memory context manager resembling an HTTP response."""


def metadata(*, dependencies=None, latest="1.0.0"):
    """Encode a small npm package metadata response."""
    data = {
        "dist-tags": {"latest": latest},
        "versions": {"1.0.0": {"dependencies": dependencies or {}}},
    }
    return Response(json.dumps(data).encode("utf-8"))


class RegistryTests(unittest.TestCase):
    """Check HTTP, metadata parsing, and CLI output without a network."""

    @patch("dependency_graph.registry.urlopen")
    def test_direct_dependencies_and_scoped_url(self, fetch):
        """Use npm's Accept header and encode scoped package names."""
        fetch.return_value = metadata(dependencies={"z": "^2", "a": "~1"})
        dependencies = direct_dependencies(
            "https://registry.npmjs.org", "@scope/name"
        )
        self.assertEqual(dependencies, {"a": "~1", "z": "^2"})
        request = fetch.call_args.args[0]
        self.assertTrue(request.full_url.endswith("/@scope%2Fname"))
        self.assertEqual(
            request.get_header("Accept"),
            "application/vnd.npm.install-v1+json",
        )

    @patch("dependency_graph.registry.urlopen")
    def test_latest_version_and_empty_dependencies(self, fetch):
        """Read latest rather than an arbitrary version."""
        fetch.return_value = metadata()
        self.assertEqual(
            direct_dependencies("https://registry.npmjs.org", "x"), {}
        )
        fetch.return_value = metadata(latest="2.0.0")
        with self.assertRaisesRegex(RegistryError, "latest"):
            direct_dependencies("https://registry.npmjs.org", "x")

    @patch("dependency_graph.registry.urlopen")
    def test_http_and_malformed_metadata(self, fetch):
        """Report missing packages, connection errors, and broken JSON."""
        fetch.side_effect = HTTPError("url", 404, "missing", {}, None)
        with self.assertRaisesRegex(RegistryError, "пакет не найден"):
            direct_dependencies("https://registry.npmjs.org", "missing")
        fetch.side_effect = URLError("offline")
        with self.assertRaisesRegex(RegistryError, "не удалось загрузить"):
            direct_dependencies("https://registry.npmjs.org", "x")
        fetch.side_effect = None
        fetch.return_value = Response(b"not-json")
        with self.assertRaisesRegex(RegistryError, "неверный JSON"):
            direct_dependencies("https://registry.npmjs.org", "x")

    @patch("main.direct_dependencies", return_value={"accepts": "~1.3"})
    def test_cli_prints_direct_dependencies(self, fetch):
        """Stage two CLI prints direct names and version ranges."""
        output = StringIO()
        with redirect_stdout(output):
            code = main(["--config", str(PROJECT / "config.example.xml")])
        self.assertEqual(code, 0)
        self.assertIn("accepts: ~1.3", output.getvalue())
        fetch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
