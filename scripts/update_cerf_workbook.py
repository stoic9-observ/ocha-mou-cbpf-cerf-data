import re
from pathlib import Path
from datetime import datetime
import xml.etree.ElementTree as ET

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "cerf"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

YEAR = 2026
USG_DONOR_NAME = "United States of America"

CONTRIB_URL = f"https://cerfgms-webapi.unocha.org/v1/donorcontribution/GetByQry/{YEAR}/year.xml"
PROJECT_URL = f"https://cerfgms-webapi.unocha.org/v1/project/year/{YEAR}.xml"

OUTFILE = OUTPUT_DIR / f"UNOCHA_USG_CERF_{YEAR}.xlsx"


def safe_sheet_name(name):
    cleaned = re.sub(r"[\[\]\:\*\?\/\\]", "", str(name))
    return cleaned[:31]


def text_to_float(value):
    if value is None or value == "":
        return 0.0
    return float(value)


def child_text(parent, path):
    found = parent.find(path)
    if found is None or found.text is None:
        return None
    return found.text


def parse_cerf_contributions_xml(url):
    """
    CERF contribution records contain nested amount fields.

    pd.read_xml() flattens the top-level contribution record but does not
    reliably extract nested donorpledge / donorcommitment / donorreceived
    amount values.

    This parser explicitly extracts:
    - PledgeAmountUSD
    - CommitmentAmountUSD
    - ReceivedAmountUSD
    - WriteoffAmountUSD
    """

    response = requests.get(url)
    response.raise_for_status()

    root = ET.fromstring(response.content)

    records = []

    for item in root.findall(".//DonorContribution"):
        record = {
            "ContributionId": child_text(item, "ContributionId"),
            "ContributionCode": child_text(item, "ContributionCode"),
            "Donor": child_text(item, "Donor"),
            "CountryCode": child_text(item, "CountryCode"),
            "RegionName": child_text(item, "RegionName"),
            "Year": child_text(item, "Year"),
            "DonorType": child_text(item, "DonorType"),
            "StatusCode": child_text(item, "StatusCode"),
            "LatestDate": child_text(item, "LatestDate"),
            "ActivityDate": child_text(item, "ActivityDate"),
            "ActivityDateType": child_text(item, "ActivityDateType"),
            "PledgeCalcUSD": child_text(item, "PledgeCalcUSD"),
            "ContributionStatus": child_text(item, "ContributionStatus"),
            "CommitmentType": child_text(item, "CommitmentType"),
            "AgreementFromYear": child_text(item, "AgreementFromYear"),
            "AgreementToYear": child_text(item, "AgreementToYear"),

            # Explicit nested monetary fields
            "PledgeDate": child_text(item, "donorpledge/donorpledge/PledgeDate"),
            "PledgeCurrency": child_text(item, "donorpledge/donorpledge/PledgeCurrency"),
            "PledgeAmountUSD": child_text(item, "donorpledge/donorpledge/PledgeAmountUSD"),

            "CommitmentDate": child_text(item, "donorcommitment/donorcommitment/CommitmentDate"),
            "CommitmentCurrency": child_text(item, "donorcommitment/donorcommitment/CommitmentCurrency"),
            "CommitmentAmountUSD": child_text(item, "donorcommitment/donorcommitment/CommitmentAmountUSD"),

            "ReceivedDate": child_text(item, "donorreceived/donorreceived/ReceivedDate"),
            "ReceivedCurrency": child_text(item, "donorreceived/donorreceived/ReceivedCurrency"),
            "ReceivedAmountUSD": child_text(item, "donorreceived/donorreceived/ReceivedAmountUSD"),

            "WriteoffDate": child_text(item, "donorwriteoff/donorwriteoff/WriteoffDate"),
            "WriteoffAmountUSD": child_text(item, "donorwriteoff/donorwriteoff/WriteoffAmountUSD"),
        }

        records.append(record)

    df = pd.DataFrame(records)

    numeric_cols = [
        "ContributionId",
        "Year",
        "StatusCode",
        "ActivityDateType",
        "PledgeCalcUSD",
        "AgreementFromYear",
        "AgreementToYear",
        "PledgeAmountUSD",
        "CommitmentAmountUSD",
        "ReceivedAmountUSD",
        "WriteoffAmountUSD",
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    date_cols = [
        "LatestDate",
        "ActivityDate",
        "PledgeDate",
        "CommitmentDate",
        "ReceivedDate",
        "WriteoffDate",
    ]

    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    df["OutstandingAmountUSD"] = (
        df["PledgeAmountUSD"].fillna(0)
        - df["ReceivedAmountUSD"].fillna(0)
        - df["WriteoffAmountUSD"].fillna(0)
    )

    return df


print("Downloading CERF donor contributions with nested XML parser...")
contrib = parse_cerf_contributions_xml(CONTRIB_URL)

print("Downloading CERF projects...")
projects = pd.read_xml(PROJECT_URL)

print("Filtering USG CERF contributions...")
usg_contrib = contrib[
    (contrib["Year"] == YEAR)
    & (contrib["Donor"].astype(str).str.strip() == USG_DONOR_NAME)
].copy()

country_summary = (
    projects
    .groupby("CountryName", as_index=False)
    .agg(
        CERF_Project_Count=("ProjectID", "count"),
        Total_Amount_Approved=("TotalAmountApproved", "sum"),
    )
    .sort_values("Total_Amount_Approved", ascending=False)
)

agency_summary = (
    projects
    .groupby(["AgencyName", "AgencyShortName"], as_index=False)
    .agg(
        CERF_Project_Count=("ProjectID", "count"),
        Total_Amount_Approved=("TotalAmountApproved", "sum"),
    )
    .sort_values("Total_Amount_Approved", ascending=False)
)

sector_summary = (
    projects
    .groupby("ProjectSectorName", as_index=False)
    .agg(
        CERF_Project_Count=("ProjectID", "count"),
        Total_Amount_Approved=("TotalAmountApproved", "sum"),
    )
    .sort_values("Total_Amount_Approved", ascending=False)
)

window_summary = (
    projects
    .groupby("WindowFullName", as_index=False)
    .agg(
        CERF_Project_Count=("ProjectID", "count"),
        Total_Amount_Approved=("TotalAmountApproved", "sum"),
    )
    .sort_values("Total_Amount_Approved", ascending=False)
)

usg_summary = pd.DataFrame({
    "Metric": [
        "USG CERF contribution records",
        "USG pledged amount",
        "USG committed amount",
        "USG received / paid amount",
        "USG writeoff amount",
        "USG outstanding amount",
    ],
    "Value": [
        len(usg_contrib),
        usg_contrib["PledgeAmountUSD"].sum(),
        usg_contrib["CommitmentAmountUSD"].sum(),
        usg_contrib["ReceivedAmountUSD"].sum(),
        usg_contrib["WriteoffAmountUSD"].sum(),
        usg_contrib["OutstandingAmountUSD"].sum(),
    ],
})

validation_checks = pd.DataFrame({
    "Check": [
        "CERF contribution rows",
        "CERF project rows",
        "USG CERF contribution rows",
        "USG donor name used",
        "CERF year",
        "USG pledged total",
        "USG committed total",
        "USG received / paid total",
        "USG outstanding total",
        "CERF project countries",
        "CERF project agencies",
        "CERF project sectors",
        "Total CERF amount approved",
    ],
    "Value": [
        len(contrib),
        len(projects),
        len(usg_contrib),
        USG_DONOR_NAME,
        YEAR,
        usg_contrib["PledgeAmountUSD"].sum(),
        usg_contrib["CommitmentAmountUSD"].sum(),
        usg_contrib["ReceivedAmountUSD"].sum(),
        usg_contrib["OutstandingAmountUSD"].sum(),
        projects["CountryName"].nunique(),
        projects["AgencyName"].nunique(),
        projects["ProjectSectorName"].nunique(),
        projects["TotalAmountApproved"].sum(),
    ],
})

methodology = pd.DataFrame({
    "Item": [
        "Workbook generated",
        "CERF contribution endpoint",
        "CERF project endpoint",
        "Raw contribution grain",
        "Raw project grain",
        "USG contribution filter",
        "Important parser note",
        "Important limitation",
    ],
    "Value": [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        CONTRIB_URL,
        PROJECT_URL,
        "One row = one CERF donor contribution record",
        "One row = one CERF project/allocation record",
        f'Year = {YEAR} and Donor = "{USG_DONOR_NAME}"',
        "CERF contribution amounts are nested XML fields. This script explicitly extracts pledge, commitment, received, and writeoff amounts from nested donorpledge, donorcommitment, donorreceived, and donorwriteoff nodes.",
        "CERF is a global pooled fund. U.S. contributions to CERF cannot be directly attributed to individual CERF country allocations or projects.",
    ],
})

print("Writing CERF workbook...")

with pd.ExcelWriter(OUTFILE, engine="openpyxl") as writer:
    validation_checks.to_excel(writer, sheet_name="00_Validation_Checks", index=False)
    methodology.to_excel(writer, sheet_name="01_Methodology", index=False)
    contrib.to_excel(writer, sheet_name="02_RAW_CERF_Contributions", index=False)
    projects.to_excel(writer, sheet_name="03_RAW_CERF_Projects", index=False)
    usg_contrib.to_excel(writer, sheet_name="04_USG_CERF_Contrib_2026", index=False)
    usg_summary.to_excel(writer, sheet_name="05_USG_CERF_Summary", index=False)
    country_summary.to_excel(writer, sheet_name="06_Country_Summary", index=False)
    agency_summary.to_excel(writer, sheet_name="07_Agency_Summary", index=False)
    sector_summary.to_excel(writer, sheet_name="08_Sector_Summary", index=False)
    window_summary.to_excel(writer, sheet_name="09_Window_Summary", index=False)

    for country in sorted(projects["CountryName"].dropna().unique()):
        country_projects = projects[projects["CountryName"] == country].copy()
        sheet = safe_sheet_name(f"CERF_{country}")
        country_projects.to_excel(writer, sheet_name=sheet, index=False)

print(f"Saved CERF workbook: {OUTFILE}")
print("")
print("USG CERF summary:")
print(usg_summary)