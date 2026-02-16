from pathlib import Path
import gzip
import zipfile

import pytest

import dbgz
import WOSRaw as wos


def _create_wos_zip(path: Path) -> Path:
    xml_payload = """<records>
<REC><UID>WOS:0001</UID><title>Paper 1</title></REC>
<REC><UID>WOS:0002</UID><title>Paper 2</title></REC>
</records>"""

    inner_gz_name = "records_01.xml.gz"
    inner_gz_path = path.parent / inner_gz_name
    with gzip.open(inner_gz_path, "wb") as gzfd:
        gzfd.write(xml_payload.encode("utf-8"))

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zipfd:
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
