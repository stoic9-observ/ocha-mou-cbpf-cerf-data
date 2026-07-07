from pathlib import Path
import pandas as pd
import plotly.express as px

ROOT = Path(__file__).resolve().parents[1]
SUMMARY_FILE = ROOT / "output" / "summary_visuals" / "usg_cbpf_cerf_funding_summary.xlsx"
OUT_DIR = ROOT / "output" / "figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_excel(SUMMARY_FILE)

# Exclude total and CERF because CERF is global, not country-specific
map_df = df[
    ~df["Fund"].isin(["TOTAL", "CERF"])
].copy()

# Clean country/fund names
map_df["Country"] = (
    map_df["Fund"]
    .astype(str)
    .str.replace(r"\s*\(.*?\)", "", regex=True)
    .replace({
        "DRC": "Democratic Republic of the Congo",
        "Myanmar": "Myanmar",
    })
)

fig = px.choropleth(
    map_df,
    locations="Country",
    locationmode="country names",
    color="Paid",
    hover_name="Fund",
    hover_data={
        "Pledged": ":$,.0f",
        "Paid": ":$,.0f",
        "Outstanding": ":$,.0f",
        "Records": True,
        "Country": False,
    },
    title="FY2026 U.S. Paid Contributions to OCHA CBPFs",
    color_continuous_scale="Blues",
)

fig.update_layout(
    margin=dict(l=0, r=0, t=50, b=0),
    coloraxis_colorbar_title="Paid USD",
)

fig.write_html(OUT_DIR / "global_cbpf_paid_heatmap.html")
fig.write_image(OUT_DIR / "global_cbpf_paid_heatmap.png", scale=2)

print("Saved:")
print(OUT_DIR / "global_cbpf_paid_heatmap.html")
print(OUT_DIR / "global_cbpf_paid_heatmap.png")