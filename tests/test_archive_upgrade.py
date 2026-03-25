from pathlib import Path
import gzip
import zipfile

import pytest

import dbgz
import WOSRaw as wos
from WOSRaw import cli as wos_cli


def _create_wos_zip(path: Path, payloads: list[str] | None = None) -> Path:
    if payloads is None:
        payloads = [
            """<records>
<REC><UID>WOS:0001</UID><title>Paper 1</title></REC>
<REC><UID>WOS:0002</UID><title>Paper 2</title></REC>
</records>"""
        ]

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zipfd:
        for index, xml_payload in enumerate(payloads, start=1):
            inner_gz_name = f"records_{index:02d}.xml.gz"
            inner_gz_path = path.parent / inner_gz_name
            with gzip.open(inner_gz_path, "wb") as gzfd:
                gzfd.write(xml_payload.encode("utf-8"))
            zipfd.write(inner_gz_path, arcname=inner_gz_name)
            inner_gz_path.unlink()

    return path


def test_wos_create_dbgz_and_reader(tmp_path: Path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    _create_wos_zip(raw_dir / "WoS_sample.zip")

    out_dbgz = tmp_path / "wos.dbgz"
    result = wos.archive.create(
        raw_dir,
        out_dbgz,
        outputFormat="dbgz",
        ncpu=1,
        showProgressbar=False,
        maxPieceSize=2,
    )

    assert result["dbgz"] is not None
    with dbgz.DBGZReader(str(out_dbgz)) as reader:
        entries = list(reader.entries)
    assert len(entries) == 2
    assert {entry["UID"] for entry in entries} == {"WOS:0001", "WOS:0002"}

    piece_reader = wos.archive.readDBGZ(out_dbgz, chunksize=1, output="dataframe", showProgressbar=False)
    chunks = list(piece_reader.chunks)
    assert len(chunks) == 2
    assert chunks[0].shape[0] == 1


def test_wos_create_both_dbgz_and_parquet(tmp_path: Path):
    try:
        import parcake  # noqa: F401
    except Exception as exc:
        pytest.skip("parcake unavailable: %s" % exc)

    raw_dir = tmp_path / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    _create_wos_zip(raw_dir / "WoS_sample_both.zip")

    out_dbgz = tmp_path / "wos_both.dbgz"
    out_parquet = tmp_path / "wos_both.parquet"

    result = wos.archive.create(
        raw_dir,
        out_dbgz,
        outputFormat="both",
        parquetPath=out_parquet,
        ncpu=1,
        showProgressbar=False,
        maxPieceSize=2,
    )

    assert Path(result["dbgz"]).exists()
    assert Path(result["parquet"]).exists()

    import pandas as pd

    frame = pd.read_parquet(out_parquet)
    assert frame.shape[0] == 2
    assert set(frame.columns) == {"UID", "data"}


def test_wos_create_uses_parallel_iterator_when_ncpu_gt_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    _create_wos_zip(raw_dir / "WoS_sample_parallel.zip")

    out_dbgz = tmp_path / "wos_parallel.dbgz"
    branch_calls = {"parallel": 0, "stream": 0}

    def fake_iter_wos_entries(*args, **kwargs):
        branch_calls["parallel"] += 1
        yield {"UID": "WOS:parallel-1", "title": "Parallel Paper", "origin": "WoS_sample_parallel"}

    def fail_stream(*args, **kwargs):
        branch_calls["stream"] += 1
        raise AssertionError("streaming path should not be used when ncpu > 1")

    monkeypatch.setattr(wos.archive, "_iter_wos_entries", fake_iter_wos_entries)
    monkeypatch.setattr(wos.archive, "_streamWOSXMLRecords", fail_stream)

    result = wos.archive.create(
        raw_dir,
        out_dbgz,
        outputFormat="dbgz",
        ncpu=2,
        showProgressbar=False,
        maxPieceSize=2,
    )

    assert result["dbgz"] is not None
    assert branch_calls == {"parallel": 1, "stream": 0}

    with dbgz.DBGZReader(str(out_dbgz)) as reader:
        entries = list(reader.entries)
    assert len(entries) == 1
    assert entries[0]["UID"] == "WOS:parallel-1"


def test_iter_wos_entries_parallel_streams_progressively(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    _create_wos_zip(
        raw_dir / "WoS_sample_parallel_stream.zip",
        payloads=[
            """<records>
<REC><UID>WOS:1001</UID><title>Paper A</title></REC>
<REC><UID>WOS:1002</UID><title>Paper B</title></REC>
</records>""",
            """<records>
<REC><UID>WOS:2001</UID><title>Paper C</title></REC>
<REC><UID>WOS:2002</UID><title>Paper D</title></REC>
</records>""",
        ],
    )

    def fail_parse(*args, **kwargs):
        raise AssertionError("legacy full-XML parser should not be used by the parallel iterator")

    monkeypatch.setattr(wos.archive, "parseWOSXML", fail_parse)

    entries = list(wos.archive._iter_wos_entries(raw_dir, ncpu=2, showProgressbar=False))

    assert len(entries) == 4
    assert {entry["UID"] for entry in entries} == {"WOS:1001", "WOS:1002", "WOS:2001", "WOS:2002"}


def test_wos_pipeline_cli_defaults_to_dbgz_and_processed_parquet(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    raw_dir = tmp_path / "WoS_2023"
    raw_dir.mkdir(parents=True, exist_ok=True)
    output_dir = tmp_path / "out"

    calls = {}

    def fake_create(*args, **kwargs):
        calls["create_args"] = args
        calls["create_kwargs"] = kwargs
        return {"dbgz": str(args[1]), "parquet": None}

    def fake_extract(**kwargs):
        calls["extract_kwargs"] = kwargs

    monkeypatch.setattr(wos.archive, "create", fake_create)
    monkeypatch.setattr(wos.processed, "runExtraction", fake_extract)

    wos_cli.main([
        str(raw_dir),
        "--output-dir",
        str(output_dir),
        "--ncpu",
        "2",
        "--no-progress",
    ])

    assert calls["create_args"][0] == raw_dir
    assert calls["create_args"][1] == output_dir / "WoS_2023_All.dbgz"
    assert calls["create_kwargs"]["outputFormat"] == "dbgz"
    assert calls["create_kwargs"]["parquetPath"] is None
    assert calls["create_kwargs"]["ncpu"] == 2
    assert calls["extract_kwargs"]["WOSArchivePath"] == output_dir / "WoS_2023_All.dbgz"
    assert calls["extract_kwargs"]["outputDir"] == output_dir
    assert calls["extract_kwargs"]["baseName"] == "WoS_2023"
    assert calls["extract_kwargs"]["formats"] == ["parquet"]


def test_wos_pipeline_cli_passes_optional_overrides(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    raw_dir = tmp_path / "raw_source"
    raw_dir.mkdir(parents=True, exist_ok=True)
    custom_dbgz = tmp_path / "artifacts" / "custom.dbgz"
    custom_parquet = tmp_path / "artifacts" / "custom.parquet"
    processed_dir = tmp_path / "processed"
    worker_logs = tmp_path / "worker_logs"

    calls = {}

    def fake_create(*args, **kwargs):
        calls["create_args"] = args
        calls["create_kwargs"] = kwargs
        return {"dbgz": str(args[1]), "parquet": str(kwargs["parquetPath"])}

    def fake_extract(**kwargs):
        calls["extract_kwargs"] = kwargs

    monkeypatch.setattr(wos.archive, "create", fake_create)
    monkeypatch.setattr(wos.processed, "runExtraction", fake_extract)

    wos_cli.main([
        str(raw_dir),
        "--raw-dbgz",
        str(custom_dbgz),
        "--raw-parquet",
        str(custom_parquet),
        "--processed-dir",
        str(processed_dir),
        "--base-name",
        "CustomWoS",
        "--raw-output-format",
        "both",
        "--processed-formats",
        "csv",
        "parquet",
        "--worker-log-dir",
        str(worker_logs),
        "--xml-timeout-seconds",
        "0",
    ])

    assert calls["create_args"][1] == custom_dbgz
    assert calls["create_kwargs"]["outputFormat"] == "both"
    assert calls["create_kwargs"]["parquetPath"] == custom_parquet
    assert calls["create_kwargs"]["xmlTimeoutSeconds"] is None
    assert calls["create_kwargs"]["workerLogDir"] == str(worker_logs)
    assert calls["extract_kwargs"]["outputDir"] == processed_dir
    assert calls["extract_kwargs"]["baseName"] == "CustomWoS"
    assert calls["extract_kwargs"]["formats"] == ["csv", "parquet"]
