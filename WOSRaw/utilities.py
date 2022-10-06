from collections import OrderedDict
import random 


#Examples
"""
PIR: publicationInfo = getPublicationInfo(wosEntry)
PT: publicationType = getPublicationType(publicationInfo) # Journal, Book in series, Book, Conference ...
ADR: authorData = getAuthors(wosEntry)
AU: authors = getAuthorNames(authorData,"wos_standard")
BA: # bookAuthors # TODO Not sure how to get it should be the same as AU
BE: bookEditors = getAuthorNames(getAuthors(wosEntry,roles={"book_editor"}),"wos_standard")
BA: # bookAuthorGroups # TODO Not sure how to get it
AF: authorsFullName = getAuthorNames(authorData,"full_name")
BF: # bookAuthorsFullName # TODO Not sure how to get it should be the same as AF
CA: # groupAuthor # TODO Not sure how to get it
GP: # groupAuthor # TODO Not sure how to get it
TI: title = getTitle(wosEntry)
SOR: sourcesData = getSources(wosEntry)
SO: publicationName = getPublicationName(sourcesData)
SE: bookSeriesTitle = getBookSeriesTitle(sourcesData)
LA: language = getPrimaryLanguage(wosEntry)
DT: docTypes = getDocTypes(wosEntry)
CT: conferenceTitles = getConferencesTitles(getConferences(wosEntry))
CY: conferenceDates = getConferencesDates(getConferences(wosEntry))
CL: conferenceLocations = getConferencesLocations(getConferences(wosEntry))
SP: conferenceSponsors = getConferenceSponsors(getConferences(wosEntry))
HO: conferenceHosts = getConferencesHosts(getConferences(wosEntry))
DE: keywords = getKeywords(wosEntry)
ID: keywordsPlus = getKeywordsPlus(wosEntry)
AB: abstract = getAbstract(wosEntry) # Not saved in the CVS
C1R: addressesData = getAddressesAndAuthors(wosEntry)
C1: addresses = formatAddressesWOS(addressesData)
RPR: repringData = getAddressesAndAuthors(wosEntry, forceReprint=True)
RP: reprintAddresses = formatAddressesWOS(repringData)
EM: emailAddresses = getAuthorNames(authorData,"email_addr")
RI: # researcherID  #TODO
OI: # orcid #TODO
FUR: fundingData = getFunding(wosEntry)
FU: funding = formatFundingWOS(fundingData)
FP: # fundingAgencyName #TODO
FX: fundingText = getFundingText(wosEntry)
CRR: referencesData = getReferences(wosEntry)
CI: referencesUIDs = getReferencesUIDs(referencesData)
PU: publisherName = getPublisherName(wosEntry)
PI: publisherCity = getPublisherCity(wosEntry)
PA: publisherAddress = getPublisherAddress(wosEntry)
IDR: ids = getIDs(wosEntry)
SN: issn = getISSN(ids)
EI: eissn = getEISSN(ids)
BN: isbn = getISBN(ids)
J9: source29Abbreviation = getSource29Abbreviation(ids)
JI: sourceISOAbbreviation = getSourceISOAbbreviation(ids)
PD: publicationMonth = getPublicationMonth(publicationInfo)
PY: publicationYear = getPublicationYear(publicationInfo)
VL: publicationVolume = getPublicationVolume(publicationInfo)
IS: publicationIssue = getPublicationIssue(publicationInfo)
PN: publicationPartNumber = getPublicationPartNumber(publicationInfo)
SU: publicationSupplement = getPublicationSupplement(publicationInfo)
SI: publicationSpecialIssue = getPublicationSpecialIssue(publicationInfo)
MA: # meetingAbstract #TODO
BP: publicationPageBegin = getPublicationPageBegin(publicationInfo)
EP: publicationPageEnd = getPublicationPageEnd(publicationInfo)
AR: publicationArticleNumber = getPublicationArticleNumber(publicationInfo)
DI: DOI = getDOI(ids)
DL: # URL #TODO
D2: # Book DOI #TODO
EA: publicationEarlyAccessMonth = getPublicationEarlyMonth(publicationInfo)
EB: publicationEarlyAccessYear = getPublicationEarlyYear(publicationInfo)
PG: publicationPageCount = getPublicationPageCount(publicationInfo)
WCR: categoryInfo = getCategoryInfo(wosEntry)
WC: subjectCategories = getCategorySubjects(categoryInfo)
WE: WOSEdition = getWOSEditions(wosEntry)
SC: researchAreas = getCategoryResearchAreas(categoryInfo)
GA: # documentDeliveryNumber #TODO
PM: PMID = getPMID(ids)
HC: # citedHalfLife #TODO
HP: # citedReferencesCount #TODO
OA: openAccess = getOpenAccess(wosEntry)
UT: UID = wosEntry["UID"]
"""


