#!/usr/bin/env python3
# main.py ────────────────────────────────────────────────────────────────
# Unified CLI that drives every stage of the *cotations* pipeline.
#
#   ┌─────────────── General help ────────────────┐
#   │  python3 main.py -h                         │
#   │                                             │
#   │  python3 main.py <sub-cmd> -h               │
#   │      → help for a particular sub-command    │
#   └─────────────────────────────────────────────┘
#
# Boolean switches are OFF by default; enable them with the flag itself
# (e.g. --dry-run).  “skip=True” defaults in helper functions are kept,
# but you can override with --no-skip.
#
# -----------------------------------------------------------------------
# $ python3 main.py -h
#
# usage: main.py [-h]
#                {export,map,reduce,pipeline,gpt-route,gpt-bulk,csv-route,csv-bulk}
#                ...
#
# positional arguments (sub-commands)
#   export       dump the whole «route» table to CSV
#   map          run the mapper step  (route.csv → MapperOutput.csv)
#   reduce       run the reducer step (GPT → result.csv)
#   pipeline     export → map → reduce → (optional) DB insert
#   gpt-route    GPT-extract cotations for ONE route (reads DB)
#   gpt-bulk     GPT-extract cotations for MANY routes  (reads DB)
#   csv-route    import ONE route’s cotations from a CSV into the DB
#   csv-bulk     import a full CSV (id ; cotations) into the DB
#
# optional arguments
#   -h, --help   show this message and exit
#
# -----------------------------------------------------------------------
# Example
#   python3 main.py pipeline --dry-run
# -----------------------------------------------------------------------

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# ── internal modules ────────────────────────────────────────────────
from Databases.DbOps import (
    ExportRoutes,
    produceRoutesCotationsInBulk,
    produceRouteCotations,
)
from MapReduce.mapper import mapper
from MapReduce.reducer import reducer
from AI.AiOps import AiOpsCotationsExtended

# ── default file locations ─────────────────────────────────────────
DATA_DIR = Path("/app/data")
DEFAULT_ROUTE_CSV   = DATA_DIR / "route.csv"
DEFAULT_MAP_CSV     = DATA_DIR / "MapperOutput.csv"
DEFAULT_REDUCE_CSV  = DATA_DIR / "result.csv"


# ===================================================================
# helpers for CLI → bool (argparse “store_false/true” is verbose)
def _add_bool_flag(
        parser: argparse.ArgumentParser,
        name: str,
        default: bool,
        help_on:  str | None = None,          # ← now optional
        help_off: str | None = None
) -> None:
    """
    Add a --flag / --no-flag pair that toggles a boolean.
    If the caller does not provide custom help text, reasonable defaults
    are generated (“enable <flag>” / “disable <flag>”).
    """
    help_on  = help_on  or f"enable {name}"
    help_off = help_off or f"disable {name}"

    group = parser.add_mutually_exclusive_group()
    group.add_argument(f"--{name}",    dest=name, action="store_true",
                       help=help_on)
    group.add_argument(f"--no-{name}", dest=name, action="store_false",
                       help=help_off)
    parser.set_defaults(**{name: default})


# ===================================================================
# sub-command functions
# -------------------------------------------------------------------
def cmd_export(ns: argparse.Namespace) -> None:
    ExportRoutes(str(ns.out))


def cmd_map(ns: argparse.Namespace) -> None:
    # mapper internally uses fixed paths, but we let the user override
    if ns.in_csv:   # monkey-patch globals inside mapper.py
        mapper.input_file  = str(ns.in_csv)   # type: ignore
    if ns.out_csv:
        mapper.output_file = str(ns.out_csv)  # type: ignore
    mapper()


def cmd_reduce(ns: argparse.Namespace) -> None:
    reducer(
        input_csv_path=ns.in_csv,
        output_csv_path=ns.out_csv,
    )


def cmd_pipeline(ns: argparse.Namespace) -> None:
    ExportRoutes(str(ns.route_csv))
    if ns.map_step:
        if ns.mapper_out:
            mapper.output_file = str(ns.mapper_out)  # type: ignore
        mapper()
    if ns.reduce_step:
        reducer(
            input_csv_path=ns.mapper_out,
            output_csv_path=ns.reduce_out,
        )
    if ns.insert_step:
        produceRoutesCotationsInBulk(
            csv_path=ns.reduce_out,
            skip=ns.skip,
            limit=ns.limit,
            dry_run=ns.dry_run,
        )


def cmd_gpt_route(ns: argparse.Namespace) -> None:
    AiOpsCotationsExtended().produceCotationsForRoute(
        route_id=ns.route_id,
        dry_run=ns.dry_run,
    )


def cmd_gpt_bulk(ns: argparse.Namespace) -> None:
    AiOpsCotationsExtended().produceCotationsInBulk(
        skip=ns.skip,
        limit=ns.limit,
        dry_run=ns.dry_run,
    )


