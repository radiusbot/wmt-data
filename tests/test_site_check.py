from __future__ import annotations

import json
from pathlib import Path

import pytest

from wmt_data.cli import EXIT_INVALID, EXIT_OK, main
from wmt_data.site_check import (
    APP_PARSER_CONFIG,
    KNOWN_SOURCES,
    REQUIRED_SITE_FILES,
    SyncError,
    check_config,
    check_parser_config,
    check_site,
    parse_json,
    sync_parser_config,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLISHED_SITE = REPO_ROOT / "site"


def valid_config() -> dict[str, object]:
    return {
        "schema": 1,
        "sources": dict.fromkeys(sorted(KNOWN_SOURCES), True),
        "bannerAds": True,
        "minSupportedAppVersion": "1.0.0",
        "notice": None,
    }


def write_site(site: Path, *, parser_version: int = 3) -> None:
    site.mkdir(parents=True, exist_ok=True)
    for name in ("index.html", "privacy.html", "terms.html", "support.html"):
        (site / name).write_text("<!doctype html>", encoding="utf-8")
    (site / "config.json").write_text(json.dumps(valid_config()), encoding="utf-8")
    (site / "parser-config.json").write_text(
        json.dumps({"version": parser_version, "sources": {}}), encoding="utf-8"
    )


def write_app_parser_config(app_repo: Path, text: str) -> None:
    path = app_repo / APP_PARSER_CONFIG
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# config.json


def test_valid_config_has_no_problems() -> None:
    assert check_config(valid_config()) == []


def test_config_notice_may_be_text() -> None:
    config = valid_config()
    config["notice"] = "NTES is down for maintenance tonight."
    assert check_config(config) == []


def test_config_must_be_an_object() -> None:
    assert check_config([]) == ["config.json: top level must be an object"]


@pytest.mark.parametrize(
    ("key", "value", "expected"),
    [
        ("schema", 2, "'schema' must be 1"),
        ("schema", True, "'schema' must be 1"),
        ("bannerAds", "yes", "'bannerAds' must be true or false"),
        ("minSupportedAppVersion", "1.0", "must look like 1.2.3"),
        ("minSupportedAppVersion", "01.0.0", "must look like 1.2.3"),
        ("notice", "", "'notice' must be null or a non-empty string"),
        ("notice", {"text": "x"}, "'notice' must be null or a non-empty string"),
        ("sources", [], "'sources' must be an object"),
    ],
)
def test_config_rejects_bad_values(key: str, value: object, expected: str) -> None:
    config = valid_config()
    config[key] = value
    problems = check_config(config)
    assert len(problems) == 1
    assert expected in problems[0]


def test_config_reports_missing_and_unknown_top_level_keys() -> None:
    config = valid_config()
    del config["bannerAds"]
    config["banner_ads"] = True
    assert check_config(config) == [
        "config.json: missing key 'bannerAds'",
        "config.json: unknown key 'banner_ads'",
    ]


def test_config_sources_must_list_every_known_source_exactly() -> None:
    config = valid_config()
    sources = dict.fromkeys(sorted(KNOWN_SOURCES - {"pnr"}), True)
    sources["PNR"] = False
    sources["schedule"] = 0  # type: ignore[assignment]
    config["sources"] = sources
    assert check_config(config) == [
        "config.json: sources is missing 'pnr'",
        "config.json: sources has unknown key 'PNR' (the app ignores it)",
        "config.json: sources.schedule must be true or false",
    ]


# parser-config.json


def test_valid_parser_config() -> None:
    assert check_parser_config({"version": 1, "sources": {"ntes": {}}}) == []


@pytest.mark.parametrize("version", [None, 0, -1, 1.5, "2", True])
def test_parser_config_rejects_bad_version(version: object) -> None:
    assert check_parser_config({"version": version, "sources": {}}) == [
        "parser-config.json: 'version' must be an integer >= 1"
    ]


def test_parser_config_requires_sources_object() -> None:
    assert check_parser_config({"version": 1}) == ["parser-config.json: 'sources' must be an object"]


def test_parse_json_rejects_duplicate_keys() -> None:
    with pytest.raises(ValueError, match="duplicate key 'bannerAds'"):
        parse_json('{"bannerAds": true, "bannerAds": false}')


# whole site


def test_check_site_accepts_complete_site(tmp_path: Path) -> None:
    write_site(tmp_path)
    assert check_site(tmp_path) == []


def test_check_site_reports_missing_files(tmp_path: Path) -> None:
    assert check_site(tmp_path) == [f"{name}: missing from {tmp_path}" for name in REQUIRED_SITE_FILES]


def test_check_site_reports_invalid_json(tmp_path: Path) -> None:
    write_site(tmp_path)
    (tmp_path / "config.json").write_text("{", encoding="utf-8")
    problems = check_site(tmp_path)
    assert len(problems) == 1
    assert problems[0].startswith("config.json: not valid JSON")


def test_published_config_matches_contract() -> None:
    document = parse_json((PUBLISHED_SITE / "config.json").read_text(encoding="utf-8"))
    assert check_config(document) == []


def test_published_pages_exist_and_link_legal_pages() -> None:
    index = (PUBLISHED_SITE / "index.html").read_text(encoding="utf-8")
    assert 'href="support.html"' in index
    assert 'href="privacy.html"' in index
    assert 'href="terms.html"' in index
    for name in ("privacy.html", "terms.html", "support.html"):
        page = (PUBLISHED_SITE / name).read_text(encoding="utf-8")
        assert "not affiliated" in page
    support = (PUBLISHED_SITE / "support.html").read_text(encoding="utf-8")
    assert "mailto:radiusbot@gmail.com" in support


# sync-parser-config


def test_sync_copies_bytes_and_returns_version(tmp_path: Path) -> None:
    app, site = tmp_path / "app", tmp_path / "site"
    text = '{\n  "version": 4,\n  "sources": {"ntes": {"x": 1}}\n}\n'
    write_app_parser_config(app, text)
    assert sync_parser_config(app, site) == 4
    assert (site / "parser-config.json").read_text(encoding="utf-8") == text


def test_sync_refuses_invalid_app_file(tmp_path: Path) -> None:
    app, site = tmp_path / "app", tmp_path / "site"
    write_app_parser_config(app, '{"sources": {}}')
    with pytest.raises(SyncError, match="'version' must be an integer"):
        sync_parser_config(app, site)
    assert not (site / "parser-config.json").exists()


def test_sync_refuses_missing_app_file(tmp_path: Path) -> None:
    with pytest.raises(SyncError, match="does not exist"):
        sync_parser_config(tmp_path / "app", tmp_path / "site")


def test_sync_refuses_to_downgrade_published_copy(tmp_path: Path) -> None:
    app, site = tmp_path / "app", tmp_path / "site"
    write_site(site, parser_version=5)
    write_app_parser_config(app, '{"version": 4, "sources": {}}')
    with pytest.raises(SyncError, match="site has version 5 but the app has 4"):
        sync_parser_config(app, site)
    assert json.loads((site / "parser-config.json").read_text(encoding="utf-8"))["version"] == 5


# command line


def test_cli_check_ok(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_site(tmp_path)
    assert main(["--site", str(tmp_path), "check"]) == EXIT_OK
    assert capsys.readouterr().out.strip() == f"{tmp_path}: OK"


def test_cli_check_fails_on_problems(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--site", str(tmp_path), "check"]) == EXIT_INVALID
    assert "index.html: missing" in capsys.readouterr().err


def test_cli_sync_then_checks_site(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app, site = tmp_path / "app", tmp_path / "site"
    write_site(site, parser_version=1)
    write_app_parser_config(app, '{"version": 2, "sources": {}}')
    monkeypatch.setenv("APP_REPO", str(app))
    assert main(["--site", str(site), "sync-parser-config"]) == EXIT_OK
    assert json.loads((site / "parser-config.json").read_text(encoding="utf-8"))["version"] == 2


def test_cli_sync_failure_exits_invalid(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--site", str(tmp_path), "sync-parser-config", "--app-repo", str(tmp_path)]) == EXIT_INVALID
    assert "does not exist" in capsys.readouterr().err
