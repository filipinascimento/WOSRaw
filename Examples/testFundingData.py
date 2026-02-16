
from pathlib import Path
from timeit import default_timer as timer
import dbgz
from tqdm.auto import tqdm
import WOSRaw as wos
import importlib 
importlib.reload(wos)

# Path to the existing dbgz file
WOSArchivePath = Path("/mnt/sciencegenome/WOS_DBGZ/WoS_2023_All.dbgz")


# Reading the file sequentially
with dbgz.DBGZReader(WOSArchivePath) as fd:
    # getting the number of entries
    print("\t Number of entries: ", fd.entriesCount)
    # getting the schema (currently UID and data)
    print("\t Scheme: ", fd.scheme)
    # TQDM can be used to print the progressbar
    for wosEntry in tqdm(fd.entries, total=fd.entriesCount):
        wos.utilities.getTitle(wosEntry)
        fundingData = wos.utilities.getFunding(wosEntry)
        funding = wos.utilities.formatFundingWOS(fundingData)
        if(fundingData):
            print("------")
            print(fundingData)
            print(funding)
            print("------")
            # ask for input enter continue q exit
            userInput = input("Press enter to continue or q to exit: ")
            if(userInput == "q"):
                break