def getFlat(data, flatKey, forceList=False, forceString = False):
    """
    Get value for deep key(tuple of keys) or None if it does not exist.

    Parameters
    ----------
    data : dict
        Dictionary to get value from.
    flatKey : tuple
        Tuple of keys path to get value for.
    forceList : bool
        If True, return list even if there is only one element.
    forceString : bool
        If True, return string even if the element is None.

    Returns
    -------
    value : object or str or list
        Value for the key path or None if it does not exist.
        If forceList is True, return list. None is replaced with empty list.
        If forceString is True, return string. None is replaced with empty string.
        
    """
    value = None
    for key in flatKey:
        if data and (key in data):
            value = data[key]
            data = value
        else:
            value = None
            break
    if(forceList and (not isinstance(value, list) and not isinstance(value, tuple))):
        if(value):
            value = [value]
        else:
            value = []
    if(forceString):
        if(value):
            value = str(value)
        else:
            value = ""
    return value

def propListToDict(propList,typeKey = "@type", valueKey = "@value"):
    """
    Convert list of properties to a dictionary.

    Parameters
    ----------
    propList : list
        List of properties.
    typeKey : str
        Key for type.
    valueKey : str
        Key for value.

    Returns
    -------
    propDict : dict
        Dictionary of properties.
        
    """
    propDict = {}
    if(propList):
        for prop in propList:
            if typeKey in prop:
                propDict[prop[typeKey]] = prop[valueKey]
            else:
                propDict[prop] = True
    return propDict




def bestName(entry):
    """
    Get best name for the entry.
    
    Parameters
    ----------
    entry : dict
        Entry to get name for.

    Returns
    -------
    name : str
        Best name for the entry.

    """
    if("display_name" in entry and entry["display_name"]):
        return entry["display_name"]
    elif("full_name" in entry and entry["full_name"]):
        return entry["full_name"]
    elif("wos_standard" in entry and entry["wos_standard"]):
        return entry["wos_standard"]
    else:
        return ""

def getAuthors(wosEntry, roles = {"author"}):
    """
    Get authors data for the entry.

    Parameters
    ----------
    wosEntry : dict
        Entry to get authors data for.
    roles : set
        Set of roles to get. If None, get all data.

    Returns
    -------
    authors : list
        List of authors data.

    """
    # possible nameType one of these:
    # 'display_name'
    # 'full_name'
    # 'wos_standard'
    # 'first_name'
    # 'last_name'
    # 'email_addr'
    authorData = getFlat(wosEntry["data"],["static_data", "summary", "names","name"], forceList=True)
    authorData = sorted(authorData, key=lambda k: int(k['@seq_no']))
    authorData = filter(lambda k: k['@role'] in roles, authorData)
    # Extra data
    # addressesData = getFlat(wosEntry[0]["data"],["static_data","fullrecord_metadata","addresses","address_name"], forceList=True)
    # getFlat(addressesData[0],["names","name"], forceList=True)
    authorNames = []
    for authorEntry in authorData:
        authorNames.append(authorEntry)
    return authorNames

#getAuthorNames(getAuthors(wosEntry),"wos_standard")
def getAuthorNames(authorData, nameType = None):
    authorNames = []
    for authorEntry in authorData:
        if(nameType is None):
            authorNames.append(bestName(authorEntry))
        elif(nameType in authorEntry and authorEntry[nameType]):
            authorNames.append(authorEntry[nameType])
        else:
            authorNames.append("")
    return authorNames



def getReprint(wosEntry):
    return getFlat(wosEntry["data"],["static_data","fullrecord_metadata","reprint_addresses","address_name"], forceList=True)


