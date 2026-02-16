
import zipfile
import gzip
from pathlib import Path
import multiprocessing as mp

import dbgz
import xmltodict
import ujson
from tqdm.auto import tqdm

try:
    from parcake import PieceSaver
except Exception:  # pragma: no cover
    PieceSaver = None

# Code to create a Web of Science dbgz archive from the 
# raw XML files.


#Path to the WoS zipped XML files 
# WOSPath = Path("/raw/WoS_2022/")

# #Path to the WoS dbgz archive
# WOSSavePath = Path("/raw/WoS_2022_DBGZ/WoS_2022_All.dbgz")

def parseWOSXML(arguments):
    xmlFileName, WOSZipPath = arguments
    baseName = WOSZipPath.stem
    with zipfile.ZipFile(WOSZipPath, 'r') as zipfd:
        with zipfd.open(xmlFileName) as xmlgzfd:
            with gzip.GzipFile(fileobj=xmlgzfd, mode="r") as xmlfd:
                xmlData = xmlfd.read()
    dataDict = xmltodict.parse(xmlData, dict_constructor=dict)["records"]["REC"]
    if isinstance(dataDict, dict):
        dataDict = [dataDict]
    for rec in dataDict:
        rec["origin"] = baseName
    return dataDict


def _iter_wos_entries(WOSPath, ncpu=None, showProgressbar=True):
    WOSPath = Path(WOSPath)
    WOSZipPaths = sorted(list(WOSPath.glob("*.zip")))

    if ncpu in (None, -1, 0):
        ncpu = max(1, mp.cpu_count())
    else:
        ncpu = max(1, int(ncpu))

    with mp.Pool(processes=ncpu) as pool:
        zipIterator = WOSZipPaths
        if showProgressbar:
            zipIterator = tqdm(zipIterator, desc="Zip files")
        for WOSZipPath in zipIterator:
            baseName = WOSZipPath.stem
            with zipfile.ZipFile(WOSZipPath, 'r') as zipfd:
                xmlParameters = [
                    (filename, WOSZipPath)
                    for filename in zipfd.namelist()
                    if filename.endswith(".xml.gz")
                ]

            xmlIterator = pool.imap_unordered(parseWOSXML, xmlParameters)
            if showProgressbar:
                xmlIterator = tqdm(
                    xmlIterator,
                    total=len(xmlParameters),
                    desc="Parsing %s" % baseName,
                    leave=False,
                )

            for dataDict in xmlIterator:
                for entry in dataDict:
                    yield entry


def create(WOSPath,
           WOSArchivePath,
           outputFormat="dbgz",
           parquetPath=None,
           ncpu=None,
           maxPieceSize=100000,
           showProgressbar=True):
    """
    Create archives from raw WOS XML files.

    Parameters
    ----------
    WOSPath : pathlib.Path or str
        Path to the WoS zipped XML files.
    WOSArchivePath : pathlib.Path or str
        Path to generate the WoS dbgz archive.
    outputFormat : str
        One of: ``"dbgz"``, ``"parquet"``, ``"both"``.
    parquetPath : pathlib.Path or str
        Optional parquet output path. Required when outputFormat includes parquet.
    ncpu : int
        Number of workers for XML parsing. ``None`` uses all CPUs.
    maxPieceSize : int
        Progressive saver chunk size.
    showProgressbar : bool
        If True, print progress bars.

    Notes
    -----
    This function uses multiprocessing to speed up the process. Thus,
    it is critical to include the check for main in the code:

    if __name__ == "__main__":
        WOSRaw.create(WOSPath, WOSArchivePath)
        ...

    """
    scheme = [
        ("UID", "s"),
        ("data", "a"),
    ]

    outputFormat = str(outputFormat).lower()
    if outputFormat not in {"dbgz", "parquet", "both"}:
        raise ValueError("outputFormat must be one of: 'dbgz', 'parquet', 'both'")

    wantsDBGZ = outputFormat in {"dbgz", "both"}
    wantsParquet = outputFormat in {"parquet", "both"}

    if wantsParquet and PieceSaver is None:
        raise RuntimeError("parcake is required for parquet output. Please install parcake.")

    WOSArchivePath = Path(WOSArchivePath)
    if parquetPath is None and wantsParquet:
        parquetPath = WOSArchivePath.with_suffix(".parquet")
    if parquetPath is not None:
        parquetPath = Path(parquetPath)

    dbgzSaver = None
    parquetSaver = None
    try:
        if wantsDBGZ:
            dbgzSaver = dbgz.DBGZPieceSaver(
                scheme,
                str(WOSArchivePath.resolve()),
                max_piece_size=maxPieceSize,
                show_progressbar=showProgressbar,
            )
        if wantsParquet:
            header = {
                "UID": "str",
                "data": "str",
            }
            parquetSaver = PieceSaver(
                header,
                str(parquetPath),
                max_piece_size=maxPieceSize,
            )

        for entry in _iter_wos_entries(WOSPath, ncpu=ncpu, showProgressbar=showProgressbar):
            uid = entry.get("UID", "")
            if dbgzSaver is not None:
                dbgzSaver.add(UID=uid, data=entry)
            if parquetSaver is not None:
                parquetSaver.add(UID=uid, data=ujson.dumps(entry))
    finally:
        if dbgzSaver is not None:
            dbgzSaver.close()
        if parquetSaver is not None:
            parquetSaver.close()

    return {
        "dbgz": str(WOSArchivePath.resolve()) if wantsDBGZ else None,
        "parquet": str(parquetPath.resolve()) if wantsParquet else None,
    }


def createIndexByUID(WOSArchivePath,WOSArchiveIndexPath):
    """
    Create a dbgz index archive from the raw WOS XML files.
    
    Parameters
    ----------
    WOSArchivePath : pathlib.Path or str
        Path to the WoS dbgz archive.
    WOSArchiveIndexPath : pathlib.Path or str
        Path to generate the WoS dbgz index archive.
    
    """
    print("Saving the index dictionary")
    with dbgz.DBGZReader(WOSArchivePath) as fd:
        fd.generateIndex(key="UID",
                        indicesPath=WOSArchiveIndexPath,
                        useDictionary=False,
                        showProgressbar=True
                        )


class readDBGZ:
    """
    Chunk reader for WOS DBGZ archives using ``dbgz.DBGZPieceReader``.
    """

    def __init__(self, archivePath, chunksize=5000, output="dict", showProgressbar=False):
        self.archivePath = Path(archivePath)
        self.chunksize = int(chunksize)
        self.output = output
        self.showProgressbar = showProgressbar

        with dbgz.DBGZReader(self.archivePath) as fd:
            self.entriesCount = fd.entriesCount
        self._reader = dbgz.DBGZPieceReader(
            str(self.archivePath),
            chunk_size=self.chunksize,
            output=self.output,
            show_progressbar=self.showProgressbar,
        )
        self.chunksCount = self._reader.task_count()

    @property
    def chunks(self):
        return iter(self._reader)

    @property
    def entries(self):
        for chunk in self._reader:
            if self.output == "dataframe":
                for entry in chunk.to_dict(orient="records"):
                    yield entry
            else:
                for entry in chunk:
                    yield entry