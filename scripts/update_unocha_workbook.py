####################
# UNOCHA DATA PULL AUTO UPDATE IF RAN
####################

import re
from pathlib import Path
from datetime import datetime

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

PROJECT_URL = "https://cbpfapi.unocha.org/vo1/odata/ProjectSummary?$format=csv"
CONTRIB_URL = "https://cbpfapi.unocha.org/vo1/odata/Contribution?$format=csv&includeTransfer=1"

OUTFILE = OUTPUT_DIR / "UNOCHA_USG_Pooled_Funds_2026.xlsx"

MOU_2025 = [
    "Guatemala", "Honduras", "El Salvador", "Ukraine", "Haiti",
    "Nigeria", "Ethiopia", "South Sudan", "Mozambique", "Myanmar",
    "DRC", "Sudan", "Bangladesh", "Syria", "Uganda", "Kenya", "Chad",
]

TRANCHE_2 = [
    "Bangladesh", "Myanmar", "Central African Republic", "Chad",
    "Colombia", "DRC", "El Salvador", "Ethiopia", "Guatemala",
    "Haiti", "Honduras", "Kenya", "Lebanon", "Mozambique",
    "Nigeria", "South Sudan", "Sudan", "Syria", "Uganda",
    "Ukraine", "Venezuela",
]


def normalize_country(name):
    if pd.isna(name):
        return ""

    name = str(name).strip()
    name = re.sub(r"\s*\(.*?\)", "", name).strip()

    replacements = {
        "Burma": "Myanmar",
        "Democratic Republic of the Congo": "DRC",
        "Congo, Democratic Republic of the": "DRC",
    }

    return replacements.get(name, name)


def safe_sheet_name(name):
    cleaned = re.sub(r"[\[\]\:\*\?\/\\]", "", str(name))
    return cleaned[:31]


print("Downloading raw OCHA Project Summary data...")
projects = pd.read_csv(PROJECT_URL, low_memory=False)

print("Downloading raw OCHA Contribution data...")
contrib = pd.read_csv(CONTRIB_URL, low_memory=False)

projects["CountryNormalized"] = projects["PooledFundName"].apply(normalize_country)
contrib["CountryNormalized"] = contrib["PooledFundName"].apply(normalize_country)

print("Filtering USG FY2026 contributions...")
usg_contrib = contrib[
    (contrib["FiscalYear"] == 2026)
    & (contrib["DonorName"].astype(str).str.strip() == "United States")
].copy()

usg_fund_ids = sorted(usg_contrib["PooledFundId"].dropna().unique())

funding_summary = (
    usg_contrib
    .groupby(["PooledFundId", "PooledFundName", "CountryNormalized"], as_index=False)
    .agg(
        PledgeAmt=("PledgeAmt", "sum"),
        PaidAmt=("PaidAmt", "sum"),
        ContributionRows=("ContributionCode", "count"),
    )
    .sort_values("PaidAmt", ascending=False)
)

announcement_countries = sorted(set(MOU_2025) | set(TRANCHE_2))

announcement_df = pd.DataFrame({"Country": announcement_countries})
announcement_df["Dec_2025_MOU"] = announcement_df["Country"].isin(MOU_2025)
announcement_df["May_2026_Tranche_2"] = announcement_df["Country"].isin(TRANCHE_2)

country_usg = (
    funding_summary
    .groupby("CountryNormalized", as_index=False)
    .agg(
        OCHA_PooledFundNames=("PooledFundName", lambda x: "; ".join(sorted(set(x)))),
        USG_Pledged=("PledgeAmt", "sum"),
        USG_Paid=("PaidAmt", "sum"),
        ContributionRows=("ContributionRows", "sum"),
    )
    .rename(columns={"CountryNormalized": "Country"})
)

project_counts = (
    projects[
        (projects["AllocationYear"] == 2026)
        & (projects["PooledFundId"].isin(usg_fund_ids))
    ]
    .groupby("CountryNormalized", as_index=False)
    .agg(
        ProjectCount=("ChfProjectCode", "count"),
        TotalProjectBudget=("Budget", "sum"),
    )
    .rename(columns={"CountryNormalized": "Country"})
)

country_usg_crosswalk = (
    announcement_df
    .merge(country_usg, on="Country", how="outer")
    .merge(project_counts, on="Country", how="left")
)

for col in ["USG_Pledged", "USG_Paid", "ContributionRows", "ProjectCount", "TotalProjectBudget"]:
    country_usg_crosswalk[col] = country_usg_crosswalk[col].fillna(0)

country_usg_crosswalk["Appears_in_CBPF_API"] = country_usg_crosswalk["USG_Pledged"] > 0

country_usg_crosswalk = country_usg_crosswalk.sort_values(
    ["Appears_in_CBPF_API", "USG_Paid", "Country"],
    ascending=[False, False, True],
)

methodology = pd.DataFrame({
    "Item": [
        "Workbook generated",
        "Project endpoint",
        "Contribution endpoint",
        "Raw project grain",
        "Raw contribution grain",
        "USG contribution filter",
        "Project filter",
        "December 2025 MOU countries",
        "May 2026 tranche countries",
        "Important limitation",
    ],
    "Value": [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        PROJECT_URL,
        CONTRIB_URL,
        "One row = one approved OCHA CBPF project",
        "One row = one donor contribution record",
        'FiscalYear = 2026 and DonorName = "United States"',
        "AllocationYear = 2026 and PooledFundId in USG-supported pooled funds",
        ", ".join(MOU_2025),
        ", ".join(TRANCHE_2),
        "CBPFs are pooled financing mechanisms. Project tabs show projects associated with pooled funds receiving U.S. contributions; they do not prove direct U.S. funding to individual projects.",
    ],
})

print("Writing Excel workbook...")

with pd.ExcelWriter(OUTFILE, engine="openpyxl") as writer:
    methodology.to_excel(writer, sheet_name="01_Methodology", index=False)
    projects.to_excel(writer, sheet_name="02_RAW_ProjectSummary", index=False)
    contrib.to_excel(writer, sheet_name="03_RAW_Contribution", index=False)
    usg_contrib.to_excel(writer, sheet_name="04_USG_Contrib_2026", index=False)
    country_usg_crosswalk.to_excel(writer, sheet_name="05_USG_Country_Crosswalk", index=False)

    # One worksheet for each USG-supported pooled fund.
    # Match by PooledFundId, not name, because fund names can differ across endpoints.
    for fund_id in usg_fund_ids:
        fund_projects = projects[
            (projects["AllocationYear"] == 2026)
            & (projects["PooledFundId"] == fund_id)
        ].copy()

        if fund_projects.empty:
            continue

        fund_name = fund_projects["PooledFundName"].dropna().iloc[0]
        sheet = safe_sheet_name(f"CBPF_{fund_name}")

        fund_projects.to_excel(writer, sheet_name=sheet, index=False)

print(f"Saved workbook: {OUTFILE}")