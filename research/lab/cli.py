from __future__ import annotations

import argparse
import json
import sys

from lab.models import MinerConfig
from lab.miners.registry import list_miners
from lab.run import run_acquisition


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lab", description="OpenTrace research lab CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    acquire = sub.add_parser("acquire", help="Run a raw acquisition miner")
    acquire.add_argument("miner", choices=list_miners(), help="Miner name")
    acquire.add_argument("--query", type=str, default="", help="Search query (arxiv)")
    acquire.add_argument("--max-results", type=int, default=100, dest="max_results")
    acquire.add_argument(
        "--download-pdf",
        action="store_true",
        default=False,
        help="Download PDF artifacts (arxiv)",
    )
    acquire.add_argument(
        "--no-download-pdf",
        action="store_false",
        dest="download_pdf",
        help="Metadata only (arxiv)",
    )
    acquire.set_defaults(download_pdf=True)
    acquire.add_argument("--json", action="store_true", help="Print manifest as JSON")

    sub.add_parser("list", help="List registered miners")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "list":
        for name in list_miners():
            print(name)
        return 0

    if args.command == "acquire":
        extras: dict = {}
        if args.query:
            extras["query"] = args.query
        config = MinerConfig(
            max_results=args.max_results,
            download_pdf=args.download_pdf,
            extras=extras,
        )
        try:
            manifest = run_acquisition(args.miner, config)
        except NotImplementedError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(manifest.to_dict(), indent=2))
        else:
            print(f"run_id={manifest.run_id} fetched={manifest.fetched} "
                  f"skipped={manifest.skipped} failed={manifest.failed}")
            print(f"manifest={manifest.manifest_path}")
            if manifest.errors:
                print("errors:", file=sys.stderr)
                for err in manifest.errors:
                    print(f"  - {err}", file=sys.stderr)
        return 0 if manifest.failed == 0 else 1

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