def getAddressesAndAuthors(wosEntry, forceReprint = False):
    addresses = []
    authors = {}
    if(not forceReprint):
        addressesData = getFlat(wosEntry["data"],["static_data","fullrecord_metadata","addresses","address_name"], forceList=True)
    else:
        addressesData = []
    if(not addressesData): # use reprint addresses when not available
        addressesData = getReprint(wosEntry)
    for addressEntry in addressesData:
        address = getFlat(addressEntry,["address_spec"], forceList=False)
        authorsList = getFlat(addressEntry,["names","name"], forceList=True)
        addresses.append(address)
        address["authors_seqs"] = []
        for author in authorsList:
            authorSequence = int(author["@seq_no"])
            authors[authorSequence] = author
            address["authors_seqs"].append(authorSequence)
    return {"addresses":addresses,"authors":authors}

def formatAddressesWOS(addressesData):
    formattedAddresses = []
    authors = addressesData["authors"]
    for address in addressesData["addresses"]:
        authorIndices = address["authors_seqs"]
        authorNames = [bestName(authors[index]) for index in authorIndices if index in authors]
        formattedAddress = "[%s] %s"%("; ".join(authorNames), address["full_address"])
        formattedAddresses.append(formattedAddress)
    return formattedAddresses

def getConferences(wosEntry):
    return getFlat(wosEntry["data"],["static_data","summary","conferences","conference"], forceList=True)

def getConferencesTitles(conferencesData):
    conferencesTitles = []
    for conferenceEntry in conferencesData:
        conferenceTitle = getFlat(conferenceEntry,["conf_titles","conf_title"], forceList=False, forceString=True)
        if(conferenceTitle):
            conferencesTitles.append(conferenceTitle)
        else:
            conferencesTitles.append("")
    return conferencesTitles

def getConferencesProperties(conferencesData, path):
    conferencesProperty = []
    for conferenceEntry in conferencesData:
        conferencesProperty+=getFlat(conferenceEntry, path, forceList=True)
    return conferencesProperty


def getConferencesTitles(conferencesData):
    return getConferencesProperties(conferencesData,path = ("conf_titles","conf_title"))

def getConferencesDates(conferencesData):
    return getConferencesProperties(conferencesData,path = ("conf_dates","conf_date","#text"))

def getConferencesLocations(conferencesData):
    locations = []
    locationsData = getConferencesProperties(conferencesData,path = ("conf_locations","conf_location"))
    for location in locationsData:
        locationText = ""
        if( "conf_city" in location):
            locationText += getFlat(location,["conf_city"],forceString=True)
        if( "conf_state" in location):
            locationText += ", " + getFlat(location,["conf_state"],forceString=True)
        locations.append(locationText)
    return locations

def getConferencesHosts(conferencesData):
    return getConferencesProperties(conferencesData,path = ("conf_locations","conf_location","conf_host"))

def getConferenceSponsors(conferencesData):
    sponsors = []
    sponsorsData = getConferencesProperties(conferencesData,path = ["sponsors"])
    for sponsor in sponsorsData:
        sponsorText = "; ".join(getFlat(sponsor,["sponsor"], forceList=True))
        sponsors.append(sponsorText)
    return sponsors

def getTitles(wosEntry):
    return propListToDict(getFlat(wosEntry["data"],["static_data","summary","titles","title"], forceList=True),typeKey = "@type", valueKey = "#text")


def getTitle(wosEntry):
    return getFlat(getTitles(wosEntry),["item"],forceString=True)

allowedSourceTitles = {'source', 'source_abbrev', 'abbrev_iso', 'abbrev_11', 'abbrev_29'}
def getSources(wosEntry):
    titles = getTitles(wosEntry)
    return {k: v for k, v in titles.items() if k in allowedSourceTitles}

def getPublicationName(sourcesData):
    return getFlat(sourcesData,["source"], forceString=True)


def getBookSeriesTitle(sourcesData):
    return getFlat(sourcesData,["series"], forceString=True)

def getKeywords(wosEntry):
    keywords = getFlat(wosEntry["data"],["static_data","fullrecord_metadata","keywords","keyword"], forceList=True)
    return keywords

def getKeywordsPlus(wosEntry):
    keywords = getFlat(wosEntry["data"],["static_data","item","keywords_plus","keyword"], forceList=True)
    return keywords


def getPrimaryLanguage(wosEntry):
    languadesData = getFlat(wosEntry["data"],["static_data","fullrecord_metadata","normalized_languages","language"], forceList=True)
    for language in languadesData:
        if(language["@type"] == "primary"):
            return language["#text"]
    return ""



