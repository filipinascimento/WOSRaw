
import dbgz
from pathlib import Path
from tqdm.auto import tqdm
from pathlib import Path
import sys
import ujson

from collections import OrderedDict
from collections import Counter
import collections 
if sys.version_info.major == 3 and sys.version_info.minor >= 10:

    from collections.abc import MutableMapping
else:
    from collections import MutableMapping


# WOSArchivePath = Path("//home/filsilva/WOS/WoS_2022_All.dbgz")


# # Path to where to save the schema files
# schemaPath = Path("Schema")

# # Path to where to save the reports files
# reportsPath = Path("Reports")

# schemaPath.mkdir(parents=True, exist_ok=True)
# reportsPath.mkdir(parents=True, exist_ok=True)


def createSchemaAndReportFile(WOSArchivePath, schemaPath=Path("Schema"), reportsPath=Path("Reports"),
                              mostCommon=5, saveEach=100000, minPercentageFilter=0):
    """
    Create a schema file and a report file for a given WOS raw dbgz file.
    The schema is a machine readable json files while the report is a 
    human readable txt file.

    Parameters
    ----------
    WOSArchivePath : pathlib.Path or str
        Path to the WOS raw dbgz file.
    schemaPath : pathlib.Path or str, optional
        Path to where to save the schema files, by default Path("Schema")
    reportsPath : pathlib.Path or str, optional 
        Path to where to save the reports files, by default Path("Reports")
    mostCommon : int, optional
        Number of most common values to save in the report, by default 5
    saveEach : int, optional
        Save the schema and report files every saveEach entries, by default 100000
    minPercentageFilter : int, optional
        Minimum percentage of values for a given field to be saved in the report, by default 0
    """

    WOSArchivePath = Path(WOSArchivePath)
    schemaPath = Path(schemaPath)
    reportsPath = Path(reportsPath)
    reportPath = reportsPath/("report_WOS.txt")

    schemaPath.mkdir(parents=True, exist_ok=True)
    reportsPath.mkdir(parents=True, exist_ok=True)

    def saveReport():
        if (reportPath is not None):
            with open(reportPath, "w") as file:
                _printSchema(schemaData,
                             file=file,
                             mostCommon=mostCommon,
                             minPercentageFilter=minPercentageFilter)

    def cleanScheme(schemaEntry):
        for key, value in schemaEntry.items():
            if (key == "$count"):
                continue
            if ("$samples" in value):
                del value["$samples"]
            if ("$listSamples" in value):
                del value["$listSamples"]
            if ("$listSamples" in value):
                del value["$listSamples"]
            if ("$schemaEntry" in value):
                if (value["$schemaEntry"]):
                    cleanScheme(value["$schemaEntry"])
                else:
                    del value["$schemaEntry"]

    def basicTypeName(obj):
        if (isinstance(obj, str)):
            return "string"
        elif (isinstance(obj, (int, float, complex)) and not isinstance(obj, bool)):
            return "number"
        elif (isinstance(obj, bool)):
            return "bool"
        elif (isinstance(obj, list)):
            return "list"
        else:
            return type(obj).__name__

    def _flatten(d, parent_key=""):
        items = []
        for k, v in d.items():
            if (k == "abstract_text" and v):
                v = "<ABSTRACT>"  # avoid large abstracts in the schema when not null
            k = k.replace(":", "_")  # no ":" allowed in keys
            new_key = parent_key+":"+str(k) if parent_key else str(k)
            if isinstance(v, MutableMapping):
                items.extend(_flatten(v, new_key).items())
            else:
                items.append((new_key, v))
        return dict(items)

    def _addToSchema(schemaData, entryData, flatDict=True, maxSamples=100):
        if (flatDict):
            entryData = _flatten(entryData)
        if "$count" not in schemaData:
            schemaData["$count"] = 0
        schemaData["$count"] += 1
        for key, value in entryData.items():
            if (key not in schemaData):
                schemaData[key] = {
                    "$count": 0,
                    "$samples": Counter(),
                    "$listSamples": Counter(),
                    "$schemaEntry": OrderedDict(),
                    "$types": Counter()
                }
            if not value:
                continue
            schemaData[key]["$count"] += 1
            schemaData[key]["$types"][basicTypeName(value)] += 1
            if (not isinstance(value, list)):
                if (len(schemaData[key]["$samples"]) < maxSamples):
                    schemaData[key]["$samples"][value] += 1
                else:
                    if (value in schemaData[key]["$samples"]):
                        schemaData[key]["$samples"][value] += 1
            else:
                for entry in value:
                    if (isinstance(entry, dict)):
                        _addToSchema(
                            schemaData[key]["$schemaEntry"], entry, flatDict=flatDict, maxSamples=maxSamples)
                    else:
                        if (len(schemaData[key]["$listSamples"]) < maxSamples):
                            schemaData[key]["$listSamples"][entry] += 1
                        else:
                            if (entry in schemaData[key]["$listSamples"]):
                                schemaData[key]["$listSamples"][entry] += 1

    def _percentageText(percentage):
        percentageText = "%.2f%%" % percentage
        if (percentage < 0.01):
            percentageText = " < 0.01%"
        return percentageText

    def _printSchema(schemaEntry, indent=0, mostCommon=5, minPercentageFilter=0, file=sys.stdout):
        for key, value in schemaEntry.items():
            if (key == "$count"):
                print(" "*indent + str(value)+" ENTRIES", file=file)
                continue
            entriesCount = schemaEntry["$count"]
            if (value["$count"]/entriesCount*100 < minPercentageFilter):
                continue
            # if key instance of tuple
            keyLabel = key
            if (isinstance(key, tuple)):
                keyLabel = ":".join(key)
            print((" "*indent)+keyLabel, file=file)
            print((" "*(indent+2))+"Count: %d (%s)" %
                  (value["$count"], _percentageText(value["$count"]/entriesCount*100)), file=file)
            typesStringArray = []
            for sampleItem, sampleCount in value["$types"].most_common(mostCommon):
                typesStringArray.append("%s (%s)" % (
                    sampleItem,
                    _percentageText(sampleCount/value["$count"]*100)))
            if (len(value["$types"]) > mostCommon):
                typesStringArray.append("...")
            print((" "*(indent+2))+"Types: " +
                  ", ".join(typesStringArray), file=file)
            if (value["$samples"]):
                print(" "*(indent+2)+"Samples:", file=file)
                for sampleItem, sampleCount in value["$samples"].most_common(mostCommon):
                    print((" "*(indent+4))+"%d (%s): %s" % (sampleCount,
                                                            _percentageText(sampleCount/value["$count"]*100), sampleItem), file=file)
                if (len(value["$samples"]) > mostCommon):
                    print((" "*(indent+4))+"...", file=file)
            if (value["$listSamples"]):
                print(" "*(indent+2)+"List Samples:", file=file)
                for sampleItem, sampleCount in value["$listSamples"].most_common(mostCommon):
                    print((" "*(indent+4))+"%d (%s): %s" % (sampleCount,
                                                            _percentageText(sampleCount/value["$count"]*100), sampleItem), file=file)
                if (len(value["$listSamples"]) > mostCommon):
                    print((" "*(indent+4))+"...", file=file)
            if (value["$schemaEntry"]):
                print(" "*(indent+2)+"Schema Entry:", file=file)
                _printSchema(value["$schemaEntry"], indent +
                             4, mostCommon=5, file=file)

    # authors  concepts  institutions  venues  works

    with dbgz.DBGZReader(WOSArchivePath) as fd:
        schemaData = OrderedDict()
        entityCount = 0
        for entity in tqdm(fd.entries, total=fd.entriesCount):
            _addToSchema(schemaData, entity["data"])
            if (entityCount > 0 and entityCount % saveEach == 0):
                saveReport()
            entityCount += 1
        saveReport()

    with open(schemaPath/("schema_WOS_samples.json"), "wt") as f:
        ujson.dump(schemaData, f, ensure_ascii=False, indent=4)
    cleanScheme(schemaData)
    with open(schemaPath/("schema_WOS.json"), "wt") as f:
        ujson.dump(schemaData, f, ensure_ascii=False, indent=4)