def cmd_csv_route(ns: argparse.Namespace) -> None:
    produceRouteCotations(
        route_id=ns.route_id,
        csv_path=ns.csv,
        dry_run=ns.dry_run,
    )


def cmd_csv_bulk(ns: argparse.Namespace) -> None:
    produceRoutesCotationsInBulk(
        csv_path=ns.csv,
        skip=ns.skip,
        limit=ns.limit,
        dry_run=ns.dry_run,
    )


# ===================================================================
# build the argparse tree
# -------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Whympr cotations – master CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # --- export ----------------------------------------------------
    sp = sub.add_parser("export", help="dump whole route table to CSV")
    sp.add_argument("-o", "--out", type=Path, default=DEFAULT_ROUTE_CSV,
                    help="output CSV")
    sp.set_defaults(func=cmd_export)

    # --- map -------------------------------------------------------
    sp = sub.add_parser("map", help="run mapper step")
    sp.add_argument("-i", "--in-csv",  type=Path, default=DEFAULT_ROUTE_CSV,
                    help="route CSV to read")
    sp.add_argument("-o", "--out-csv", type=Path, default=DEFAULT_MAP_CSV,
                    help="output CSV (mapper result)")
    sp.set_defaults(func=cmd_map)

    # --- reduce ----------------------------------------------------
    sp = sub.add_parser("reduce", help="run reducer step (GPT)")
    sp.add_argument("-i", "--in-csv",  type=Path, default=DEFAULT_MAP_CSV)
    sp.add_argument("-o", "--out-csv", type=Path, default=DEFAULT_REDUCE_CSV)
    sp.set_defaults(func=cmd_reduce)

    # --- pipeline --------------------------------------------------
    sp = sub.add_parser("pipeline", help="export → map → reduce → (optional DB)")
    sp.add_argument("--route-csv",  type=Path, default=DEFAULT_ROUTE_CSV)
    sp.add_argument("--mapper-out", type=Path, default=DEFAULT_MAP_CSV)
    sp.add_argument("--reduce-out", type=Path, default=DEFAULT_REDUCE_CSV)
    _add_bool_flag(sp, "map_step",    True,  "include mapper step")
    _add_bool_flag(sp, "reduce_step", True,  "include reducer step")
    _add_bool_flag(sp, "insert_step", False, "insert reducer CSV into DB")
    _add_bool_flag(sp, "skip",        True,
                   help_on="skip routes that already have ai_cotations",
                   help_off="re-process every route (no skip)")
    sp.add_argument("--limit",   type=int, default=None,
                    help="max #routes to insert when insert_step is on")
    _add_bool_flag(sp, "dry_run", False,
                   help_on="do NOT write ai_cotations when inserting")
    sp.set_defaults(func=cmd_pipeline)

    # --- gpt-route -------------------------------------------------
    sp = sub.add_parser("gpt-route", help="GPT a single route directly from DB")
    sp.add_argument("route_id", type=int)
    _add_bool_flag(sp, "dry_run", False, help_on="do not write in DB")
    sp.set_defaults(func=cmd_gpt_route)

    # --- gpt-bulk --------------------------------------------------
    sp = sub.add_parser("gpt-bulk", help="GPT many routes directly from DB")
    _add_bool_flag(sp, "skip", True,
                   help_on="skip routes with existing ai_cotations",
                   help_off="process even already-filled routes")
    sp.add_argument("--limit",   type=int, default=None)
    _add_bool_flag(sp, "dry_run", False)          # ← 3-arg call now OK
    sp.set_defaults(func=cmd_gpt_bulk)

    # --- csv-route -------------------------------------------------
    sp = sub.add_parser("csv-route", help="import ONE route from a CSV into DB")
    sp.add_argument("route_id", type=int)
    sp.add_argument("csv",      type=Path)
    _add_bool_flag(sp, "dry_run", False)          # ← 3-arg call now OK
    sp.set_defaults(func=cmd_csv_route)

    # --- csv-bulk --------------------------------------------------
    sp = sub.add_parser("csv-bulk", help="import a CSV (id;cotations) into DB")
    sp.add_argument("csv", type=Path)
    _add_bool_flag(sp, "skip", True,
                   help_on="skip rows whose ai_cotations is non-empty",
                   help_off="overwrite existing ai_cotations")
    sp.add_argument("--limit",  type=int, default=None)
    _add_bool_flag(sp, "dry_run", False)          # ← 3-arg call now OK
    sp.set_defaults(func=cmd_csv_bulk)

    return p


# ===================================================================
def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    ns     = parser.parse_args(argv)
    ns.func(ns)


# ===================================================================
if __name__ == "__main__":
    main(sys.argv[1:])

