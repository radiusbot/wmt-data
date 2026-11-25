"""Checks for the files published under site/.

The contract is docs/contracts/remote_files.md in the workspace root. Every check
returns a list of human-readable problems; an empty list means the input is valid.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

CONFIG_FILE = "config.json"
PARSER_CONFIG_FILE = "parser-config.json"
REQUIRED_SITE_FILES = (
    "index.html",
    "privacy.html",
    "terms.html",
    "support.html",
    CONFIG_FILE,
    PARSER_CONFIG_FILE,
)

CONFIG_SCHEMA_VERSION = 1
# Mirrors the Dart enum `LiveSource` (app/lib/domain/settings.dart).
KNOWN_SOURCES = frozenset(
    {"liveStatus", "pnr", "stationBoard", "coachPosition", "referenceData", "schedule", "trainsBetween"}
)
CONFIG_KEYS = frozenset({"schema", "sources", "bannerAds", "minSupportedAppVersion", "notice"})

_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")

APP_PARSER_CONFIG = Path("assets/config") / PARSER_CONFIG_FILE


class DuplicateKeyError(ValueError):
    """A JSON object repeats a key; json.loads would silently keep the last value."""


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate key {key!r}")
        result[key] = value
    return result


def parse_json(text: str) -> object:
    """Strict JSON parse: duplicate object keys are an error."""
    return json.loads(text, object_pairs_hook=_reject_duplicate_keys)


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def check_config(document: object) -> list[str]:
    if not isinstance(document, dict):
        return ["config.json: top level must be an object"]
    problems: list[str] = []
    for key in sorted(CONFIG_KEYS - document.keys()):
        problems.append(f"config.json: missing key {key!r}")
    for key in sorted(document.keys() - CONFIG_KEYS):
        problems.append(f"config.json: unknown key {key!r}")

    if "schema" in document and not (
        _is_int(document["schema"]) and document["schema"] == CONFIG_SCHEMA_VERSION
    ):
        problems.append(f"config.json: 'schema' must be {CONFIG_SCHEMA_VERSION}")

    if "sources" in document:
        problems.extend(_check_sources(document["sources"]))

    if "bannerAds" in document and not isinstance(document["bannerAds"], bool):
        problems.append("config.json: 'bannerAds' must be true or false")

    if "minSupportedAppVersion" in document:
        version = document["minSupportedAppVersion"]
        if not (isinstance(version, str) and _SEMVER.match(version)):
            problems.append("config.json: 'minSupportedAppVersion' must look like 1.2.3")

    if "notice" in document:
        notice = document["notice"]
        if notice is not None and not (isinstance(notice, str) and notice.strip()):
            problems.append("config.json: 'notice' must be null or a non-empty string")
    return problems


def _check_sources(sources: object) -> list[str]:
    if not isinstance(sources, dict):
        return ["config.json: 'sources' must be an object"]
    problems: list[str] = []
    # The app treats a missing key as enabled and ignores unknown keys, so both
    # would hide a typo in a kill switch. The published file lists every source.
    for key in sorted(KNOWN_SOURCES - sources.keys()):
        problems.append(f"config.json: sources is missing {key!r}")
    for key in sorted(sources.keys() - KNOWN_SOURCES):
        problems.append(f"config.json: sources has unknown key {key!r} (the app ignores it)")
    for key, value in sorted(sources.items()):
        if key in KNOWN_SOURCES and not isinstance(value, bool):
            problems.append(f"config.json: sources.{key} must be true or false")
    return problems


def parser_config_version(document: object) -> int | None:
    """The document's `version` if it is an integer >= 1, else None."""
    if not isinstance(document, dict):
        return None
    version = document.get("version")
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        return None
    return version


def check_parser_config(document: object) -> list[str]:
    if not isinstance(document, dict):
        return ["parser-config.json: top level must be an object"]
    problems: list[str] = []
    if parser_config_version(document) is None:
        problems.append("parser-config.json: 'version' must be an integer >= 1")
    if not isinstance(document.get("sources"), dict):
        problems.append("parser-config.json: 'sources' must be an object")
    return problems


def _load(path: Path) -> tuple[object, list[str]]:
    try:
        return parse_json(path.read_text(encoding="utf-8")), []
    except (UnicodeDecodeError, ValueError) as error:
        return None, [f"{path.name}: not valid JSON ({error})"]


def check_site(site_dir: Path) -> list[str]:
    problems = [
        f"{name}: missing from {site_dir}" for name in REQUIRED_SITE_FILES if not (site_dir / name).is_file()
    ]
    for name, check in ((CONFIG_FILE, check_config), (PARSER_CONFIG_FILE, check_parser_config)):
        path = site_dir / name
        if path.is_file():
            document, load_problems = _load(path)
            problems.extend(load_problems or check(document))
    return problems


class SyncError(Exception):
    """The app's parser-config.json cannot be published."""


def sync_parser_config(app_repo: Path, site_dir: Path) -> int:
    """Copy the app's bundled parser-config.json into site/ byte for byte; return its version.

    Refuses an invalid source file, and refuses to replace a published copy that has a
    higher version (that would mean the app checkout is older than what is live).
    """
    source = app_repo / APP_PARSER_CONFIG
    if not source.is_file():
        raise SyncError(f"{source} does not exist")
    content = source.read_bytes()
    document, problems = _load(source)
    problems = problems or check_parser_config(document)
    version = parser_config_version(document)
    if problems or version is None:
        raise SyncError("; ".join(problems))

    target = site_dir / PARSER_CONFIG_FILE
    if target.is_file():
        published, _ = _load(target)
        published_version = parser_config_version(published)
        if published_version is not None and published_version > version:
            raise SyncError(
                f"site has version {published_version} but the app has {version}; update the app checkout"
            )
    _atomic_write_bytes(target, content)
    return version


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
