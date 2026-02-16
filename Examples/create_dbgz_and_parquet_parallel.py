from pathlib import Path

import WOSRaw as wos


def main():
    wos_path = Path("/mnt/sciencegenome/WOS_RAW/WoS_2023")
    out_dbgz = Path("./Processed/WoS_2023_sample.dbgz")
    out_parquet = Path("./Processed/WoS_2023_sample.parquet")
    out_dbgz.parent.mkdir(parents=True, exist_ok=True)

    result = wos.archive.create(
        wos_path,
        out_dbgz,
        outputFormat="both",
        parquetPath=out_parquet,
        ncpu=4,
        maxPieceSize=100_000,
        showProgressbar=True,
    )
    print(result)


if __name__ == "__main__":
    main()
