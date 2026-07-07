from pathlib import Path

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from adjustText import adjust_text

ROOT = Path(__file__).resolve().parents[1]
SUMMARY_FILE = ROOT / "output" / "summary_visuals" / "usg_cbpf_cerf_funding_summary.xlsx"

OUT_DIR = ROOT / "output" / "figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_excel(SUMMARY_FILE)

df = df[~df["Fund"].isin(["TOTAL", "CERF"])].copy()

df["Country"] = (
    df["Fund"]
    .astype(str)
    .str.replace(r"\s*\(.*?\)", "", regex=True)
    .replace({
        "DRC": "Dem. Rep. Congo",
        "Myanmar": "Myanmar",
    })
)

world = gpd.read_file(
    "https://naturalearth.s3.amazonaws.com/110m_cultural/ne_110m_admin_0_countries.zip"
)

world = world.merge(
    df,
    left_on="NAME",
    right_on="Country",
    how="left",
)

fig, ax = plt.subplots(figsize=(24, 14))

world.plot(
    ax=ax,
    color="#f5f5f5",
    edgecolor="#d0d0d0",
    linewidth=0.35,
)

funded = world[world["Paid"].notna()].copy()

funded.plot(
    ax=ax,
    column="Paid",
    cmap="Blues",
    edgecolor="#333333",
    linewidth=0.6,
    legend=True,
    legend_kwds={
        "label": "Paid U.S. contribution",
        "shrink": 0.45,
    },
    vmin=0,
    vmax=funded["Paid"].max(),
)

# Format color scale as dollars instead of scientific notation
cbar_ax = fig.axes[-1]
cbar_ax.yaxis.set_major_formatter(
    mtick.FuncFormatter(lambda x, _: f"${x/1_000_000:,.0f}M")
)
cbar_ax.tick_params(labelsize=8)
cbar_ax.set_ylabel("Paid U.S. contribution", fontsize=9)

texts = []

for _, row in funded.iterrows():
    point = row.geometry.representative_point()
    x, y = point.x, point.y

    label = (
        f"{row['Fund']}\n"
        f"${row['Paid']/1_000_000:.0f}M paid\n"
        f"${row['Pledged']/1_000_000:.0f}M pledged"
    )

    text = ax.text(
        x,
        y,
        label,
        fontsize=8,
        ha="center",
        va="center",
        bbox=dict(
            boxstyle="round,pad=0.16",
            fc="white",
            ec="#777777",
            lw=0.45,
            alpha=0.92,
        ),
        zorder=5,
    )
    texts.append(text)

adjust_text(
    texts,
    ax=ax,
    expand_points=(2.7, 2.7),
    expand_text=(2.1, 2.1),
    force_points=0.75,
    force_text=0.95,
    arrowprops=dict(
        arrowstyle="-",
        color="#555555",
        lw=0.45,
    ),
)

ax.set_title(
    "FY2026 U.S. Contributions to OCHA Country-Based Pooled Funds",
    fontsize=20,
    weight="bold",
    pad=22,
)

ax.text(
    0.01,
    0.025,
    (
        "Sources: UN OCHA CBPF API and CERF Data API. "
        "CERF is excluded from the country map because it is a global pooled fund. "
        "Mapped values show paid U.S. contributions to CBPFs; labels show paid and pledged totals."
    ),
    transform=ax.transAxes,
    fontsize=8.5,
    color="#555555",
)

ax.axis("off")

out_png = OUT_DIR / "global_cbpf_paid_labeled_map.png"
out_pdf = OUT_DIR / "global_cbpf_paid_labeled_map.pdf"

plt.savefig(out_png, dpi=600, bbox_inches="tight")
plt.savefig(out_pdf, bbox_inches="tight")
plt.close()

print(f"Saved labeled map PNG: {out_png}")
print(f"Saved labeled map PDF: {out_pdf}")