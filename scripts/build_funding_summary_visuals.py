from pathlib import Path
from datetime import datetime

import pandas as pd
from great_tables import GT, md, style, loc

ROOT = Path(__file__).resolve().parents[1]

CBPF_FILE = ROOT / "output" / "UNOCHA_USG_Pooled_Funds_2026.xlsx"
CERF_FILE = ROOT / "output" / "cerf" / "UNOCHA_USG_CERF_2026.xlsx"

OUT_DIR = ROOT / "output" / "summary_visuals"
OUT_DIR.mkdir(parents=True, exist_ok=True)

today = datetime.now().strftime("%B %d, %Y")

DEC_MOU = {
    "Guatemala", "Honduras", "El Salvador", "Ukraine", "Haiti",
    "Nigeria", "Ethiopia", "South Sudan", "Mozambique", "Myanmar",
    "DRC", "Sudan", "Bangladesh", "Syria", "Uganda", "Kenya", "Chad",
}

MAY_NOTICE = {
    "Bangladesh", "Myanmar", "Central African Republic", "Chad",
    "Colombia", "DRC", "El Salvador", "Ethiopia", "Guatemala",
    "Haiti", "Honduras", "Kenya", "Lebanon", "Mozambique",
    "Nigeria", "South Sudan", "Sudan", "Syria", "Uganda",
    "Ukraine", "Venezuela",
}


def normalize_fund_name(name):
    name = str(name).strip()
    base = name.split("(")[0].strip()

    replacements = {
        "Burma": "Myanmar",
        "Democratic Republic of the Congo": "DRC",
        "Congo, Democratic Republic of the": "DRC",
    }

    return replacements.get(base, base)


# ----------------------------
# CBPF summary
# ----------------------------

cbpf = pd.read_excel(CBPF_FILE, sheet_name="04_USG_Contrib_2026")

cbpf_summary = (
    cbpf
    .groupby("PooledFundName", as_index=False)
    .agg(
        Pledged=("PledgeAmt", "sum"),
        Paid=("PaidAmt", "sum"),
        Records=("ContributionCode", "count"),
    )
)

cbpf_summary["Fund"] = cbpf_summary["PooledFundName"]
cbpf_summary["Country"] = cbpf_summary["Fund"].apply(normalize_fund_name)
cbpf_summary["Dec 2025 MOU"] = cbpf_summary["Country"].isin(DEC_MOU)
cbpf_summary["May 2026 Notice"] = cbpf_summary["Country"].isin(MAY_NOTICE)

cbpf_summary = cbpf_summary[
    [
        "Fund",
        "Country",
        "Pledged",
        "Paid",
        "Records",
        "Dec 2025 MOU",
        "May 2026 Notice",
    ]
]

# ----------------------------
# CERF summary
# ----------------------------

cerf = pd.read_excel(CERF_FILE, sheet_name="04_USG_CERF_Contrib_2026")

cerf_summary = pd.DataFrame({
    "Fund": ["CERF"],
    "Country": ["CERF"],
    "Pledged": [cerf["PledgeAmountUSD"].sum()],
    "Paid": [cerf["ReceivedAmountUSD"].sum()],
    "Records": [cerf["ContributionCode"].count()],
    "Dec 2025 MOU": [True],
    "May 2026 Notice": [True],
})

# ----------------------------
# May notice placeholders
# ----------------------------

existing_countries = set(cbpf_summary["Country"]) | {"CERF"}

missing_may_countries = sorted(MAY_NOTICE - existing_countries)

placeholders = pd.DataFrame({
    "Fund": missing_may_countries,
    "Country": missing_may_countries,
    "Pledged": 0,
    "Paid": 0,
    "Records": 0,
    "Dec 2025 MOU": [country in DEC_MOU for country in missing_may_countries],
    "May 2026 Notice": True,
})

# ----------------------------
# Final summary table
# ----------------------------

summary = pd.concat(
    [
        cbpf_summary,
        cerf_summary,
        placeholders,
    ],
    ignore_index=True,
)

summary["Outstanding"] = summary["Pledged"] - summary["Paid"]

summary = summary.sort_values(
    ["Paid", "Pledged", "Fund"],
    ascending=[False, False, True],
)

summary_output = summary[
    [
        "Fund",
        "Pledged",
        "Paid",
        "Outstanding",
        "Records",
        "Dec 2025 MOU",
        "May 2026 Notice",
    ]
].copy()

summary_output.to_csv(
    OUT_DIR / "usg_cbpf_cerf_funding_summary.csv",
    index=False,
)

summary_output.to_excel(
    OUT_DIR / "usg_cbpf_cerf_funding_summary.xlsx",
    index=False,
)

# ----------------------------
# Pretty table
# ----------------------------

table_df = summary_output.copy()

table_df["Dec 2025 MOU"] = table_df["Dec 2025 MOU"].map({
    True: "✓",
    False: "✗",
})

table_df["May 2026 Notice"] = table_df["May 2026 Notice"].map({
    True: "✓",
    False: "✗",
})

total_row = pd.DataFrame({
    "Fund": ["TOTAL"],
    "Pledged": [summary_output["Pledged"].sum()],
    "Paid": [summary_output["Paid"].sum()],
    "Outstanding": [summary_output["Outstanding"].sum()],
    "Records": [summary_output["Records"].sum()],
    "Dec 2025 MOU": [""],
    "May 2026 Notice": [""],
})

table_df = pd.concat([table_df, total_row], ignore_index=True)

table = (
    GT(table_df)
    .tab_header(
        title=md("**FY2026 U.S. Contributions to OCHA Pooled Funds**"),
        subtitle="CBPFs and CERF, with December 2025 MOU and May 2026 notice coverage",
    )
    .cols_label(
        Fund="Fund",
        Pledged="Pledged",
        Paid="Paid",
        Outstanding="Outstanding",
        Records="Records",
        **{
            "Dec 2025 MOU": "Dec MOU",
            "May 2026 Notice": "May Notice",
        },
    )
    .fmt_currency(
        columns=["Pledged", "Paid", "Outstanding"],
        currency="USD",
        decimals=0,
    )
    .fmt_number(columns=["Records"], decimals=0)
    .tab_style(
        style=style.text(weight="bold"),
        locations=loc.body(columns=["Fund"]),
    )
    .tab_source_note(
        source_note=md(f"Generated: {today}")
    )
    .tab_source_note(
        source_note=md(
            "Sources: UN OCHA CBPF API and CERF Data API. "
            "CBPF rows show FY2026 U.S. contributions to pooled funds. "
            "Placeholder rows identify May 2026 notice countries not currently matched to FY2026 U.S. CBPF contribution records."
        )
    )
)

table.gtsave(OUT_DIR / "usg_cbpf_cerf_funding_summary.png")

print(f"Saved table: {OUT_DIR / 'usg_cbpf_cerf_funding_summary.png'}")
print(f"Saved CSV:   {OUT_DIR / 'usg_cbpf_cerf_funding_summary.csv'}")
print(f"Saved Excel: {OUT_DIR / 'usg_cbpf_cerf_funding_summary.xlsx'}")