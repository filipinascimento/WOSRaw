



import zipfile
import gzip
from pathlib import Path
import dbgz
from tqdm.auto import tqdm
import multiprocessing as mp
import xmltodict

# Code to create a Web of Science dbgz archive from the 
# raw XML files.


#Path to the WoS zipped XML files 
# WOSPath = Path("/raw/WoS_2022/")

# #Path to the WoS dbgz archive
# WOSSavePath = Path("/raw/WoS_2022_DBGZ/WoS_2022_All.dbgz")

def parseWOSXML(arguments):
    xmlFileName,WOSZipPath, = arguments
    baseName = WOSZipPath.stem
    with zipfile.ZipFile(WOSZipPath, 'r') as zipfd:
        with zipfd.open(xmlFileName) as xmlgzfd:
            with gzip.GzipFile(fileobj=xmlgzfd,mode="r") as xmlfd:
                xmlData = xmlfd.read()
    dataDict = xmltodict.parse(xmlData,dict_constructor=dict)["records"]["REC"]
    for rec in dataDict:
        rec["origin"] = baseName
    return dataDict

def create(WOSPath, WOSArchivePath):
    """
    Create a dbgz archive from the raw WOS XML files.

    Parameters
    ----------
    WOSPath : pathlib.Path or str
        Path to the WoS zipped XML files.
    WOSArchivePath : pathlib.Path or str
        Path to generate the WoS dbgz archive.

    Notes
    -----
    This function uses multiprocessing to speed up the process. Thus,
    it is critical to include the check for main in the code:

    if __name__ == "__main__":
        WOSRaw.create(WOSPath, WOSArchivePath)
        ...

    """
    WOSZipPaths = sorted(list(WOSPath.glob("*.zip")))

    scheme = [
        ("UID", "s"),
        ("data", "a"),
    ]



    num_processors = mp.cpu_count()//8
    pool = mp.Pool(processes=num_processors)
    
    with dbgz.DBGZWriter(WOSArchivePath.resolve(), scheme) as dbgzfd:
        for WOSZipPath in tqdm(WOSZipPaths, desc="Zip files"):
            baseName = WOSZipPath.stem
            with zipfile.ZipFile(WOSZipPath, 'r') as zipfd:
                xmlParameters = [(filename,WOSZipPath) for filename in zipfd.namelist() if filename.endswith(".xml.gz")]
            for dataDict in tqdm(pool.imap_unordered(parseWOSXML, xmlParameters), total=len(xmlParameters), desc="Parsing %s"%baseName, leave=False):
            # for dataDict in pool.map(func=parseWOSXML, iterable=xmlParameters):
                for entry in dataDict:
                    dbgzfd.write(UID=entry["UID"], data=entry)
    
    print("cleaning...")
    pool.close()
    pool.join()


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