import pandas as pd
from pathlib import Path

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# -----------------------------
# CBPF API endpoints
# -----------------------------
PROJECT_SUMMARY_URL = "https://cbpfapi.unocha.org/vo1/odata/ProjectSummary?$format=csv"
CONTRIBUTION_URL = "https://cbpfapi.unocha.org/vo1/odata/Contribution?$format=csv&includeTransfer=1"

# -----------------------------
# CERF API endpoints
# -----------------------------
CERF_CONTRIBUTION_URL = "https://cerfgms-webapi.unocha.org/v1/donorcontribution/year/2026.xml"
CERF_PROJECT_URL = "https://cerfgms-webapi.unocha.org/v1/project/year/2026.xml"

print("Downloading CBPF Project Summary...")
project_summary = pd.read_csv(PROJECT_SUMMARY_URL, low_memory=False)

print("Downloading CBPF Contribution...")
contribution = pd.read_csv(CONTRIBUTION_URL, low_memory=False)

print("Downloading CERF Contribution...")
cerf_contribution = pd.read_xml(CERF_CONTRIBUTION_URL)

print("Downloading CERF Projects...")
cerf_projects = pd.read_xml(CERF_PROJECT_URL)

# -----------------------------
# CBPF: USG contributions for FY2026
# -----------------------------
usg_contrib = contribution[
    (contribution["FiscalYear"] == 2026) &
    (contribution["DonorName"].astype(str).str.strip() == "United States")
].copy()

# Funds that received USG CBPF contributions
usg_funds = usg_contrib["PooledFundName"].dropna().unique()

# CBPF funding summary
cbpf_funding = (
    usg_contrib
    .groupby(["PooledFundId", "PooledFundName"], as_index=False)
    .agg(
        PledgeAmt=("PledgeAmt", "sum"),
        PaidAmt=("PaidAmt", "sum"),
        ContributionRows=("ContributionCode", "count")
    )
    .sort_values("PaidAmt", ascending=False)
)

cbpf_funding.insert(0, "Mechanism", "CBPF")
cbpf_funding.rename(columns={"PooledFundName": "Fund"}, inplace=True)

# -----------------------------
# CERF: USG contributions for FY2026
# -----------------------------
# CERF column names may vary, so this searches each row for "United States"
usg_cerf_contrib = cerf_contribution[
    cerf_contribution.astype(str).apply(
        lambda row: row.str.contains("United States", case=False, regex=False).any(),
        axis=1
    )
].copy()

# Try to summarize CERF contribution amounts if common amount columns exist
cerf_paid_col = None
cerf_pledge_col = None

for col in cerf_contribution.columns:
    lower = col.lower()
    if cerf_paid_col is None and "paid" in lower and "amt" in lower:
        cerf_paid_col = col
    if cerf_pledge_col is None and "pledge" in lower and "amt" in lower:
        cerf_pledge_col = col

cerf_summary = pd.DataFrame([{
    "Mechanism": "CERF",
    "PooledFundId": "",
    "Fund": "Central Emergency Response Fund",
    "PledgeAmt": usg_cerf_contrib[cerf_pledge_col].sum() if cerf_pledge_col else "",
    "PaidAmt": usg_cerf_contrib[cerf_paid_col].sum() if cerf_paid_col else "",
    "ContributionRows": len(usg_cerf_contrib)
}])

# Combined Funding tab
funding = pd.concat(
    [
        cbpf_funding[["Mechanism", "PooledFundId", "Fund", "PledgeAmt", "PaidAmt", "ContributionRows"]],
        cerf_summary
    ],
    ignore_index=True
)

# -----------------------------
# Export workbook
# -----------------------------
excel_path = OUTPUT_DIR / "UNOCHA_USG_Pooled_Funds_2026.xlsx"

with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
    funding.to_excel(writer, sheet_name="Funding", index=False)

    # Raw CBPF data
    project_summary.to_excel(writer, sheet_name="RAW_CBPF_ProjectSummary", index=False)
    contribution.to_excel(writer, sheet_name="RAW_CBPF_Contribution", index=False)
    usg_contrib.to_excel(writer, sheet_name="USG_CBPF_Contrib_2026", index=False)

    # One tab per USG-supported CBPF
    for fund in usg_funds:
        fund_projects = project_summary[
            (project_summary["PooledFundName"] == fund) &
            (project_summary["AllocationYear"] == 2026)
        ].copy()

        sheet_name = f"CBPF_{fund}"[:31]
        fund_projects.to_excel(writer, sheet_name=sheet_name, index=False)

    # CERF data
    cerf_contribution.to_excel(writer, sheet_name="RAW_CERF_Contribution", index=False)
    cerf_projects.to_excel(writer, sheet_name="RAW_CERF_Projects", index=False)
    usg_cerf_contrib.to_excel(writer, sheet_name="USG_CERF_Contrib_2026", index=False)

print(f"Saved: {excel_path}")