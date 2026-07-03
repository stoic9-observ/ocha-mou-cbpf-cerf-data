import pandas as pd
import altair as alt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = ROOT / "output" / "UNOCHA_USG_Pooled_Funds_2026.xlsx"
VIS_DIR = ROOT / "output" / "visuals"
VIS_DIR.mkdir(parents=True, exist_ok=True)

funding = pd.read_excel(WORKBOOK, sheet_name="Funding")
projects = pd.read_excel(WORKBOOK, sheet_name="RAW_CBPF_ProjectSummary")
usg = pd.read_excel(WORKBOOK, sheet_name="USG_CBPF_Contrib_2026")

# 1. USG contribution by pooled fund
chart1 = (
    alt.Chart(funding)
    .mark_bar()
    .encode(
        x=alt.X("PaidAmt:Q", title="USG Paid Amount"),
        y=alt.Y("Fund:N", sort="-x", title="Pooled Fund"),
        tooltip=["Fund", "PledgeAmt", "PaidAmt", "ContributionRows"]
    )
    .properties(
        title="FY2026 U.S. Contributions to OCHA Country-Based Pooled Funds",
        width=800,
        height=350
    )
)

chart1.save(VIS_DIR / "usg_cbpf_contributions.html")

# 2. Project budgets by USG-supported pooled fund
usg_funds = usg["PooledFundName"].dropna().unique()

projects_2026 = projects[
    (projects["AllocationYear"] == 2026) &
    (projects["PooledFundName"].isin(usg_funds))
].copy()

chart2 = (
    alt.Chart(projects_2026)
    .mark_circle(size=80, opacity=0.7)
    .encode(
        x=alt.X("Budget:Q", title="Project Budget"),
        y=alt.Y("PooledFundName:N", title="Pooled Fund"),
        tooltip=[
            "PooledFundName",
            "OrganizationName",
            "OrganizationType",
            "ProjectTitle",
            "Budget",
            "ProjectStatus"
        ]
    )
    .properties(
        title="Projects in FY2026 CBPFs Receiving U.S. Contributions",
        width=900,
        height=450
    )
)

chart2.save(VIS_DIR / "projects_by_fund_budget.html")

# 3. Top implementing organizations
top_orgs = (
    projects_2026
    .groupby(["OrganizationName", "OrganizationType"], as_index=False)
    .agg(
        TotalBudget=("Budget", "sum"),
        ProjectCount=("ChfProjectCode", "count")
    )
    .sort_values("TotalBudget", ascending=False)
    .head(20)
)

chart3 = (
    alt.Chart(top_orgs)
    .mark_bar()
    .encode(
        x=alt.X("TotalBudget:Q", title="Total Project Budget"),
        y=alt.Y("OrganizationName:N", sort="-x", title="Organization"),
        tooltip=["OrganizationName", "OrganizationType", "TotalBudget", "ProjectCount"]
    )
    .properties(
        title="Top Implementing Organizations in U.S.-Supported CBPFs",
        width=900,
        height=500
    )
)

chart3.save(VIS_DIR / "top_implementing_orgs.html")

print(f"Saved visuals to: {VIS_DIR}")