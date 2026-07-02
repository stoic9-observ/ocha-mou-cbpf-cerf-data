import pandas as pd
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

PROJECT_SUMMARY_URL = "https://cbpfapi.unocha.org/vo1/odata/ProjectSummary?$format=csv"
CONTRIBUTION_URL = "https://cbpfapi.unocha.org/vo1/odata/Contribution?$format=csv&includeTransfer=1"

print("Downloading CBPF Project Summary...")
project_summary = pd.read_csv(PROJECT_SUMMARY_URL, low_memory=False)

print("Downloading CBPF Contribution...")
contribution = pd.read_csv(CONTRIBUTION_URL, low_memory=False)

usg_contrib = contribution[
    (contribution["FiscalYear"] == 2026) &
    (contribution["DonorName"].astype(str).str.strip() == "United States")
].copy()

usg_funds = sorted(usg_contrib["PooledFundName"].dropna().unique())

funding = (
    usg_contrib
    .groupby(["PooledFundId", "PooledFundName"], as_index=False)
    .agg(
        PledgeAmt=("PledgeAmt", "sum"),
        PaidAmt=("PaidAmt", "sum"),
        ContributionRows=("ContributionCode", "count")
    )
    .sort_values("PaidAmt", ascending=False)
)

funding.insert(0, "Mechanism", "CBPF")
funding.rename(columns={"PooledFundName": "Fund"}, inplace=True)

readme = pd.DataFrame({
    "Item": [
        "Workbook generated",
        "Mechanism covered",
        "Project source",
        "Contribution source",
        "USG filter",
        "Fiscal year filter",
        "Project allocation year filter",
        "Important limitation"
    ],
    "Value": [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "UN OCHA Country-Based Pooled Funds (CBPF)",
        PROJECT_SUMMARY_URL,
        CONTRIBUTION_URL,
        'DonorName == "United States"',
        "FiscalYear == 2026",
        "AllocationYear == 2026",
        "Project tabs show projects implemented through pooled funds that received U.S. contributions; they do not prove direct U.S. funding to individual projects."
    ]
})

excel_path = OUTPUT_DIR / "UNOCHA_USG_Pooled_Funds_2026.xlsx"

print("Building Excel workbook...")

with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
    readme.to_excel(writer, sheet_name="README_Methodology", index=False)
    funding.to_excel(writer, sheet_name="Funding", index=False)
    project_summary.to_excel(writer, sheet_name="RAW_CBPF_ProjectSummary", index=False)
    contribution.to_excel(writer, sheet_name="RAW_CBPF_Contribution", index=False)
    usg_contrib.to_excel(writer, sheet_name="USG_CBPF_Contrib_2026", index=False)

    for fund in usg_funds:
        fund_projects = project_summary[
            (project_summary["PooledFundName"] == fund) &
            (project_summary["AllocationYear"] == 2026)
        ].copy()

        sheet_name = f"CBPF_{fund}"[:31]
        fund_projects.to_excel(writer, sheet_name=sheet_name, index=False)

print(f"Saved: {excel_path}")