def getDocTypes(wosEntry):
    docTypes = []
    docTypesData = getFlat(wosEntry["data"],["static_data","fullrecord_metadata","normalized_doctypes","doctype"], forceList=True)
    for docType in docTypesData:
        docTypes.append(docType)
    return docTypes


def getAbstract(wosEntry):
    return getFlat(wosEntry["data"],["static_data","fullrecord_metadata","abstracts","abstract","abstract_text","p"], forceList=True)

def getFunding(wosEntry):
    return getFlat(wosEntry["data"],["static_data","fullrecord_metadata","fund_ack","grants","grant"], forceList=True)

def formatFundingWOS(fundingData):
    formattedFunding = []
    for fundingEntry in fundingData:
        grants = getFlat(fundingEntry,["grant_agency"], forceList=True)
        grantName = ""
        if(grants):
            grantName=str(grants[0])
        grantIDs = getFlat(fundingEntry,["grant_ids","grant_id"], forceList=True)
        formattedFunding.append("%s [%s]"%(grantName, "; ".join(grantIDs)))
    return formattedFunding

def getFundingText(wosEntry):
    return getFlat(wosEntry["data"],["static_data","fullrecord_metadata","fund_ack","fund_text","p"], forceList=True)

def getReferences(wosEntry):
    return getFlat(wosEntry["data"],["static_data","fullrecord_metadata","references","reference"], forceList=True)


def getReferencesUIDs(referencesData):
    referencesIDs = []
    for referenceEntry in referencesData:
        uid = getFlat(referenceEntry,["uid"])
        if(uid and uid.find(".")==-1):
            referencesIDs.append(uid)
        else:
            referencesIDs.append("")
    return referencesIDs

def getPublisherName(wosEntry):
    return getFlat(wosEntry["data"],["static_data","summary", "publishers","publisher", "names","name","display_name"], forceString=True)

def getPublisherCity(wosEntry):
    return getFlat(wosEntry["data"],["static_data","summary", "publishers","publisher", "address_spec","city"], forceString=True)

def getPublisherAddress(wosEntry):
    return getFlat(wosEntry["data"],["static_data","summary", "publishers","publisher", "address_spec","full_address"], forceString=True)


def getIDs(wosEntry):
    idPath = ["dynamic_data","cluster_related","identifiers","identifier"]
    return propListToDict(getFlat(wosEntry["data"],idPath, forceList=True))



def getISSN(ids):
    return getFlat(ids,["issn"], forceString=True)

def getEISSN(ids):
    return getFlat(ids,["eissn"], forceString=True)

def getISBN(ids):
    return getFlat(ids,["isbn"], forceString=True)

def getDOI(ids):
    return getFlat(ids,["doi"], forceString=True)

def getPMID(ids):
    return getFlat(ids,["pmid"], forceString=True)

def getPMCID(ids):
    return getFlat(ids,["pmcid"], forceString=True)

def getSource29Abbreviation(sources):
    return getFlat(sources,["abbrev_29"], forceString=True)

def getSourceISOAbbreviation(sources):
    return getFlat(sources,["abbrev_iso"], forceString=True)

def getPublicationInfo(wosEntry):
    return getFlat(wosEntry["data"],["static_data","summary","pub_info"])

def getPublicationType(publicationInfoData):
    return getFlat(publicationInfoData,["@pubtype"], forceString=True)

def getPublicationMonth(publicationInfoData):
    return getFlat(publicationInfoData,["@pubmonth"], forceString=True)

def getPublicationYear(publicationInfoData):
    return getFlat(publicationInfoData,["@pubyear"], forceString=True)
    
def getPublicationEarlyMonth(publicationInfoData):
    return getFlat(publicationInfoData,["@early_access_month"], forceString=True)

def getPublicationEarlyYear(publicationInfoData):
    return getFlat(publicationInfoData,["@early_access_year"], forceString=True)
    
def getPublicationVolume(publicationInfoData):
    return getFlat(publicationInfoData,["@vol"], forceString=True)

def getPublicationIssue(publicationInfoData):
    return getFlat(publicationInfoData,["@issue"], forceString=True)

def getPublicationPartNumber(publicationInfoData):
    return getFlat(publicationInfoData,["@part_no"], forceString=True)

def getPublicationSupplement(publicationInfoData):
    return getFlat(publicationInfoData,["@supplement"], forceString=True)

def getPublicationSpecialIssue(publicationInfoData):
    return getFlat(publicationInfoData,["@special_issue"], forceString=True)

