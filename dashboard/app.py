"""
Silk Route — Global Health Supply Chain Risk & Cost Intelligence
Streamlit dashboard

Run with:  streamlit run dashboard/app.py
(run from the project root so the relative paths below resolve)
"""

import pandas as pd
import streamlit as st
import plotly.express as px
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data" / "processed" / "shipments_clean.csv"
TABLES = BASE / "outputs" / "tables"

st.set_page_config(page_title="Silk Route — Supply Chain Risk & Cost Intelligence",
                    layout="wide")

st.title("🧭 Silk Route — Global Health Supply Chain Risk & Cost Intelligence")
st.caption("Analysis of ~10,300 real ARV/HIV commodity shipments (USAID/SCMS delivery history, "
           "2006–2015). Source: USAID Supply Chain Shipment Pricing Data.")


@st.cache_data
def load_data():
    df = pd.read_csv(DATA)
    return df


@st.cache_data
def load_table(name):
    return pd.read_csv(TABLES / name)


df = load_data()

tab1, tab2, tab3 = st.tabs(["🏭 Vendor Risk", "✈️ Freight Efficiency", "⏱️ Lead Time"])

# ---------------------------------------------------------------------
# TAB 1: Vendor concentration risk
# ---------------------------------------------------------------------
with tab1:
    st.header("Vendor Concentration Risk")
    st.markdown(
        "Herfindahl-Hirschman Index (HHI) by product category. **HHI ≥ 0.25** is "
        "conventionally treated as high concentration — a single-supplier "
        "dependency risk worth flagging to procurement."
    )

    pareto = load_table("vendor_pareto_overall.csv")
    risk = load_table("vendor_concentration_by_subclass.csv")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total spend analyzed", f"${pareto['spend_usd'].sum()/1e6:,.0f}M")
    col2.metric("Unique manufacturers", f"{len(pareto)}")
    n80 = int((pareto["cumulative_share_pct"] <= 80).sum()) + 1
    col3.metric("Vendors driving 80% of spend", n80)

    fig = px.bar(pareto.head(15), x="vendor", y="spend_usd",
                 title="Top 15 Manufacturers by Spend",
                 labels={"spend_usd": "Spend (USD)", "vendor": "Manufacturer"})
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Risk table by product category")
    def highlight_risk(row):
        color = {"High": "background-color:#ffcccc",
                 "Moderate": "background-color:#fff3cd",
                 "Low": "background-color:#d4edda"}.get(row["risk_tier"], "")
        return [color] * len(row)

    st.dataframe(
        risk.style.apply(highlight_risk, axis=1),
        use_container_width=True,
    )

# ---------------------------------------------------------------------
# TAB 2: Freight efficiency
# ---------------------------------------------------------------------
with tab2:
    st.header("Freight Mode Cost Efficiency")
    st.markdown(
        "Cost per kilogram by shipment mode, and the air-freight premium "
        "paid vs. ground (truck/ocean) options, by country."
    )

    mode_cost = load_table("freight_cost_by_mode.csv")
    premium = load_table("air_freight_premium_by_country.csv")

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(mode_cost.sort_values("median_cost_per_kg"),
                     x="median_cost_per_kg", y="Shipment Mode", orientation="h",
                     title="Median Freight Cost per kg by Mode",
                     labels={"median_cost_per_kg": "USD / kg"})
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        avg_mult = premium["air_premium_multiplier"].mean()
        st.metric("Average air-vs-ground cost multiplier", f"{avg_mult:.1f}x")
        fig2 = px.bar(premium.head(10), x="country", y="air_premium_multiplier",
                      title="Top 10 Countries: Air Freight Premium",
                      labels={"air_premium_multiplier": "Air cost ÷ Ground cost"})
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Full country-level premium table")
    st.dataframe(premium, use_container_width=True)

# ---------------------------------------------------------------------
# TAB 3: Lead time / route performance
# ---------------------------------------------------------------------
with tab3:
    st.header("Lead Time & Route Performance")
    st.markdown(
        "Countries plotted by **mean lead time** (chronic delay) vs. "
        "**standard deviation** (unpredictability). These need different fixes: "
        "a chronically slow but predictable route needs schedule adjustment; "
        "an unpredictable one needs a process or carrier fix."
    )

    leadtime = load_table("leadtime_by_country.csv")

    fig = px.scatter(
        leadtime, x="mean_days", y="std_days", size="n_shipments",
        hover_name="Country", text="Country",
        title="Chronic Delay vs. Unpredictability by Country",
        labels={"mean_days": "Mean lead time (days)", "std_days": "Lead time std-dev (days)"},
    )
    fig.update_traces(textposition="top center")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Full country lead-time table")
    st.dataframe(leadtime.sort_values("mean_days", ascending=False), use_container_width=True)

st.divider()
st.caption(
    "Built as a portfolio project. Data source: USAID Supply Chain Shipment Pricing Data "
    "(SCMS Delivery History). The dataset's own documentation cautions that lead-time and "
    "cost conclusions by product/country carry contextual caveats — see README for details."
)
