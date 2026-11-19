"""Load and validate the XML configuration for the graph explorer."""

from dataclasses import dataclass
from pathlib import Path
import re
from urllib.parse import urlparse
import xml.etree.ElementTree as ET


FIELDS = ("package", "repository", "test_mode", "output", "max_depth")
PACKAGE_NAME = re.compile(
    r"^(?:@[a-z0-9][a-z0-9._-]*/)?[a-z0-9][a-z0-9._-]*$"
)


class ConfigError(ValueError):
    """Invalid or unreadable configuration."""


@dataclass(frozen=True)
class Config:
    """Validated user settings and the location of their XML file."""

    package: str
    repository: str
    test_mode: bool
    output: Path
    max_depth: int
    source: Path

    def items(self):
        """Return settings in the same order as the XML template."""
        return (
            ("package", self.package),
            ("repository", self.repository),
            ("test_mode", str(self.test_mode).lower()),
            ("output", self.output),
            ("max_depth", self.max_depth),
        )


def _read_fields(path):
    """Read a flat XML document with exactly the expected fields."""
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError) as error:
        raise ConfigError(f"не удалось прочитать {path}: {error}") from error
    if root.tag != "config" or root.attrib:
        raise ConfigError("корневой элемент должен быть <config> без атрибутов")
    values = {}
    for node in root:
        if node.tag not in FIELDS or node.tag in values:
            raise ConfigError(f"неизвестный или повторный параметр: {node.tag}")
        if node.attrib or list(node):
            raise ConfigError(f"параметр {node.tag} должен содержать текст")
        values[node.tag] = (node.text or "").strip()
    missing = set(FIELDS) - set(values)
    if missing:
        raise ConfigError(f"отсутствует параметр: {', '.join(sorted(missing))}")
    return values


def _validate_repository(value, test_mode, base):
    """Accept a readable file in test mode or an HTTP registry URL."""
    if test_mode:
        path = Path(value).expanduser()
        path = path if path.is_absolute() else base / path
        if not path.is_file():
            raise ConfigError(f"repository: файл не найден: {path}")
        return str(path.resolve())
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ConfigError("repository: требуется URL http(s) репозитория")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ConfigError("repository: URL не должен содержать учётные данные")
    return value.rstrip("/")


def _validate_output(value, base):
    """Ensure that the SVG destination has an existing directory."""
    path = Path(value).expanduser()
    path = path if path.is_absolute() else base / path
    if not value or path.suffix.lower() != ".svg":
        raise ConfigError("output: имя файла должно оканчиваться на .svg")
    if not path.parent.is_dir() or path.is_dir():
        raise ConfigError(f"output: каталог назначения не существует: {path}")
    return path.resolve()


def load_config(path):
    """Load settings and report field-specific errors before execution."""
    path = Path(path).expanduser().resolve()
    values = _read_fields(path)
    package = values["package"]
    mode = values["test_mode"].lower()
    if mode not in ("true", "false"):
        raise ConfigError("test_mode: допустимы только true и false")
    valid_name = (
        re.fullmatch(r"[A-Z]+", package) if mode == "true"
        else PACKAGE_NAME.fullmatch(package)
    )
    if not valid_name or len(package) > 214:
        raise ConfigError("package: некорректное имя пакета")
    depth = values["max_depth"]
    if not depth.isascii() or not depth.isdecimal():
        raise ConfigError("max_depth: требуется целое число от 0")
    base = path.parent
    repository = _validate_repository(
        values["repository"], mode == "true", base
    )
    return Config(
        package=package,
        repository=repository,
        test_mode=mode == "true",
        output=_validate_output(values["output"], base),
        max_depth=int(depth),
        source=path,
    )
