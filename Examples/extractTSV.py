import dbgz
from pathlib import Path
from tqdm.auto import tqdm
import WOSRaw as wos
import ujson

WOSArchivePath = Path("/mnt/sciencegenome/WOS_DBGZ/WoS_2023_All.dbgz")



WOSTSVPath = Path("/mnt/sciencegenome/WOS_TSV_2023/WoS_2023.tsv")
WOSTSVExtraDataPath = Path("/mnt/sciencegenome/WOS_TSV_2023/WoS_2023_extra.tsv")
WOSTSVAbstractPath = Path("/mnt/sciencegenome/WOS_TSV_2023/WoS_2023_abstract.tsv")
WOSTSVReferencesPath = Path("/mnt/sciencegenome/WOS_TSV_2023/WoS_2023_references.tsv")

errorFilePath = Path("errors.log")



tsvFile = open(WOSTSVPath, "wt", encoding="utf-8")
tsvExtraDataFile = open(WOSTSVExtraDataPath, "wt", encoding="utf-8")
tsvAbstractFile = open(WOSTSVAbstractPath, "wt", encoding="utf-8")
tsvReferencesFile = open(WOSTSVReferencesPath, "wt", encoding="utf-8")
errorFile = open(errorFilePath, "wt", encoding="utf-8")


def parseEntry(entry,separator = ";"):
    if(isinstance(entry,list)):
        return (separator+" ").join([v.replace(separator,",.") for v in entry]).replace("\t","    ")
    else:
        return entry.replace("\t","    ")

header=True
with dbgz.DBGZReader(WOSArchivePath) as fd:
    for wosEntry in tqdm(fd.entries, total=fd.entriesCount):
        try:
            fieldsData = wos.utilities.getAllFields(wosEntry)
            if(header):
                tsvFields = [key for key in fieldsData.keys() if len(key)==2 and key!="AB"]
                extraFields = ["UT"]+[key for key in fieldsData.keys() if len(key)==3 and key!="AB"]
                abstractFields = ["UT","AB"]
                referencesFields = ["Citing","Cited"]
                tsvFile.write("\t".join(tsvFields)+"\n")
                tsvExtraDataFile.write("\t".join(extraFields)+"\n")
                tsvAbstractFile.write("\t".join(abstractFields)+"\n")
                tsvReferencesFile.write("\t".join(referencesFields)+"\n")
                header=False
            tsvLine = "\t".join([parseEntry(fieldsData[key]) for key in tsvFields]).replace("\n","  ")+"\n"
            tsvFile.write(tsvLine)
            tsvExtraDataLine = "\t".join([ujson.dumps(fieldsData[key]) for key in extraFields]).replace("\n","  ")+"\n"
            tsvExtraDataFile.write(tsvExtraDataLine)
            if(fieldsData["AB"]):
                tsvAbstractLine = "\t".join([parseEntry(fieldsData[key],separator="|") for key in abstractFields]).replace("\n","  ")+"\n"
                tsvAbstractFile.write(tsvAbstractLine)
            fromUID = fieldsData["UT"]
            for toUID in fieldsData["CI"]:
                if(toUID):
                    tsvReferencesLine = fromUID+"\t"+toUID+"\n"
                    tsvReferencesFile.write(tsvReferencesLine)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(str(e))
            errorFile.write(str(wosEntry["UID"])+"\t"+str(e).replace("\n","  ")+"\n")




# Closing files
tsvFile.close()
tsvExtraDataFile.close()
tsvAbstractFile.close()
tsvReferencesFile.close()
errorFile.close()
