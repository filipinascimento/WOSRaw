from __future__ import annotations

import argparse
from pathlib import Path
from time import perf_counter

from . import archive
from . import processed


def _default_base_name(wos_path: Path) -> str:
    name = wos_path.resolve().name.strip()
    return name or "WoS"


def _resolve_paths(args: argparse.Namespace) -> tuple[Path, Path, Path, str]:
    wos_path = Path(args.wos_path)
    output_dir = Path(args.output_dir) if args.output_dir else Path.cwd()
    output_dir.mkdir(parents=True, exist_ok=True)

    base_name = args.base_name or _default_base_name(wos_path)
    raw_dbgz = Path(args.raw_dbgz) if args.raw_dbgz else output_dir / f"{base_name}_All.dbgz"
    processed_dir = Path(args.processed_dir) if args.processed_dir else output_dir

    raw_dbgz.parent.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    return wos_path, raw_dbgz, processed_dir, base_name


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a WoS raw DBGZ archive and export processed tables from a raw WoS XML directory."
    )
    parser.add_argument("wos_path", help="Directory containing WoS .zip XML deliveries")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Default output directory for generated files; defaults to the current working directory",
    )
    parser.add_argument("--raw-dbgz", default=None, help="Output raw .dbgz path")
    parser.add_argument("--raw-parquet", default=None, help="Output raw .parquet path")
    parser.add_argument("--processed-dir", default=None, help="Output directory for processed tables")
    parser.add_argument(
        "--base-name",
        default=None,
        help="Base name for generated files; defaults to the raw WoS directory name",
    )
    parser.add_argument("--ncpu", type=int, default=16, help="Number of worker processes for XML parsing")
    parser.add_argument("--max-piece-size", type=int, default=10000, help="Piece size for dbgz/parquet outputs")
    parser.add_argument(
        "--xml-timeout-seconds",
        type=float,
        default=3600,
        help="Timeout for a single XML task in the raw stage; use 0 to disable",
    )
    parser.add_argument(
        "--heartbeat-seconds",
        type=int,
        default=120,
        help="Interval for raw-stage heartbeat logs while waiting on workers",
    )
    parser.add_argument(
        "--worker-log-dir",
        default=None,
        help="Directory for per-worker logs during raw stage",
    )
    parser.add_argument(
        "--raw-output-format",
        choices=["dbgz", "parquet", "both"],
        default="dbgz",
        help="Raw archive output format(s)",
    )
    parser.add_argument(
        "--processed-formats",
        nargs="+",
        choices=["tsv", "csv", "parquet", "dbgz"],
        default=["parquet"],
        help="Processed table output formats",
    )
    parser.add_argument("--no-progress", action="store_true", help="Disable progress bars")
    return parser.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)
    start = perf_counter()

    wos_path, raw_dbgz, processed_dir, base_name = _resolve_paths(args)

    print("[wosraw] Starting pipeline", flush=True)
    print(f"[wosraw] input={wos_path}", flush=True)
    print(f"[wosraw] raw_dbgz={raw_dbgz}", flush=True)
    print(f"[wosraw] processed_dir={processed_dir}", flush=True)
    print(
        f"[wosraw] raw_output_format={args.raw_output_format} | processed_formats={','.join(args.processed_formats)}",
        flush=True,
    )

    result = archive.create(
        wos_path,
        raw_dbgz,
        outputFormat=args.raw_output_format,
        parquetPath=(Path(args.raw_parquet) if args.raw_parquet else None),
        ncpu=args.ncpu,
        maxPieceSize=args.max_piece_size,
        showProgressbar=not args.no_progress,
        xmlTimeoutSeconds=(None if args.xml_timeout_seconds == 0 else args.xml_timeout_seconds),
        heartbeatSeconds=args.heartbeat_seconds,
        workerLogDir=args.worker_log_dir,
    )
    print(f"[wosraw] Raw stage complete: {result}", flush=True)

    processed.runExtraction(
        WOSArchivePath=raw_dbgz,
        outputDir=processed_dir,
        baseName=base_name,
        formats=args.processed_formats,
        maxPieceSize=args.max_piece_size,
        showProgress=not args.no_progress,
    )

    elapsed = perf_counter() - start
    print(f"[wosraw] All done in {elapsed/60:.2f} min", flush=True)


if __name__ == "__main__":
    main()
