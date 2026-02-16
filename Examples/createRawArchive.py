
import WOSRaw as wos
from pathlib import Path


#Path to the WoS zipped XML files 
WOSPath = Path("/mnt/sciencegenome/WOS_RAW/WoS_2023/")

# Path where to save the WoS dbgz archive
WOSArchivePath = Path("/mnt/sciencegenome/WOS_DBGZ/WoS_2023_All.dbgz")

# Path to the generated 
WOSIndexPath = Path("/mnt/sciencegenome/WOS_DBGZ/WoS_2023_All_byUID.idbgz")

if __name__ == "__main__":
    wos.archive.create(WOSPath, WOSArchivePath)
    # This may take several hours to complete
    wos.archive.createIndexByUID(WOSArchivePath, WOSIndexPath)


