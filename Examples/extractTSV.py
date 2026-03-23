import argparse
import csv
from pathlib import Path

import dbgz
from tqdm.auto import tqdm
import ujson

import WOSRaw as wos

try:
    from parcake import PieceSaver
except Exception:  # pragma: no cover
    PieceSaver = None


def parseEntry(entry, separator=";"):
    if isinstance(entry, list):
        normalized = [str(value).replace(separator, ",.") for value in entry]
        return (separator + " ").join(normalized).replace("\t", "    ")
    if entry is None:
        return ""
    return str(entry).replace("\t", "    ")


def toParquetValue(value):
    if isinstance(value, (dict, list)):
        return ujson.dumps(value)
    if value is None:
        return ""
    return str(value)


class ProcessedTableWriter:
    def __init__(
        self,
        outputDir,
        baseName,
        tableSuffix,
        columns,
        formats,
        maxPieceSize=10000,
    ):
        self.columns = list(columns)
        self.formats = set(formats)
        self.basePath = Path(outputDir) / f"{baseName}_{tableSuffix}"

        self.textWriters = []
        self.parquetSaver = None
        self.dbgzSaver = None
        self._dbgzIndex = 0

        if "tsv" in self.formats:
            path = self.basePath.with_suffix(".tsv")
            textFile = open(path, "wt", encoding="utf-8", newline="")
            textWriter = csv.DictWriter(textFile, fieldnames=self.columns, delimiter="\t")
            textWriter.writeheader()
            self.textWriters.append((textFile, textWriter))

        if "csv" in self.formats:
            path = self.basePath.with_suffix(".csv")
            textFile = open(path, "wt", encoding="utf-8", newline="")
            textWriter = csv.DictWriter(textFile, fieldnames=self.columns, delimiter=",")
            textWriter.writeheader()
            self.textWriters.append((textFile, textWriter))

        if "parquet" in self.formats:
            if PieceSaver is None:
                raise RuntimeError("parcake is required for parquet output. Please install parcake.")
            header = {column: "str" for column in self.columns}
            self.parquetSaver = PieceSaver(
                header,
                str(self.basePath.with_suffix(".parquet")),
                max_piece_size=maxPieceSize,
            )

        if "dbgz" in self.formats:
            scheme = [("row_id", "s"), ("data", "a")]
            self.dbgzSaver = dbgz.DBGZPieceSaver(
                scheme,
                str(self.basePath.with_suffix(".dbgz")),
                max_piece_size=maxPieceSize,
                show_progressbar=False,
            )

    def writeRow(self, row, rowId=""):
        cleanRow = {column: row.get(column, "") for column in self.columns}

        if self.textWriters:
            textRow = {
                column: parseEntry(cleanRow[column], separator="|" if column == "AB" else ";")
                for column in self.columns
            }
            for _, writer in self.textWriters:
                writer.writerow(textRow)

        if self.parquetSaver is not None:
            parquetRow = {column: toParquetValue(cleanRow[column]) for column in self.columns}
            self.parquetSaver.add(**parquetRow)

        if self.dbgzSaver is not None:
            if not rowId:
                rowId = str(self._dbgzIndex)
            self.dbgzSaver.add(row_id=str(rowId), data=cleanRow)
            self._dbgzIndex += 1

    def close(self):
        for textFile, _ in self.textWriters:
            textFile.close()
        if self.parquetSaver is not None:
            self.parquetSaver.close()
        if self.dbgzSaver is not None:
            self.dbgzSaver.close()


def buildAuthorRows(uid, authorRecords):
    rows = []
    for author in authorRecords:
        addresses = author.get("addresses", [])
        rows.append(
            {
                "UT": uid,
                "author_seq_no": author.get("seq_no", ""),
                "author_role": author.get("role", ""),
                "author_reprint": author.get("reprint", ""),
                "author_display_name": author.get("display_name", ""),
                "author_full_name": author.get("full_name", ""),
                "author_wos_standard": author.get("wos_standard", ""),
                "author_email": author.get("email_addr", ""),
                "author_r_id": author.get("r_id", ""),
                "author_orcid_id": author.get("orcid_id", ""),
                "author_addr_no": author.get("addr_no", []),
                "author_countries": author.get("countries", []),
                "author_affiliations": [address.get("full_address", "") for address in addresses],
                "author_addresses": addresses,
            }
        )
    return rows