def getPublicationPageBegin(publicationInfoData):
    return getFlat(publicationInfoData,["page","@begin"], forceString=True)

def getPublicationPageEnd(publicationInfoData):
    return getFlat(publicationInfoData,["page","@end"], forceString=True)

def getPublicationArticleNumber(publicationInfoData):
    return getFlat(publicationInfoData,["art_no"], forceString=True)

def getPublicationPageCount(publicationInfoData):
    return getFlat(publicationInfoData,["page","@page_count"], forceString=True)

def getCategoryInfo(wosEntry):
    return getFlat(wosEntry["data"],["static_data","fullrecord_metadata","category_info"])

def getCategoryHeadings(categoryInfoData):
    return getFlat(categoryInfoData,["headings","heading"], forceList=True)

def getCategorySubheadings(categoryInfoData):
    return getFlat(categoryInfoData,["subheadings","subheading"], forceList=True)

def getCategorySubjects(categoryInfoData, subjectTypes = {"traditional"}):
    subjectEntries = getFlat(categoryInfoData,["subjects","subject"], forceList=True)
    categories = []
    for subjectEntry in subjectEntries:
        if(subjectEntry["@ascatype"] in subjectTypes):
            categories.append(subjectEntry["#text"])
    return categories

def getCategoryResearchAreas(categoryInfoData):
    return getCategorySubjects(categoryInfoData, subjectTypes = {"extended"})


def getContributors(wosEntry, roles = {"author"}):
    contributorData = getFlat(wosEntry["data"],["static_data", "contributors","contributor"], forceList=True)
    contributionsArray = []
    for contributor in contributorData:
        contributorEntries= getFlat(contributor,["name"], forceList=True)
        for contributorEntry in contributorEntries:
            contributionsArray.append(contributorEntry)
    
    contributionsArray = sorted(contributionsArray, key=lambda k: int(k['@seq_no']))

    return contributionsArray

def getWOSEditions(wosEntry):
    return [entry["@value"] for entry in getFlat(wosEntry["data"],["static_data","summary","EWUID","edition"], forceList=True)]

def getOpenAccess(wosEntry):
    return list(set([entry["@type"] for entry in getFlat(wosEntry["data"],["dynamic_data","ic_related","oases","oas"], forceList=True)]))


