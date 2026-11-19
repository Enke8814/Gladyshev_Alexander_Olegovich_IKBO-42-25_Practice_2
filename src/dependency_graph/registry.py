"""Read npm package metadata without npm or third-party packages."""

import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


ACCEPT = "application/vnd.npm.install-v1+json"
TIMEOUT_SECONDS = 10


class RegistryError(ValueError):
    """The npm registry could not provide usable package metadata."""


def _metadata_url(repository, package):
    """Build an npm endpoint, encoding the slash in scoped names."""
    return f"{repository}/{quote(package, safe='@')}"


def _fetch_metadata(repository, package):
    """Download and decode the npm registry's JSON metadata."""
    url = _metadata_url(repository, package)
    request = Request(url, headers={"Accept": ACCEPT})
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.load(response)
    except HTTPError as error:
        if error.code == 404:
            raise RegistryError(f"пакет не найден: {package}") from error
        raise RegistryError(f"HTTP {error.code} при загрузке {package}") from error
    except (URLError, TimeoutError, OSError) as error:
        raise RegistryError(
            f"не удалось загрузить {package}: {error}"
        ) from error
    except (UnicodeError, ValueError) as error:
        raise RegistryError(
            f"неверный JSON для {package}: {error}"
        ) from error


def direct_dependencies(repository, package):
    """Return sorted runtime dependencies of the latest tagged version."""
    metadata = _fetch_metadata(repository, package)
    if not isinstance(metadata, dict):
        raise RegistryError(f"неверные метаданные пакета: {package}")
    tags = metadata.get("dist-tags")
    versions = metadata.get("versions")
    if not isinstance(tags, dict) or not isinstance(versions, dict):
        raise RegistryError(f"нет версий или dist-tags для {package}")
    latest = tags.get("latest")
    manifest = versions.get(latest) if isinstance(latest, str) else None
    if not isinstance(manifest, dict):
        raise RegistryError(f"не найдена версия latest для {package}")
    dependencies = manifest.get("dependencies", {})
    if not isinstance(dependencies, dict) or any(
        not isinstance(name, str) or not isinstance(spec, str)
        for name, spec in dependencies.items()
    ):
        raise RegistryError(f"неверное поле dependencies для {package}")
    return dict(sorted(dependencies.items()))
