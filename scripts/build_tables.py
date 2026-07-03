import pandas as pd
from pathlib import Path
from great_tables import GT, md
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = ROOT / "output" / "UNOCHA_USG_Pooled_Funds_2026.xlsx"
OUT_DIR = ROOT / "output" / "tables"
OUT_DIR.mkdir(parents=True, exist_ok=True)

contrib = pd.read_excel(WORKBOOK, sheet_name="USG_CBPF_Contrib_2026")

summary = (
    contrib
    .groupby("PooledFundName", as_index=False)
    .agg(
        pledge_amt=("PledgeAmt", "sum"),
        paid_amt=("PaidAmt", "sum"),
        contribution_records=("ContributionCode", "count")
    )
    .sort_values("paid_amt", ascending=False)
)

summary["paid_pct"] = summary["paid_amt"] / summary["pledge_amt"]

total_row = pd.DataFrame([{
    "PooledFundName": "TOTAL",
    "pledge_amt": summary["pledge_amt"].sum(),
    "paid_amt": summary["paid_amt"].sum(),
    "contribution_records": summary["contribution_records"].sum(),
    "paid_pct": summary["paid_amt"].sum() / summary["pledge_amt"].sum()
}])

summary_with_total = pd.concat([summary, total_row], ignore_index=True)

today = datetime.now().strftime("%B %d, %Y")

table = (
    GT(summary_with_total)
    .tab_header(
        title=md("**FY2026 U.S. Contributions to OCHA CBPFs**"),
        subtitle="Country-Based Pooled Funds receiving U.S. Government contributions"
    )
    .cols_label(
        PooledFundName="Pooled Fund / Country",
        pledge_amt="Pledged",
        paid_amt="Paid",
        contribution_records="Records",
        paid_pct="Paid %"
    )
    .fmt_currency(columns=["pledge_amt", "paid_amt"], currency="USD", decimals=0)
    .fmt_percent(columns="paid_pct", decimals=0)
   
    .tab_source_note(
    source_note=md(
        f"**Data downloaded:** {today}"
    )
)
.tab_source_note(
    source_note=md(
        "Source: UN OCHA CBPF API, Contribution endpoint. Filtered where `DonorName = United States` and `FiscalYear = 2026`."
    )
)
.tab_source_note(
    source_note=md(
        "Methodology: CBPFs are pooled financing mechanisms. This table summarizes U.S. Government contributions to pooled funds and should not be interpreted as direct U.S. funding to individual projects."
    )
)
    )


output_file = OUT_DIR / "usg_cbpf_contributions_by_country.png"

table.gtsave(output_file)

print(f"Saved table to {output_file}")