def getAllFields(wosEntry):
    fieldData = OrderedDict()
    fieldData["PIR"] =  publicationInfo = getPublicationInfo(wosEntry)
    fieldData["PT"]  =  publicationType = getPublicationType(publicationInfo) # Journal, Book in series, Book, Conference ...
    fieldData["ADR"] =  authorData = getAuthors(wosEntry)
    fieldData["AU"]  =  authors = getAuthorNames(authorData)
    # fieldData["BA"]  =  # bookAuthors # TODO Not sure how to get it should be the same as AU
    fieldData["BE"]  =  bookEditors = getAuthorNames(getAuthors(wosEntry,roles={"book_editor"}))
    # fieldData["BA"]  =  # bookAuthorGroups # TODO Not sure how to get it
    fieldData["AF"]  =  authorsFullName = getAuthorNames(authorData,"full_name")
    # fieldData["BF"]  =  # bookAuthorsFullName # TODO Not sure how to get it should be the same as AF
    # fieldData["CA"]  =  # groupAuthor # TODO Not sure how to get it
    # fieldData["GP"]  =  # groupAuthor # TODO Not sure how to get it
    fieldData["TI"]  =  title = getTitle(wosEntry)
    fieldData["SOR"] =  sourcesData = getSources(wosEntry)
    fieldData["SO"]  =  publicationName = getPublicationName(sourcesData)
    fieldData["SE"]  =  bookSeriesTitle = getBookSeriesTitle(sourcesData)
    fieldData["LA"]  =  language = getPrimaryLanguage(wosEntry)
    fieldData["DT"]  =  docTypes = getDocTypes(wosEntry)
    fieldData["CT"]  =  conferenceTitles = getConferencesTitles(getConferences(wosEntry))
    fieldData["CY"]  =  conferenceDates = getConferencesDates(getConferences(wosEntry))
    fieldData["CL"]  =  conferenceLocations = getConferencesLocations(getConferences(wosEntry))
    fieldData["SP"]  =  conferenceSponsors = getConferenceSponsors(getConferences(wosEntry))
    fieldData["HO"]  =  conferenceHosts = getConferencesHosts(getConferences(wosEntry))
    fieldData["DE"]  =  keywords = getKeywords(wosEntry)
    fieldData["ID"]  =  keywordsPlus = getKeywordsPlus(wosEntry)
    fieldData["AB"]  =  abstract = getAbstract(wosEntry) # Not saved in the CVS
    fieldData["C1R"] =  addressesData = getAddressesAndAuthors(wosEntry)
    fieldData["C1"]  =  addresses = formatAddressesWOS(addressesData)
    fieldData["RPR"] =  reprintData = getAddressesAndAuthors(wosEntry, forceReprint=True)
    fieldData["RP"]  =  reprintAddresses = formatAddressesWOS(reprintData)
    fieldData["EM"]  =  emailAddresses = getAuthorNames(authorData,"email_addr")
    # fieldData["RI"]  =  # researcherID  #TODO
    # fieldData["OI"]  =  # orcid #TODO
    fieldData["FUR"] =  fundingData = getFunding(wosEntry)
    fieldData["FU"]  =  funding = formatFundingWOS(fundingData)
    # fieldData["FP"]  =  # fundingAgencyName #TODO
    fieldData["FX"]  =  fundingText = getFundingText(wosEntry)
    fieldData["CRR"] =  referencesData = getReferences(wosEntry)
    fieldData["CI"]  =  referencesUIDs = getReferencesUIDs(referencesData)
    fieldData["PU"]  =  publisherName = getPublisherName(wosEntry)
    fieldData["PI"]  =  publisherCity = getPublisherCity(wosEntry)
    fieldData["PA"]  =  publisherAddress = getPublisherAddress(wosEntry)
    fieldData["IDR"] =  ids = getIDs(wosEntry)
    fieldData["SN"]  =  issn = getISSN(ids)
    fieldData["EI"]  =  eissn = getEISSN(ids)
    fieldData["BN"]  =  isbn = getISBN(ids)
    fieldData["J9"]  =  source29Abbreviation = getSource29Abbreviation(sourcesData)
    fieldData["JI"]  =  sourceISOAbbreviation = getSourceISOAbbreviation(sourcesData)
    fieldData["PD"]  =  publicationMonth = getPublicationMonth(publicationInfo)
    fieldData["PY"]  =  publicationYear = getPublicationYear(publicationInfo)
    fieldData["VL"]  =  publicationVolume = getPublicationVolume(publicationInfo)
    fieldData["IS"]  =  publicationIssue = getPublicationIssue(publicationInfo)
    fieldData["PN"]  =  publicationPartNumber = getPublicationPartNumber(publicationInfo)
    fieldData["SU"]  =  publicationSupplement = getPublicationSupplement(publicationInfo)
    fieldData["SI"]  =  publicationSpecialIssue = getPublicationSpecialIssue(publicationInfo)
    # fieldData["MA"]  =  # meetingAbstract #TODO
    fieldData["BP"]  =  publicationPageBegin = getPublicationPageBegin(publicationInfo)
    fieldData["EP"]  =  publicationPageEnd = getPublicationPageEnd(publicationInfo)
    fieldData["AR"]  =  publicationArticleNumber = getPublicationArticleNumber(publicationInfo)
    fieldData["DI"]  =  DOI = getDOI(ids)
    # fieldData["DL"]  =  # URL #TODO
    # fieldData["D2"]  =  # Book DOI #TODO
    fieldData["EA"]  =  publicationEarlyAccessMonth = getPublicationEarlyMonth(publicationInfo)
    fieldData["EB"]  =  publicationEarlyAccessYear = getPublicationEarlyYear(publicationInfo)
    fieldData["PG"]  =  publicationPageCount = getPublicationPageCount(publicationInfo)
    fieldData["WCR"] =  categoryInfo = getCategoryInfo(wosEntry)
    fieldData["WC"]  =  subjectCategories = getCategorySubjects(categoryInfo)
    fieldData["WE"]  =  WOSEdition = getWOSEditions(wosEntry)
    fieldData["SC"]  =  researchAreas = getCategoryResearchAreas(categoryInfo)
    # fieldData["GA"]  =  # documentDeliveryNumber #TODO
    fieldData["PM"]  =  PMID = getPMID(ids)
    # fieldData["HC"]  =  # citedHalfLife #TODO
    # fieldData["HP"]  =  # citedReferencesCount #TODO
    fieldData["OA"]  =  openAccess = getOpenAccess(wosEntry)
    fieldData["UT"]  =  UID = wosEntry["UID"]
    return fieldData


