import re
from pathlib import Path
from datetime import datetime

import pandas as pd
from great_tables import GT, md, style, loc

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "output" / "tables"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PROJECT_SUMMARY_URL = "https://cbpfapi.unocha.org/vo1/odata/ProjectSummary?$format=csv"
CONTRIBUTION_URL = "https://cbpfapi.unocha.org/vo1/odata/Contribution?$format=csv&includeTransfer=1"

TRANCHE_1 = [
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


def normalize_country(name: str) -> str:
    if pd.isna(name):
        return ""

    name = str(name).strip()
    name = re.sub(r"\s*\(.*?\)", "", name).strip()

    replacements = {
        "Burma": "Myanmar",
        "Myanmar": "Myanmar",
        "Democratic Republic of the Congo": "DRC",
        "Congo, Democratic Republic of the": "DRC",
        "DRC": "DRC",
    }

    return replacements.get(name, name)


print("Downloading OCHA CBPF data...")
projects = pd.read_csv(PROJECT_SUMMARY_URL, low_memory=False)
contrib = pd.read_csv(CONTRIBUTION_URL, low_memory=False)

print("Filtering USG FY2026 contributions...")
usg_contrib = contrib[
    (contrib["FiscalYear"] == 2026)
    & (contrib["DonorName"].astype(str).str.strip() == "United States")
].copy()

usg_contrib["Country"] = usg_contrib["PooledFundName"].apply(normalize_country)

funding_summary = (
    usg_contrib
    .groupby(["Country", "PooledFundName"], as_index=False)
    .agg(
        PledgeAmt=("PledgeAmt", "sum"),
        PaidAmt=("PaidAmt", "sum"),
        ContributionRows=("ContributionCode", "count"),
    )
)

projects["Country"] = projects["PooledFundName"].apply(normalize_country)

project_counts = (
    projects[
        (projects["AllocationYear"] == 2026)
        & (projects["PooledFundName"].isin(usg_contrib["PooledFundName"].unique()))
    ]
    .groupby("Country", as_index=False)
    .agg(
        ProjectCount=("ChfProjectCode", "count"),
        TotalProjectBudget=("Budget", "sum"),
    )
)

all_countries = sorted(
    set(TRANCHE_1)
    | set(TRANCHE_2)
    | set(funding_summary["Country"].dropna())
)

crosswalk = pd.DataFrame({"Country": all_countries})

crosswalk["Dec 2025 MOU"] = crosswalk["Country"].isin(TRANCHE_1)
crosswalk["May 2026 tranche"] = crosswalk["Country"].isin(TRANCHE_2)
crosswalk["CBPF API"] = crosswalk["Country"].isin(set(funding_summary["Country"]))

crosswalk = crosswalk.merge(
    funding_summary.groupby("Country", as_index=False).agg(
        PledgeAmt=("PledgeAmt", "sum"),
        PaidAmt=("PaidAmt", "sum"),
        ContributionRows=("ContributionRows", "sum"),
        FundNames=("PooledFundName", lambda x: "; ".join(sorted(set(x)))),
    ),
    on="Country",
    how="left",
)

crosswalk = crosswalk.merge(project_counts, on="Country", how="left")

numeric_cols = [
    "PledgeAmt",
    "PaidAmt",
    "ContributionRows",
    "ProjectCount",
    "TotalProjectBudget",
]

crosswalk[numeric_cols] = crosswalk[numeric_cols].fillna(0)

crosswalk["Dec 2025 MOU"] = crosswalk["Dec 2025 MOU"].map({True: "✓", False: ""})
crosswalk["May 2026 tranche"] = crosswalk["May 2026 tranche"].map({True: "✓", False: ""})
crosswalk["CBPF API"] = crosswalk["CBPF API"].map({True: "✓", False: ""})

crosswalk["Notes"] = ""
crosswalk.loc[
    crosswalk["Country"].isin(["Central African Republic", "Lebanon", "Venezuela"]),
    "Notes"
] = "Listed in May tranche; not currently matched to FY2026 USG CBPF contribution data."

crosswalk.loc[
    crosswalk["Country"] == "Myanmar",
    "Notes"
] = "Listed as Burma in May tranche."

crosswalk.loc[
    crosswalk["FundNames"].astype(str).str.contains("RhPF|ESAHF|AP-RHPF", regex=True, na=False),
    "Notes"
] = "Regional pooled fund."

crosswalk = crosswalk.sort_values(
    ["CBPF API", "PaidAmt", "Country"],
    ascending=[False, False, True],
)

totals = pd.DataFrame({
    "Country": ["TOTAL"],
    "Dec 2025 MOU": [f"{(crosswalk['Dec 2025 MOU'] == '✓').sum()} countries"],
    "May 2026 tranche": [f"{(crosswalk['May 2026 tranche'] == '✓').sum()} countries"],
    "CBPF API": [f"{(crosswalk['CBPF API'] == '✓').sum()} funds"],
    "PledgeAmt": [crosswalk["PledgeAmt"].sum()],
    "PaidAmt": [crosswalk["PaidAmt"].sum()],
    "ContributionRows": [crosswalk["ContributionRows"].sum()],
    "FundNames": [""],
    "ProjectCount": [crosswalk["ProjectCount"].sum()],
    "TotalProjectBudget": [crosswalk["TotalProjectBudget"].sum()],
    "Notes": [""],
})

crosswalk = pd.concat([crosswalk, totals], ignore_index=True)

today = datetime.now().strftime("%B %d, %Y")

table = (
    GT(crosswalk)
    .tab_header(
        title=md("**U.S.–OCHA Humanitarian Funding Crosswalk**"),
        subtitle="December 2025 MOU and May 2026 tranche compared with FY2026 OCHA CBPF contribution data",
    )
    .cols_label(
        Country="Country / Fund",
        FundNames="OCHA pooled fund name",
        PledgeAmt="USG pledged",
        PaidAmt="USG paid",
        ContributionRows="Contribution records",
        ProjectCount="2026 projects",
        TotalProjectBudget="Project budget",
        Notes="Notes",
    )
    .fmt_currency(
        columns=["PledgeAmt", "PaidAmt", "TotalProjectBudget"],
        currency="USD",
        decimals=0,
    )
    .fmt_number(columns=["ContributionRows", "ProjectCount"], decimals=0)
    .tab_style(
        style=style.text(weight="bold"),
        locations=loc.body(columns=["Country"]),
    )
    .tab_source_note(source_note=md(f"**Generated:** {today}"))
    .tab_source_note(
        source_note=md(
            "Source: UN OCHA CBPF API, Project Summary and Contribution endpoints. "
            "Filtered where `DonorName = United States` and `FiscalYear = 2026`."
        )
    )
    .tab_source_note(
        source_note=md(
            "Methodology note: CBPFs are pooled financing mechanisms. This table identifies "
            "U.S. contributions to pooled funds and projects associated with those pooled funds; "
            "it does not attribute U.S. dollars directly to individual projects."
        )
    )
)

output_file = OUT_DIR / "usg_ocha_mou_cbpf_crosswalk.png"
csv_file = OUT_DIR / "usg_ocha_mou_cbpf_crosswalk.csv"

table.gtsave(output_file)
crosswalk.to_csv(csv_file, index=False)

print(f"Saved table image to: {output_file}")
print(f"Saved crosswalk CSV to: {csv_file}")