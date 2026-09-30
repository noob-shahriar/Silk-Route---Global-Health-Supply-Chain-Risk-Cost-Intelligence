"""
04_leadtime_analysis.py
Silk Route: lead time & route performance analysis.

Answers: which countries/routes are chronically slow (high mean lead time)
vs. unpredictable (high variance), since those need different fixes.
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
IN_PATH = BASE / "data" / "processed" / "shipments_clean.csv"
FIG_DIR = BASE / "outputs" / "figures"
TAB_DIR = BASE / "outputs" / "tables"

MIN_SHIPMENTS_PER_COUNTRY = 20


def main():
    df = pd.read_csv(IN_PATH)
    valid = df.dropna(subset=["lead_time_days", "Country"])
    print(f"Shipments with usable lead_time_days: {len(valid):,} of {len(df):,}")

    country_stats = (
        valid.groupby("Country")["lead_time_days"]
        .agg(n_shipments="count", mean_days="mean", median_days="median", std_days="std")
        .query("n_shipments >= @MIN_SHIPMENTS_PER_COUNTRY")
        .sort_values("mean_days", ascending=False)
    )
    country_stats.to_csv(TAB_DIR / "leadtime_by_country.csv")

    overall_mean = valid["lead_time_days"].mean()
    overall_median = valid["lead_time_days"].median()
    print(f"\nOverall lead time: mean={overall_mean:.1f} days, median={overall_median:.1f} days")
    print(f"\nCountries analyzed (>= {MIN_SHIPMENTS_PER_COUNTRY} shipments): {len(country_stats)}")

    print("\n5 slowest countries by mean lead time:")
    print(country_stats.head(5).round(1).to_string())

    print("\n5 most unpredictable countries by lead time std-dev:")
    print(country_stats.sort_values("std_days", ascending=False).head(5).round(1).to_string())

    # Chronic-slow vs. unpredictable quadrant chart
    fig, ax = plt.subplots(figsize=(9, 7))
    ax.scatter(country_stats["mean_days"], country_stats["std_days"],
               s=country_stats["n_shipments"] / 3, alpha=0.6, color="#3d5a80")
    for country, row in country_stats.iterrows():
        if row["mean_days"] > country_stats["mean_days"].quantile(0.75) or \
           row["std_days"] > country_stats["std_days"].quantile(0.75):
            ax.annotate(country, (row["mean_days"], row["std_days"]), fontsize=8,
                        xytext=(4, 4), textcoords="offset points")
    ax.axvline(country_stats["mean_days"].median(), color="gray", linestyle="--", linewidth=1)
    ax.axhline(country_stats["std_days"].median(), color="gray", linestyle="--", linewidth=1)
    ax.set_xlabel("Mean lead time (days) — chronically slow →")
    ax.set_ylabel("Lead time std-dev (days) — unpredictable →")
    ax.set_title("Route Performance: Chronic Delay vs. Unpredictability\n(bubble size = shipment count)")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "leadtime_quadrant.png", dpi=150)
    plt.close(fig)

    # Lead time by shipment mode
    mode_stats = (
        valid.groupby("Shipment Mode")["lead_time_days"]
        .agg(n_shipments="count", mean_days="mean", median_days="median")
        .sort_values("mean_days")
    )
    mode_stats.to_csv(TAB_DIR / "leadtime_by_mode.csv")
    print("\nLead time by shipment mode:")
    print(mode_stats.round(1).to_string())

    print(f"\nSaved: {TAB_DIR/'leadtime_by_country.csv'}")
    print(f"Saved: {TAB_DIR/'leadtime_by_mode.csv'}")
    print(f"Saved: {FIG_DIR/'leadtime_quadrant.png'}")


if __name__ == "__main__":
    main()