def getScheme(valid=None,invalid=None):
    schemeFields = OrderedDict()
    schemeFields["PIR"] = ("publicationInfo","a")
    schemeFields["PT"] = ("publicationType","s")
    schemeFields["ADR"] = ("authorData","a")
    schemeFields["AU"] = ("authorNames","S")
    schemeFields["BE"] = ("bookEditors","S")
    schemeFields["TI"] = ("Title","s")
    schemeFields["SOR"] = ("sourcesData","a")
    schemeFields["SO"] = ("publicationName","s")
    schemeFields["SE"] = ("bookSeriesTitle","s")
    schemeFields["LA"] = ("languages","S")
    schemeFields["DT"] = ("docTypes","S")
    schemeFields["CT"] = ("conferenceTitles","S")
    schemeFields["CY"] = ("conferenceDates","S")
    schemeFields["CL"] = ("conferenceLocations","S")
    schemeFields["SP"] = ("conferenceSponsors","S")
    schemeFields["HO"] = ("conferenceHosts","S")
    schemeFields["DE"] = ("keywords","S")
    schemeFields["ID"] = ("keywordsPlus","S")
    schemeFields["AB"] = ("abstract","S")
    schemeFields["C1R"] = ("addressesData","a")
    schemeFields["C1"] = ("addresses","S")
    schemeFields["RPR"] = ("repringData","a")
    schemeFields["RP"] = ("reprintAddresses","S")
    schemeFields["EM"] = ("emailAddresses","S")
    schemeFields["FUR"] = ("fundingData","a")
    schemeFields["FU"] = ("funding","S")
    schemeFields["FX"] = ("fundingText","S")
    schemeFields["CRR"] = ("referencesData","a")
    schemeFields["CI"] = ("referencesUIDs","S")
    schemeFields["PU"] = ("publisherName","s")
    schemeFields["PI"] = ("publisherCity","s")
    schemeFields["PA"] = ("publisherAddress","s")
    schemeFields["IDR"] = ("ids","a")
    schemeFields["SN"] = ("ISSN","s")
    schemeFields["EI"] = ("EISSN","s")
    schemeFields["BN"] = ("ISBN","s")
    schemeFields["J9"] = ("source29Abbreviation","s")
    schemeFields["JI"] = ("sourceISOAbbreviation","s")
    schemeFields["PD"] = ("publicationMonth","s")
    schemeFields["PY"] = ("publicationYear","s")
    schemeFields["VL"] = ("publicationVolume","s")
    schemeFields["IS"] = ("publicationIssue","s")
    schemeFields["PN"] = ("publicationPartNumber","s")
    schemeFields["SU"] = ("publicationSupplement","s")
    schemeFields["SI"] = ("publicationSpecialIssue","s")
    # schemeFields["MA"] = ("meetingAbstract","S")
    schemeFields["BP"] = ("publicationPageBegin","s")
    schemeFields["EP"] = ("publicationPageEnd","s")
    schemeFields["AR"] = ("publicationArticleNumber","s")
    schemeFields["DI"] = ("DOI","s")
    # schemeFields["DL"] = ("URL","s")
    # schemeFields["D2"] = ("BookDOI","s")
    schemeFields["EA"] = ("publicationEarlyAccessMonth","s")
    schemeFields["EB"] = ("publicationEarlyAccessYear","s")
    schemeFields["PG"] = ("publicationPageCount","s")
    schemeFields["WCR"] = ("categoryInfo","a")
    schemeFields["WC"] = ("subjectCategories","S")
    schemeFields["WE"] = ("WOSEdition","S")
    schemeFields["SC"] = ("researchAreas","S")
    # schemeFields["GA"] = ("documentDeliveryNumber","s")
    schemeFields["PM"] = ("PMID","s")
    # schemeFields["HC"] = ("citedHalfLife","s")
    # schemeFields["HP"] = ("citedReferencesCount","s")
    schemeFields["OA"] = ("openAccess","S")
    schemeFields["UT"] = ("UID","s")
    if(valid is not None):
        schemeFields = {k:v for k,v in schemeFields.items() if k in valid}
    if(invalid is not None):
        schemeFields = {k:v for k,v in schemeFields.items() if k not in invalid}
    return schemeFields

