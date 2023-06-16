import dbgz
from pathlib import Path
from tqdm.auto import tqdm
import WOSRaw as wos
import ujson

WOSArchivePath = Path("//home/filsilva/WOS/WoS_2022_All.dbgz")


with open("orcid.tsv", "wt") as orcidFile:
    with open("r_id.tsv", "wt") as ridFile:
        orcidFile.write("UID\tseq_no\torcid\n")
        ridFile.write("UID\tseq_no\tr_id\n")
        with dbgz.DBGZReader(WOSArchivePath) as archive:
            for entry in tqdm(archive.entries,total=archive.entriesCount):
                if("contributors" in entry["data"]["static_data"]):
                    contributorsData = wos.utilities.getContributors(entry)
                    for contributor in contributorsData:
                        if("@orcid_id" in contributor):
                            orcidFile.write(f"{entry['UID']}\t{contributor['@seq_no']}\t{contributor['@orcid_id']}\n")
                        if("@r_id" in contributor):
                            ridFile.write(f"{entry['UID']}\t{contributor['@seq_no']}\t{contributor['@r_id']}\n")



