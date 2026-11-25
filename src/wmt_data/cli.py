"""Command line: `python -m wmt_data check` and `python -m wmt_data sync-parser-config`."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from wmt_data.site_check import SyncError, check_site, sync_parser_config

EXIT_OK = 0
EXIT_INVALID = 1

DEFAULT_SITE_DIR = Path("site")
DEFAULT_APP_REPO = Path("../app")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wmt_data", description=__doc__)
    parser.add_argument("--site", type=Path, default=DEFAULT_SITE_DIR, help="site directory (default: site)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check", help="validate site/ against docs/contracts/remote_files.md")
    sync = sub.add_parser("sync-parser-config", help="copy the app's parser-config.json into site/")
    sync.add_argument(
        "--app-repo",
        type=Path,
        default=Path(os.environ.get("APP_REPO", DEFAULT_APP_REPO)),
        help="app checkout (default: $APP_REPO or ../app)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    site_dir: Path = args.site

    if args.command == "sync-parser-config":
        try:
            version = sync_parser_config(args.app_repo, site_dir)
        except SyncError as error:
            print(f"sync-parser-config: {error}", file=sys.stderr)
            return EXIT_INVALID
        print(f"parser-config.json version {version} copied to {site_dir}")

    problems = check_site(site_dir)
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        return EXIT_INVALID
    print(f"{site_dir}: OK")
    return EXIT_OK
