
import zipfile
import gzip
from pathlib import Path
import multiprocessing as mp
import time
import os
import traceback
from datetime import datetime
import warnings

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
    if len(arguments) == 2:
        xmlFileName, WOSZipPath = arguments
        workerLogDir = None
    else:
        xmlFileName, WOSZipPath, workerLogDir = arguments
    baseName = WOSZipPath.stem

    def workerLog(message):
        if not workerLogDir:
            return
        try:
            logDirPath = Path(workerLogDir)
            logDirPath.mkdir(parents=True, exist_ok=True)
            pid = os.getpid()
            logPath = logDirPath / f"worker_{pid}.log"
            timestamp = datetime.utcnow().isoformat(timespec="seconds") + "Z"
            with open(logPath, "a", encoding="utf-8") as logfd:
                logfd.write(f"[{timestamp}] {message}\n")
        except Exception:
            pass

    workerLog(f"START zip={WOSZipPath.name} xml={xmlFileName}")
    try:
        with zipfile.ZipFile(WOSZipPath, 'r') as zipfd:
            with zipfd.open(xmlFileName) as xmlgzfd:
                with gzip.GzipFile(fileobj=xmlgzfd, mode="r") as xmlfd:
                    dataDict = xmltodict.parse(xmlfd, dict_constructor=dict)["records"]["REC"]
        workerLog(
            "READ_DONE zip=%s xml=%s"
            % (WOSZipPath.name, xmlFileName)
        )
        if isinstance(dataDict, dict):
            dataDict = [dataDict]
        for rec in dataDict:
            rec["origin"] = baseName
        workerLog(
            "DONE zip=%s xml=%s records=%d"
            % (WOSZipPath.name, xmlFileName, len(dataDict))
        )
        return dataDict
    except KeyboardInterrupt:
        workerLog(f"INTERRUPTED zip={WOSZipPath.name} xml={xmlFileName}")
        raise
    except Exception as exc:
        workerLog(
            "ERROR zip=%s xml=%s error=%s\n%s"
            % (WOSZipPath.name, xmlFileName, str(exc), traceback.format_exc())
        )
        raise RuntimeError(
            "worker pid=%s zip=%s xml=%s error=%s"
            % (os.getpid(), WOSZipPath.name, xmlFileName, str(exc))
        ) from exc


def _streamWOSXMLRecords(xmlFileName, WOSZipPath, onRecord, workerLogDir=None):
    """Stream records from a single ``.xml.gz`` member and dispatch each record.

    Parameters
    ----------
    xmlFileName : str
        Member path inside ``WOSZipPath``.
    WOSZipPath : pathlib.Path
        Path to source WoS ``.zip`` archive.
    onRecord : callable
        Callback receiving one parsed record dictionary at a time.
    workerLogDir : str or pathlib.Path or None
        Optional directory for parser logs.

    Returns
    -------
    int
        Number of parsed records.
    """
    baseName = Path(WOSZipPath).stem

    def workerLog(message):
        if not workerLogDir:
            return
        try:
            logDirPath = Path(workerLogDir)
            logDirPath.mkdir(parents=True, exist_ok=True)
            pid = os.getpid()
            logPath = logDirPath / f"worker_{pid}.log"
            timestamp = datetime.utcnow().isoformat(timespec="seconds") + "Z"
            with open(logPath, "a", encoding="utf-8") as logfd:
                logfd.write(f"[{timestamp}] {message}\n")
        except Exception:
            pass

    recordCount = 0
    workerLog(f"STREAM_START zip={Path(WOSZipPath).name} xml={xmlFileName}")
    try:
        with zipfile.ZipFile(WOSZipPath, 'r') as zipfd:
            with zipfd.open(xmlFileName) as xmlgzfd:
                with gzip.GzipFile(fileobj=xmlgzfd, mode="r") as xmlfd:

                    def callback(_, record):
                        nonlocal recordCount
                        if isinstance(record, dict):
                            record["origin"] = baseName
                            onRecord(record)
                            recordCount += 1
                        return True

                    xmltodict.parse(
                        xmlfd,
                        dict_constructor=dict,
                        item_depth=2,
                        item_callback=callback,
                    )
        workerLog(
            "STREAM_DONE zip=%s xml=%s records=%d"
            % (Path(WOSZipPath).name, xmlFileName, recordCount)
        )
    except Exception as exc:
        workerLog(
            "STREAM_ERROR zip=%s xml=%s error=%s\n%s"
            % (Path(WOSZipPath).name, xmlFileName, str(exc), traceback.format_exc())
        )
        raise RuntimeError(
            "stream parser pid=%s zip=%s xml=%s error=%s"
            % (os.getpid(), Path(WOSZipPath).name, xmlFileName, str(exc))
        ) from exc

    return recordCount


