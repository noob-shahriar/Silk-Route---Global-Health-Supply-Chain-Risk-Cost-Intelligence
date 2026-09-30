"""
03_freight_efficiency.py
Silk Route: freight mode cost-efficiency analysis.

Answers: how much more does air freight cost per kg than ocean/truck,
and where is the program plausibly overpaying for speed?
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
IN_PATH = BASE / "data" / "processed" / "shipments_clean.csv"
FIG_DIR = BASE / "outputs" / "figures"
TAB_DIR = BASE / "outputs" / "tables"


def main():
    df = pd.read_csv(IN_PATH)

    valid = df.dropna(subset=["freight_cost_per_kg", "Shipment Mode"])
    valid = valid[valid["freight_cost_per_kg"] > 0]
    # Trim extreme outliers (top/bottom 1%) so a handful of tiny/huge
    # shipments don't distort the mode-level averages
    lo, hi = valid["freight_cost_per_kg"].quantile([0.01, 0.99])
    valid = valid[(valid["freight_cost_per_kg"] >= lo) & (valid["freight_cost_per_kg"] <= hi)]

    print(f"Shipments with usable freight-cost-per-kg: {len(valid):,} of {len(df):,}")

    # ---------------------------------------------------------------
    # 1) Freight cost per kg by shipment mode (overall)
    # ---------------------------------------------------------------
    mode_summary = (
        valid.groupby("Shipment Mode")["freight_cost_per_kg"]
        .agg(median_cost_per_kg="median", mean_cost_per_kg="mean",
             n_shipments="count", total_weight_kg=lambda s: valid.loc[s.index, "weight_kg"].sum())
        .sort_values("median_cost_per_kg", ascending=False)
    )
    mode_summary.to_csv(TAB_DIR / "freight_cost_by_mode.csv")
    print("\nFreight cost per kg by shipment mode:")
    print(mode_summary.round(2).to_string())

    fig, ax = plt.subplots(figsize=(8, 5))
    mode_summary["median_cost_per_kg"].sort_values().plot(kind="barh", ax=ax, color="#264653")
    ax.set_xlabel("Median freight cost per kg (USD)")
    ax.set_title("Freight Cost Efficiency by Shipment Mode")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "freight_cost_by_mode.png", dpi=150)
    plt.close(fig)

    # ---------------------------------------------------------------
    # 2) Air premium vs. Truck/Ocean, by country
    # ---------------------------------------------------------------
    ground_modes = ["Truck", "Ocean"]
    air_modes = ["Air", "Air Charter"]

    country_mode = (
        valid[valid["Shipment Mode"].isin(ground_modes + air_modes)]
        .groupby(["Country", "Shipment Mode"])["freight_cost_per_kg"]
        .median()
        .unstack()
    )

    rows = []
    for country, row in country_mode.iterrows():
        air_vals = [row[m] for m in air_modes if m in row and pd.notna(row[m])]
        ground_vals = [row[m] for m in ground_modes if m in row and pd.notna(row[m])]
        if air_vals and ground_vals:
            air_cost = min(air_vals)
            ground_cost = min(ground_vals)
            if ground_cost > 0:
                rows.append({
                    "country": country,
                    "air_cost_per_kg": round(air_cost, 2),
                    "ground_cost_per_kg": round(ground_cost, 2),
                    "air_premium_multiplier": round(air_cost / ground_cost, 2),
                })

    premium_table = pd.DataFrame(rows).sort_values("air_premium_multiplier", ascending=False)
    premium_table.to_csv(TAB_DIR / "air_freight_premium_by_country.csv", index=False)

    if len(premium_table):
        avg_multiplier = premium_table["air_premium_multiplier"].mean()
        print(f"\nCountries with both air and ground shipment data: {len(premium_table)}")
        print(f"Average air-vs-ground freight cost multiplier: {avg_multiplier:.1f}x")
        print("\nTop 5 countries where air freight carries the largest premium:")
        print(premium_table.head(5).to_string(index=False))

    # ---------------------------------------------------------------
    # 3) Air-mode share of total freight spend
    # ---------------------------------------------------------------
    mode_spend = df.dropna(subset=["freight_cost_usd"]).groupby("Shipment Mode")["freight_cost_usd"].sum()
    air_spend = mode_spend[mode_spend.index.isin(air_modes)].sum()
    total_spend = mode_spend.sum()
    print(f"\nAir modes account for {air_spend/total_spend:.1%} of ${total_spend:,.0f} "
          f"in total recorded freight cost.")

    print(f"\nSaved: {TAB_DIR/'freight_cost_by_mode.csv'}")
    print(f"Saved: {TAB_DIR/'air_freight_premium_by_country.csv'}")
    print(f"Saved: {FIG_DIR/'freight_cost_by_mode.png'}")


if __name__ == "__main__":
    main()
