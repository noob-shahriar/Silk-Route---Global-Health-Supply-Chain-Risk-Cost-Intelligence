"""
01_clean.py
Silk Route: Global Health Supply Chain Risk & Cost Intelligence

Loads the raw SCMS Delivery History dataset, cleans it, standardizes
vendors/dates/freight fields, and writes a processed CSV used by every
downstream analysis script.
"""

import re
import pandas as pd
import numpy as np
from pathlib import Path

RAW_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "SCMS_Delivery_History_Dataset.csv"
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "shipments_clean.csv"


def parse_mixed_date(series: pd.Series) -> pd.Series:
    """The raw file mixes m/d/yy and d-Mon-yy date formats in the same column."""
    return pd.to_datetime(series, errors="coerce", format="mixed", dayfirst=False)


def standardize_manufacturer(raw: str) -> str:
    """Collapse manufacturing-site strings that refer to the same company
    (e.g. 'Aurobindo Unit III, India' and 'Aurobindo Unit VII, IN') into one
    vendor group, so vendor-concentration analysis isn't split across
    cosmetic variants of the same supplier."""
    if not isinstance(raw, str) or raw.strip() == "":
        return "Unknown"

    known = [
        "Aurobindo", "Mylan", "Cipla", "Strides", "Hetero", "ABBVIE",
        "Emcure", "Macleods", "Ranbaxy", "Alere", "Micro labs",
        "Matrix", "Ranbaxy per Shasun", "Ranbaxy",
    ]
    for name in known:
        if name.lower() in raw.lower():
            # Mylan (formerly Matrix) Nashik -> Mylan
            if name == "Matrix":
                continue
            return name

    # Fall back to first comma-separated token, title-cased
    first_token = raw.split(",")[0].strip()
    return first_token if first_token else "Unknown"


def numeric_or_flag(series: pd.Series, flag_name: str):
    """Split a column that mixes numbers with text placeholders
    (e.g. 'Freight Included in Commodity Cost', 'Invoiced Separately',
    'See DN-XXXX (ID#:XXXXX)') into a numeric column plus a category
    column describing why the numeric value is missing."""
    numeric = pd.to_numeric(series, errors="coerce")

    def categorize(val):
        if pd.notna(pd.to_numeric(val, errors="coerce")):
            return "numeric"
        if not isinstance(val, str):
            return "missing"
        v = val.lower()
        if "included in commodity cost" in v:
            return "included_in_commodity_cost"
        if "invoiced separately" in v:
            return "invoiced_separately"
        if v.startswith("see dn") or "see dn-" in v:
            return "see_related_shipment"
        if "weight captured separately" in v:
            return "captured_separately"
        return "other_non_numeric"

    category = series.apply(categorize)
    return numeric, category


def main():
    print(f"Reading raw file: {RAW_PATH}")
    df = pd.read_csv(RAW_PATH, encoding="utf-8-sig")
    print(f"Raw shape: {df.shape}")

    df.columns = [c.strip() for c in df.columns]

    # --- Drop fully empty / non-analytical columns -------------------------
    drop_cols = [c for c in ["PQ #", "PQ First Sent to Client Date"] if c in df.columns]
    df = df.drop(columns=drop_cols, errors="ignore")

    # --- Parse dates ---------------------------------------------------------
    date_cols = ["PO Sent to Vendor Date", "Scheduled Delivery Date",
                 "Delivered to Client Date", "Delivery Recorded Date"]
    for col in date_cols:
        if col in df.columns:
            df[col] = parse_mixed_date(df[col])

    # --- Lead time (days from PO sent to delivered) --------------------------
    df["lead_time_days"] = (df["Delivered to Client Date"] - df["PO Sent to Vendor Date"]).dt.days
    # Drop physically impossible lead times (negative, or absurd multi-year outliers)
    df.loc[(df["lead_time_days"] < 0) | (df["lead_time_days"] > 900), "lead_time_days"] = np.nan

    # --- Freight cost & weight: split numeric vs. category flag --------------
    df["freight_cost_usd"], df["freight_cost_flag"] = numeric_or_flag(df["Freight Cost (USD)"], "freight")
    df["weight_kg"], df["weight_flag"] = numeric_or_flag(df["Weight (Kilograms)"], "weight")

    # Freight cost per kg, only where both are real numbers and weight > 0
    valid_freight = df["freight_cost_usd"].notna() & df["weight_kg"].notna() & (df["weight_kg"] > 0)
    df["freight_cost_per_kg"] = np.where(valid_freight, df["freight_cost_usd"] / df["weight_kg"], np.nan)

    # --- Standardize manufacturer / vendor name -------------------------------
    df["manufacturer_group"] = df["Manufacturing Site"].apply(standardize_manufacturer)

    # --- Standardize country name whitespace ----------------------------------
    df["Country"] = df["Country"].astype(str).str.strip()

    # --- Line item value sanity ------------------------------------------------
    df["Line Item Value"] = pd.to_numeric(df["Line Item Value"], errors="coerce")

    # --- Save ---------------------------------------------------------------
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False)
    print(f"Wrote cleaned file: {OUT_PATH}  shape={df.shape}")

    # --- Quick data-quality summary printed for the README ----------------
    print("\n--- Data quality summary ---")
    print(f"Rows: {len(df):,}")
    print(f"Date range (PO Sent to Vendor Date): {df['PO Sent to Vendor Date'].min()} to {df['PO Sent to Vendor Date'].max()}")
    print(f"Unique countries: {df['Country'].nunique()}")
    print(f"Unique manufacturer groups: {df['manufacturer_group'].nunique()}")
    print(f"Rows with usable lead_time_days: {df['lead_time_days'].notna().sum():,} "
          f"({df['lead_time_days'].notna().mean():.1%})")
    print(f"Rows with numeric freight cost: {(df['freight_cost_flag']=='numeric').sum():,} "
          f"({(df['freight_cost_flag']=='numeric').mean():.1%})")
    print(f"Rows with numeric weight: {(df['weight_flag']=='numeric').sum():,} "
          f"({(df['weight_flag']=='numeric').mean():.1%})")
    print("\nFreight cost flag breakdown:")
    print(df["freight_cost_flag"].value_counts())
    print("\nTotal Line Item Value (USD): {:,.0f}".format(df["Line Item Value"].sum()))


if __name__ == "__main__":
    main()
