from pathlib import Path
import WOSRaw as wos



WOSArchivePath = Path("/mnt/sciencegenome/WOS_DBGZ/WoS_2023_All.dbgz")


# # Path to where to save the schema files
schemaPath = Path("Schema")

# # Path to where to save the reports files
reportsPath = Path("Reports")

schemaPath.mkdir(parents=True, exist_ok=True)
reportsPath.mkdir(parents=True, exist_ok=True)


wos.report.createSchemaAndReportFile(
    WOSArchivePath,
    schemaPath=schemaPath,
    reportsPath=reportsPath,
    mostCommon=5,
    saveEach=100000,
    minPercentageFilter=0
)

# createSchemaAndReportFile(WOSArchivePath, schemaPath=Path("Schema"), reportsPath=Path("Reports"),
#                               mostCommon=5, saveEach=100000, minPercentageFilter=0):
#     """
#     Create a schema file and a report file for a given WOS raw dbgz file.
#     The schema is a machine readable json files while the report is a 
#     human readable txt file.

#     Parameters
#     ----------
#     WOSArchivePath : pathlib.Path or str
#         Path to the WOS raw dbgz file.
#     schemaPath : pathlib.Path or str, optional
#         Path to where to save the schema files, by default Path("Schema")
#     reportsPath : pathlib.Path or str, optional 
#         Path to where to save the reports files, by default Path("Reports")
#     mostCommon : int, optional
#         Number of most common values to save in the report, by default 5
#     saveEach : int, optional
#         Save the schema and report files every saveEach entries, by default 100000
#     minPercentageFilter : int, optional
#         Minimum percentage of values for a given field to be saved in the report, by default 0
#     """