def _iter_wos_entries(
    WOSPath,
    ncpu=None,
    showProgressbar=True,
    xmlTimeoutSeconds=None,
    heartbeatSeconds=120,
    workerLogDir=None,
):
    WOSPath = Path(WOSPath)
    WOSZipPaths = sorted(list(WOSPath.glob("*.zip")))

    if ncpu in (None, -1, 0):
        ncpu = max(1, mp.cpu_count())
    else:
        ncpu = max(1, int(ncpu))

    if xmlTimeoutSeconds is not None and float(xmlTimeoutSeconds) <= 0:
        xmlTimeoutSeconds = None
    if heartbeatSeconds is None:
        heartbeatSeconds = 120
    heartbeatSeconds = max(5, int(heartbeatSeconds))

    with mp.Pool(processes=ncpu) as pool:
        zipIterator = WOSZipPaths
        if showProgressbar:
            zipIterator = tqdm(zipIterator, desc="Zip files")
        for WOSZipPath in zipIterator:
            baseName = WOSZipPath.stem
            with zipfile.ZipFile(WOSZipPath, 'r') as zipfd:
                xmlParameters = [
                    (filename, WOSZipPath, workerLogDir)
                    for filename in zipfd.namelist()
                    if filename.endswith(".xml.gz")
                ]

            asyncResults = {
                xmlParams[0]: pool.apply_async(parseWOSXML, (xmlParams,))
                for xmlParams in xmlParameters
            }
            startedAt = {xmlParams[0]: time.monotonic() for xmlParams in xmlParameters}
            pending = set(asyncResults.keys())

            xmlProgress = None
            if showProgressbar:
                xmlProgress = tqdm(
                    total=len(xmlParameters),
                    desc="Parsing %s" % baseName,
                    leave=False,
                )

            lastHeartbeat = 0.0
            while pending:
                completedNow = []
                for filename in list(pending):
                    task = asyncResults[filename]
                    if task.ready():
                        completedNow.append(filename)

                if completedNow:
                    for filename in completedNow:
                        task = asyncResults[filename]
                        pending.remove(filename)
                        try:
                            dataDict = task.get()
                        except KeyboardInterrupt:
                            raise
                        except Exception as exc:
                            raise RuntimeError(
                                "Failed parsing XML '%s' inside '%s': %s"
                                % (filename, baseName, str(exc))
                            ) from exc
                        if xmlProgress is not None:
                            xmlProgress.update(1)
                        for entry in dataDict:
                            yield entry
                    continue

                now = time.monotonic()
                if xmlTimeoutSeconds is not None:
                    oldestFile = None
                    oldestElapsed = -1.0
                    for filename in pending:
                        elapsed = now - startedAt[filename]
                        if elapsed > oldestElapsed:
                            oldestElapsed = elapsed
                            oldestFile = filename
                    if oldestElapsed > float(xmlTimeoutSeconds):
                        raise TimeoutError(
                            "Timeout while parsing XML '%s' in '%s' (%.1fs > %.1fs). "
                            "Use --xml-timeout-seconds to increase/disable timeout."
                            % (
                                oldestFile,
                                baseName,
                                oldestElapsed,
                                float(xmlTimeoutSeconds),
                            )
                        )

                if now - lastHeartbeat >= heartbeatSeconds:
                    oldestFile = None
                    oldestElapsed = -1.0
                    for filename in pending:
                        elapsed = now - startedAt[filename]
                        if elapsed > oldestElapsed:
                            oldestElapsed = elapsed
                            oldestFile = filename
                    print(
                        "[archive] %s pending_xml=%d/%d oldest=%s elapsed=%.1fs"
                        % (
                            baseName,
                            len(pending),
                            len(xmlParameters),
                            oldestFile,
                            oldestElapsed,
                        ),
                        flush=True,
                    )
                    lastHeartbeat = now

                time.sleep(0.5)

            if xmlProgress is not None:
                xmlProgress.close()


def create(WOSPath,
           WOSArchivePath,
           outputFormat="dbgz",
           parquetPath=None,
           ncpu=None,
           maxPieceSize=10000,
           showProgressbar=True,
           xmlTimeoutSeconds=None,
           heartbeatSeconds=120,
           workerLogDir=None):
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
        Progressive saver chunk size. Lower values reduce peak memory.
    showProgressbar : bool
        If True, print progress bars.
    xmlTimeoutSeconds : float or None
        Optional timeout in seconds for parsing a single XML inside a zip file.
        ``None`` disables timeout.
    heartbeatSeconds : int
        Interval in seconds for heartbeat logs while waiting for XML workers.
    workerLogDir : pathlib.Path or str or None
        Optional directory where each worker writes task logs to files named
        ``worker_<pid>.log``.

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

    maxPieceSize = max(1, int(maxPieceSize))

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

        if ncpu not in (None, 0, 1):
            warnings.warn(
                "create() now enforces streaming XML parsing in-process to avoid memory spikes; "
                "ncpu is ignored in this mode.",
                RuntimeWarning,
            )

        WOSPath = Path(WOSPath)
        WOSZipPaths = sorted(list(WOSPath.glob("*.zip")))

        zipIterator = WOSZipPaths
        if showProgressbar:
            zipIterator = tqdm(zipIterator, desc="Zip files")

        for WOSZipPath in zipIterator:
            baseName = WOSZipPath.stem
            with zipfile.ZipFile(WOSZipPath, 'r') as zipfd:
                xmlFiles = [
                    filename
                    for filename in zipfd.namelist()
                    if filename.endswith(".xml.gz")
                ]

            xmlIterator = xmlFiles
            if showProgressbar:
                xmlIterator = tqdm(xmlFiles, desc="Parsing %s" % baseName, leave=False)

            for xmlFileName in xmlIterator:

                def onRecord(entry):
                    uid = entry.get("UID", "")
                    if dbgzSaver is not None:
                        dbgzSaver.add(UID=uid, data=entry)
                    if parquetSaver is not None:
                        parquetSaver.add(UID=uid, data=ujson.dumps(entry))

                _streamWOSXMLRecords(
                    xmlFileName,
                    WOSZipPath,
                    onRecord=onRecord,
                    workerLogDir=workerLogDir,
                )
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