# %%

import numpy as np
import pandas as pd
from pathlib import Path
from tqdm.auto import tqdm
import pickle as pkl
import pandas as pd
import csv



WOSDataPath = "/gpfs/sciencegenome/WOS/WoS_2022.tsv"
WOSCitationsPath = "/gpfs/sciencegenome/WOS/WoS_2022_citations_per_year.tsv"

rawPubPath = Path("/gpfs/sciencegenome/NSF-TIP/raw/pub/")
rawFundingPath = Path("/gpfs/sciencegenome/NSF-TIP/raw/funding/")
rawDisruptionPath = Path("/gpfs/sciencegenome/NSF-TIP/derived/disrupt_top5")
preprocessedPath = Path("/gpfs/sciencegenome/NSF-TIP/preprocessed/")
disruptionPreprocessPath = Path("/gpfs/sciencegenome/NSF-TIP/raw/cd5index")


chunksize = 5000
length = 84162157

uid2Year = {}
with tqdm(total=length, desc="chunks read: ") as bar:
    # enumerate chunks read without low_memory (it is massive for pandas to precisely assign dtypes)
    for i, chunk in enumerate(pd.read_csv(WOSDataPath, chunksize=chunksize,sep="\t",encoding='utf-8',error_bad_lines=False, low_memory=False,
    quoting=csv.QUOTE_NONE)):
        for uid,year in zip(chunk["UT"].tolist(),chunk["PY"].tolist()):
            uid2Year[uid] = year
        bar.update(chunksize)


referencesFile = "/gpfs/sciencegenome/WOS/WoS_2022_references.tsv"

UID2CitationCountsPerYear = {}
# UID2CitationCountsPerYear[cited UID][Year] = citation count

from collections import Counter
import csv
chunksize = 5000
with tqdm(total=1373897063, desc="chunks read: ") as bar:
    # enumerate chunks read without low_memory (it is massive for pandas to precisely assign dtypes)
    for i, chunk in enumerate(pd.read_csv(referencesFile, chunksize=chunksize,sep="\t",encoding='utf-8', low_memory=False,quoting=csv.QUOTE_NONE)):
        for citing,cited in zip(chunk["Citing"].tolist(),chunk["Cited"].tolist()):
            if citing in uid2Year:
                citingYear = uid2Year[citing]
            else:
                citingYear = 0
            if(cited not in UID2CitationCountsPerYear):
                UID2CitationCountsPerYear[cited] = Counter()
            UID2CitationCountsPerYear[cited][citingYear] += 1
            
        bar.update(chunksize)


# saving UID2CitationCountsPerYear as a tsv with two columns: UID, CitationCountsPerYear (json)
import ujson
with open(WOSCitationsPath, "w") as f:
    f.write("UID\tCitationCountsPerYear\n")
    for uid in tqdm(UID2CitationCountsPerYear,desc="Saving TSV citations"):
        #Order by year
        jsonData = {k: v for k, v in sorted(UID2CitationCountsPerYear[uid].items(), key=lambda item: item[0])}
        f.write(f"{uid}\t{ujson.dumps(jsonData)}\n")

