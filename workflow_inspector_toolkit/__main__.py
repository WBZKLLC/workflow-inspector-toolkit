"""Command-line interface; safe local writes and no network requests."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from . import __version__
from .core import ValidationError, analyze, compare, load_events
from .report import render_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate and summarize local workflow event files.")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "analyze", "compare", "report"):
        item = sub.add_parser(name)
        item.add_argument("input", type=Path, help="CSV or JSON input; baseline for comparisons")
        if name == "compare":
            item.add_argument("followup", type=Path)
        if name == "report":
            item.add_argument("--followup", type=Path, help="Add a baseline/follow-up comparison")
            item.add_argument("--synthetic", action="store_true", help="Label this as fictional example data")
        item.add_argument("--output", type=Path, required=name == "report", help="New local output file; never overwrites")
    args = parser.parse_args(argv)
    try:
        events = load_events(args.input)
        if args.command == "validate":
            result = {"valid": True, "events": len(events), "contract": "four-event-subset-v1"}
        elif args.command == "analyze":
            result = analyze(events)
        elif args.command == "compare":
            result = compare(events, load_events(args.followup))
        else:
            result = compare(events, load_events(args.followup)) if args.followup else analyze(events)
        output = render_report(result, synthetic=args.synthetic) if args.command == "report" else json.dumps(result, indent=2, allow_nan=False) + "\n"
        if args.output:
            try:
                with args.output.open("x", encoding="utf-8", newline="\n") as stream:
                    stream.write(output)
            except FileExistsError:
                raise ValidationError("output already exists; choose a new output path") from None
            except OSError:
                raise ValidationError("output file could not be written") from None
            print("Output written locally.")
        else:
            print(output, end="")
        return 0
    except ValidationError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except BrokenPipeError:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
