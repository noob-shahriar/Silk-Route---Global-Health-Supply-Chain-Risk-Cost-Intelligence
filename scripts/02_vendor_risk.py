"""
02_vendor_risk.py
Silk Route: vendor concentration risk analysis.

Answers: how concentrated is supplier spend, per product category, and
where does the program have a single-point-of-failure vendor risk?
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
IN_PATH = BASE / "data" / "processed" / "shipments_clean.csv"
FIG_DIR = BASE / "outputs" / "figures"
TAB_DIR = BASE / "outputs" / "tables"


def herfindahl(spend_shares: pd.Series) -> float:
    """HHI on a 0-1 scale (sum of squared market shares). >0.25 = highly
    concentrated by standard antitrust/procurement conventions."""
    return float((spend_shares ** 2).sum())


def risk_tier(hhi: float) -> str:
    if hhi >= 0.25:
        return "High"
    if hhi >= 0.15:
        return "Moderate"
    return "Low"


def main():
    df = pd.read_csv(IN_PATH)
    df["Line Item Value"] = pd.to_numeric(df["Line Item Value"], errors="coerce")
    df = df.dropna(subset=["Line Item Value", "manufacturer_group", "Sub Classification"])

    total_spend = df["Line Item Value"].sum()
    print(f"Total spend analyzed: ${total_spend:,.0f}")

    # ---------------------------------------------------------------
    # 1) Overall vendor Pareto (whole program)
    # ---------------------------------------------------------------
    vendor_spend = (
        df.groupby("manufacturer_group")["Line Item Value"]
        .sum()
        .sort_values(ascending=False)
    )
    vendor_share = vendor_spend / vendor_spend.sum()
    cum_share = vendor_share.cumsum()

    pareto_table = pd.DataFrame({
        "vendor": vendor_spend.index,
        "spend_usd": vendor_spend.values,
        "share_pct": (vendor_share.values * 100).round(2),
        "cumulative_share_pct": (cum_share.values * 100).round(2),
    })
    pareto_table.to_csv(TAB_DIR / "vendor_pareto_overall.csv", index=False)

    n_vendors_for_80pct = int((cum_share <= 0.80).sum()) + 1
    print(f"Vendors: {len(vendor_spend)} total. "
          f"{n_vendors_for_80pct} vendor(s) account for ~80% of total spend.")
    print(f"Top vendor: {pareto_table.iloc[0]['vendor']} "
          f"(${pareto_table.iloc[0]['spend_usd']:,.0f}, "
          f"{pareto_table.iloc[0]['share_pct']}% of spend)")

    # Pareto chart (top 15 vendors)
    top15 = pareto_table.head(15)
    fig, ax1 = plt.subplots(figsize=(10, 6))
    ax1.bar(top15["vendor"], top15["spend_usd"] / 1e6, color="#2a6f97")
    ax1.set_ylabel("Spend (USD, millions)")
    ax1.set_xticklabels(top15["vendor"], rotation=60, ha="right")
    ax2 = ax1.twinx()
    ax2.plot(top15["vendor"], top15["cumulative_share_pct"], color="#d62828", marker="o")
    ax2.set_ylabel("Cumulative % of total spend")
    ax2.axhline(80, color="gray", linestyle="--", linewidth=1)
    plt.title("Top 15 Manufacturers by Spend — Pareto View")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "vendor_pareto_top15.png", dpi=150)
    plt.close(fig)

    # ---------------------------------------------------------------
    # 2) HHI per product sub-classification -> risk table
    # ---------------------------------------------------------------
    rows = []
    for sub_class, g in df.groupby("Sub Classification"):
        cat_spend = g.groupby("manufacturer_group")["Line Item Value"].sum()
        cat_total = cat_spend.sum()
        if cat_total <= 0:
            continue
        shares = cat_spend / cat_total
        hhi = herfindahl(shares)
        top_vendor = shares.idxmax()
        top_vendor_share = shares.max()
        rows.append({
            "sub_classification": sub_class,
            "total_spend_usd": cat_total,
            "n_vendors": g["manufacturer_group"].nunique(),
            "top_vendor": top_vendor,
            "top_vendor_share_pct": round(top_vendor_share * 100, 1),
            "hhi": round(hhi, 3),
            "risk_tier": risk_tier(hhi),
        })

    risk_table = pd.DataFrame(rows).sort_values("total_spend_usd", ascending=False)
    risk_table.to_csv(TAB_DIR / "vendor_concentration_by_subclass.csv", index=False)

    n_high = (risk_table["risk_tier"] == "High").sum()
    print(f"\nProduct sub-classifications analyzed: {len(risk_table)}")
    print(f"Sub-classifications with HIGH vendor concentration risk (HHI >= 0.25): {n_high}")
    print("\nTop 5 highest-risk categories by spend:")
    print(risk_table[risk_table["risk_tier"] == "High"]
          .sort_values("total_spend_usd", ascending=False)
          .head(5)[["sub_classification", "total_spend_usd", "top_vendor",
                     "top_vendor_share_pct", "hhi"]]
          .to_string(index=False))

    # Bar chart: HHI by sub-classification (top 10 by spend)
    top10_risk = risk_table.head(10).sort_values("hhi")
    colors = top10_risk["risk_tier"].map({"High": "#d62828", "Moderate": "#f4a259", "Low": "#2a9d8f"})
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(top10_risk["sub_classification"], top10_risk["hhi"], color=colors)
    ax.axvline(0.25, color="gray", linestyle="--", linewidth=1, label="High-risk threshold (0.25)")
    ax.set_xlabel("Herfindahl-Hirschman Index (HHI)")
    ax.set_title("Vendor Concentration Risk — Top 10 Product Categories by Spend")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / "vendor_concentration_hhi.png", dpi=150)
    plt.close(fig)

    print(f"\nSaved: {TAB_DIR/'vendor_pareto_overall.csv'}")
    print(f"Saved: {TAB_DIR/'vendor_concentration_by_subclass.csv'}")
    print(f"Saved: {FIG_DIR/'vendor_pareto_top15.png'}")
    print(f"Saved: {FIG_DIR/'vendor_concentration_hhi.png'}")


if __name__ == "__main__":
    main()