def runExtraction(
    WOSArchivePath,
    outputDir,
    baseName,
    formats,
    maxPieceSize=10000,
    showProgress=True,
):
    outputDir = Path(outputDir)
    outputDir.mkdir(parents=True, exist_ok=True)

    errorFilePath = outputDir / f"{baseName}_errors.log"
    errorFile = open(errorFilePath, "wt", encoding="utf-8")

    mainWriter = None
    extraWriter = None
    abstractWriter = None
    referencesWriter = None
    authorsWriter = None

    try:
        with dbgz.DBGZReader(WOSArchivePath) as fd:
            iterator = fd.entries
            if showProgress:
                iterator = tqdm(fd.entries, total=fd.entriesCount)

            for wosEntry in iterator:
                try:
                    fieldsData = wos.utilities.getAllFields(wosEntry)

                    if mainWriter is None:
                        tsvFields = [key for key in fieldsData.keys() if len(key) == 2 and key != "AB"]
                        extraFields = ["UT"] + [
                            key for key in fieldsData.keys() if len(key) == 3 and key != "AB"
                        ]
                        abstractFields = ["UT", "AB"]
                        referencesFields = ["Citing", "Cited"]
                        authorFields = [
                            "UT",
                            "author_seq_no",
                            "author_role",
                            "author_reprint",
                            "author_display_name",
                            "author_full_name",
                            "author_wos_standard",
                            "author_email",
                            "author_r_id",
                            "author_orcid_id",
                            "author_addr_no",
                            "author_countries",
                            "author_affiliations",
                            "author_addresses",
                        ]

                        mainWriter = ProcessedTableWriter(
                            outputDir, baseName, "main", tsvFields, formats, maxPieceSize=maxPieceSize
                        )
                        extraWriter = ProcessedTableWriter(
                            outputDir,
                            baseName,
                            "extra",
                            extraFields,
                            formats,
                            maxPieceSize=maxPieceSize,
                        )
                        abstractWriter = ProcessedTableWriter(
                            outputDir,
                            baseName,
                            "abstract",
                            abstractFields,
                            formats,
                            maxPieceSize=maxPieceSize,
                        )
                        referencesWriter = ProcessedTableWriter(
                            outputDir,
                            baseName,
                            "references",
                            referencesFields,
                            formats,
                            maxPieceSize=maxPieceSize,
                        )
                        authorsWriter = ProcessedTableWriter(
                            outputDir,
                            baseName,
                            "authors",
                            authorFields,
                            formats,
                            maxPieceSize=maxPieceSize,
                        )

                    uid = fieldsData["UT"]
                    mainRow = {key: fieldsData[key] for key in tsvFields}
                    extraRow = {key: fieldsData[key] for key in extraFields}

                    mainWriter.writeRow(mainRow, rowId=uid)
                    extraWriter.writeRow(extraRow, rowId=uid)

                    if fieldsData["AB"]:
                        abstractRow = {"UT": uid, "AB": fieldsData["AB"]}
                        abstractWriter.writeRow(abstractRow, rowId=uid)

                    for toUID in fieldsData["CI"]:
                        if toUID:
                            referencesWriter.writeRow({"Citing": uid, "Cited": toUID}, rowId=f"{uid}->{toUID}")

                    for authorRow in buildAuthorRows(uid, fieldsData.get("AUR", [])):
                        authorRowId = f"{uid}:{authorRow['author_seq_no']}"
                        authorsWriter.writeRow(authorRow, rowId=authorRowId)
                except KeyboardInterrupt:
                    raise
                except Exception as error:
                    print(str(error))
                    errorFile.write(
                        str(wosEntry["UID"]) + "\t" + str(error).replace("\n", "  ") + "\n"
                    )
    finally:
        if mainWriter is not None:
            mainWriter.close()
        if extraWriter is not None:
            extraWriter.close()
        if abstractWriter is not None:
            abstractWriter.close()
        if referencesWriter is not None:
            referencesWriter.close()
        if authorsWriter is not None:
            authorsWriter.close()
        errorFile.close()


def parseArgs():
    parser = argparse.ArgumentParser(
        description="Extract processed WOS tables (main/extra/abstract/references/authors) from a raw DBGZ archive."
    )
    parser.add_argument("--archive", required=True, help="Input WoS raw .dbgz archive path")
    parser.add_argument("--output-dir", required=True, help="Output directory for processed tables")
    parser.add_argument("--base-name", default="WoS", help="Base name for generated files")
    parser.add_argument(
        "--formats",
        nargs="+",
        default=["tsv"],
        choices=["tsv", "csv", "parquet", "dbgz"],
        help="Output formats to generate (one or more)",
    )
    parser.add_argument(
        "--max-piece-size",
        type=int,
        default=10000,
        help="Piece size for dbgz/parquet outputs",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable progress bars",
    )
    return parser.parse_args()


def main():
    args = parseArgs()
    runExtraction(
        WOSArchivePath=Path(args.archive),
        outputDir=Path(args.output_dir),
        baseName=args.base_name,
        formats=args.formats,
        maxPieceSize=args.max_piece_size,
        showProgress=not args.no_progress,
    )


if __name__ == "__main__":
    main()
