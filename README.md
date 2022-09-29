# Introduction
[WOSRaw](https://github.com/filipinascimento/WOSRaw) was created to export Web of Science data from the XML files provided as yearly dumps. It uses a [DBGZ](https://github.com/filipinascimento/dbgz) file to store all the data in a compressed format.

# Installation
The package can be installed by using the following command:
```bash
python -m pip install git+https://github.com/filipinascimento/WOSRaw.git
```
The package may requires an updated version of `dbgz`:

```bash
pip install -U dbgz
```

Check the examples in https://github.com/filipinascimento/WOSRaw/tree/main/Examples

# DBGZ file
 [DBGZ](https://github.com/filipinascimento/dbgz) version provides a fast way to access the raw data. About 2 hours are needed to iterate over all the entries in sequence. The framework also provides a way to access the entries in a random order based on the `WOS ID`(UID).

Code to generate archives from the XML files and to extract information from the WOS dbgz files can be found in https://github.com/filipinascimento/WOSRaw/tree/main/Examples (more info on that is coming soon).

To create an archive from the XML files, use the following code:

```python
import WOSRaw as wos
from pathlib import Path

#Path to the WoS zipped XML files 
WOSPath = Path("/raw/WoS_2022/")

# Path where to save the WoS dbgz archive
WOSArchivePath = Path("/gpfs/sciencegenome/WOS/WoS_2022_All.dbgz")
wos.archive.create(WOSPath, WOSArchivePath)
```

# Usage
The utilities functions in `WOSRaw.utilities` can be used to get certain properties from the entries in the dbgz files. For instance:

```python
from pathlib import Path
from timeit import default_timer as timer
import dbgz
from tqdm.auto import tqdm
import WOSRaw as wos

# Path to the existing dbgz file
WOSArchivePath = Path("/gpfs/sciencegenome/WOS/WoS_2022_All.dbgz")


# Reading the file sequentially
with dbgz.DBGZReader(WOSArchivePath) as fd:
    # getting the number of entries
    print("\t Number of entries: ", fd.entriesCount)
    # getting the schema (currently UID and data)
    print("\t Scheme: ", fd.scheme)
    # TQDM can be used to print the progressbar
    for wosEntry in tqdm(fd.entries, total=fd.entriesCount):
        UID = wosEntry["UID"]
        entryData = wosEntry["data"] # XML records data
        wos.utilities.getTitle(wosEntry) # Extracting the title
        ... # do something with the data
```



## Documentation for the RAW Files
Clarivate provides documentation for the XML raw files in:
https://clarivate.libguides.com/c.php?g=593069&p=4101845

Including the Schema user guide:
https://clarivate.libguides.com/ld.php?content_id=27109663



## More usage
To iterate over all the entries, you can use the following code:

```python
from pathlib import Path
import dbgz
from tqdm.auto import tqdm
WOSArchivePath = Path("/gpfs/sciencegenome/WOS/WoS_2022_All.dbgz")

with dbgz.DBGZReader(WOSArchivePath) as fd:
    # getting the number of entries
    print("\t Number of entries: ", fd.entriesCount)
    # getting the schema (currently UID and data)
    print("\t Scheme: ", fd.scheme)
    # TQDM can be used to print the progressbar
    for entry in tqdm(fd.entries, total=fd.entriesCount):
        UID = entry["UID"]
        entryData = entry["data"] # XML records data
        ... # do something with the data
```

The entries are all based on the RAW XML and were not further processed. It contains only two fields at the first level:
- `UID`: WoS ID
- `data`: Python dictionary directly converted from the XML record (see the XML guides). The only addition is the field `origin` which stores the name of the original zip file containing this entry.


### Random access to the WoS entries
We also provide an index based on UID, which allows random access to the entries data. These dictionaries can be built using the following code:

```python
import WOSRaw as wos
from pathlib import Path

# Path to the WoS zipped XML files 
WOSPath = Path("/raw/WoS_2022/")

# Path to the generated 
WOSIndexPath = Path("/gpfs/sciencegenome/WOS/WoS_2022_All_byUID.idbgz")

# This may take several hours to complete
wos.archive.createIndexByUID(WOSArchivePath, WOSIndexPath)
```

We recommend to move the `.dbgz` and `.idbgz` files to a local storage (such as HDD or SSD), otherwise the random access can become slow.

Example usage of the index to randomly access the entries:
```python
import dbgz
from pathlib import Path
from tqdm.auto import tqdm

WOSIndexPath = Path("/gpfs/sciencegenome/WoS_2022_DBGZ/WoS_2022_All_byUID.idbgz")
print("Loading the index dictionary")
indexDictionary = dbgz.readIndicesDictionary(WOSIndexPath)
wosUID = "WOS:000200919700142" # or any other UID
with dbgz.DBGZReader(WOSArchivePath) as fd:
    wosEntry = fd.readAt(indexDictionary[wosUID][0])[0]
...
```


## Utilities functions
Here is a guide on how to use `WOSRaw.utilities` functions to get the desired data from the WoS entry:

Tags with three letters (also marked by a *) are new to WoS and include complete JSON entries in the `WoS_2022_extra.tsv`. Lists are separted by `; `.

| Tag | Description | Utility function |
| --- | --- | --- |
| PIR* | Publication Info (JSON) | `getPublicationInfo(wosEntry)` |
| PT | Publication Type: Journal, Book in series, Book, Conference | `getPublicationType(publicationInfo)` |
| ADR* | Author Data (JSON) | `getAuthors(wosEntry)` |
| AU | Authors | `getAuthorNames(authorData,"wos_standard")` |
| BA |  Book Authors | `# TODO Not sure how to get it should be the same as AU` |
| BE | Book Editors | `getAuthorNames(getAuthors(wosEntry,roles={"book_editor"}),"wos_standard")` |
| BA | Book Author Groups | `# TODO Not sure how to get it` |
| AF | Authors Full Name | ` getAuthorNames(authorData,"full_name")` |
| BF | Book Authors Full Name | `# TODO Not sure how to get it should be the same as AF` |
| CA | Group Authors | `# TODO Not sure how to get it` |
| GP | Group Authors? | `# TODO Not sure how to get it` |
| TI | Title | `getTitle(wosEntry)` |
| SOR* | Sources Data (JSON) | `getSources(wosEntry)` |
| SO | Publication Name | `getPublicationName(sourcesData)` |
| SE | Book Series Title | `getBookSeriesTitle(sourcesData)` |
| LA | Language | `getPrimaryLanguage(wosEntry)` |
| DT | Document Type | `getDocTypes(wosEntry)` |
| CT | Conference Title | `getConferencesTitles(getConferences(wosEntry))` |
| CY | Conference Dates | `getConferencesDates(getConferences(wosEntry))` |
| CL | Conference Locations | `getConferencesLocations(getConferences(wosEntry))` |
| SP | Conference Sponsors | `getConferenceSponsors(getConferences(wosEntry))` |
| HO | Conference Hosts | `getConferencesHosts(getConferences(wosEntry))` |
| DE | Keywords | `getKeywords(wosEntry)` |
| ID | Keywords Plus | `getKeywordsPlus(wosEntry)` |
| AB | Abstract | `getAbstract(wosEntry) # Not saved in the CVS` |
| C1R* | Addresses Data (JSON) | `getAddressesAndAuthors(wosEntry)` |
| C1 | Addresses | `formatAddressesWOS(addressesData)` |
| RPR* | Reprint Data (JSON) | `getAddressesAndAuthors(wosEntry, forceReprint=True)` |
| RP | Reprint Addresses | `formatAddressesWOS(repringData)` |
| EM | Email Addresses | `getAuthorNames(authorData,"email_addr")` |
| RI | ResearcherID | ` # TODO` |
| OI | ORCID | `# TODO` |
| FUR* | Funding Data (JSON) | `getFunding(wosEntry)` |
| FU | Format Funding WOS | `formatFundingWOS(fundingData)` |
| FP | Funding Agency Name | `# TODO` |
| FX | Funding Text | `getFundingText(wosEntry)` |
| CRR* | References Data (JSON) | `getReferences(wosEntry)` |
| CI | References UIDs | `getReferencesUIDs(referencesData)` |
| PU | Publisher Name | `getPublisherName(wosEntry)` |
| PI | Publisher City | `getPublisherCity(wosEntry)` |
| PA | Publisher Address | `getPublisherAddress(wosEntry)` |
| IDR* | IDs Data (JSON) | `getIDs(wosEntry)` |
| SN | ISSN | `getISSN(ids)` |
| EI | EISSN | `getEISSN(ids)` |
| BN | ISBN | `getISBN(ids)` |
| J9 | Source 29-abbreviation | `getSource29Abbreviation(sourcesData)` |
| JI | Source ISO-abbreviation | `getSourceISOAbbreviation(sourcesData)` |
| PD | Publication Month | `getPublicationMonth(publicationInfo)` |
| PY | Publication Year | `getPublicationYear(publicationInfo)` |
| VL | Publication Volume | `getPublicationVolume(publicationInfo)` |
| IS | Publication Issue | `getPublicationIssue(publicationInfo)` |
| PN | Publication Part Number | `getPublicationPartNumber(publicationInfo)` |
| SU | Publication Supplement | `getPublicationSupplement(publicationInfo)` |
| SI | Publication Special Issue | `getPublicationSpecialIssue(publicationInfo)` |
| MA | Meeting Abstract | `# TODO` |
| BP | Publication Page Begin | `getPublicationPageBegin(publicationInfo)` |
| EP | Publication Page End | `getPublicationPageEnd(publicationInfo)` |
| AR | Publication Article Number | `getPublicationArticleNumber(publicationInfo)` |
| DI | DOI | `getDOI(ids)` |
| DL | URL | `# TODO` |
| D2 | Book DOI | `# TODO` |
| EA | Publication Early Access Month | `getPublicationEarlyMonth(publicationInfo)` |
| EB | Publication Early Access Year | `getPublicationEarlyYear(publicationInfo)` |
| PG | Page Count | `getPublicationPageCount(publicationInfo)` |
| WCR* | Category Info Data (JSON) | `getCategoryInfo(wosEntry)` |
| WC | Subject Categories | `getCategorySubjects(categoryInfo)` |
| WE | WOS Edition | `getWOSEditions(wosEntry)` |
| SC | Research Areas | `getCategoryResearchAreas(categoryInfo)` |
| GA | Document Delivery Number | `# TODO` |
| PM | PMID | `getPMID(ids)` |
| HC | Cited Half-life | `# TODO` |
| HP | Cited References Count | `# TODO` |
| OA | Open Access | `getOpenAccess(wosEntry)` |
| UT | UID | `wosEntry["UID"]` |

# TSV files
The script `Examples/extractTSV.py` can be used to generate TSV files from the WOS data. The columns correspond to the above table.

Files description:
 - `WoS_2022.tsv` contains fields organized in the same fashion as the output of the web of science web interface. These fields are described in https://images.webofknowledge.com/images/help/WOS/hs_wos_fieldtags.html
 - `WoS_2022_extra.tsv` contains fields with complete data in fields (such as complete authors, publisher or addresses data) each entry is in JSON format
 - `WoS_2022_abstract.tsv` contains the abstracts and respective `UID`
 - `WoS_2022_references.tsv` pairs of citing and cited UIDs


# Dehydrated DBGZ for fast access 
(coming soon)
