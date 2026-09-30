# 🧭 Silk Route — Global Health Supply Chain Risk & Cost Intelligence

An end-to-end supply chain analytics project on real global health commodity
shipment data: ~10,300 shipments of antiretroviral (ARV) and HIV lab
commodities delivered to 40+ countries between 2006 and 2015, worth roughly
**$1.63B**, sourced from the **USAID Supply Chain Management System (SCMS)
delivery history**.

Instead of another generic "explore the dataset" project, this analysis is
built around three concrete procurement decisions a supply chain team would
actually need to make:

1. **Vendor risk** — which product categories depend on a single supplier,
   and how risky is that dependency?
2. **Freight cost efficiency** — how much extra are we paying for air
   freight, and is that premium justified?
3. **Route reliability** — which countries are chronically slow to deliver
   to, and which are simply unpredictable?

## The business framing

> A health commodities program has shipped $1.6B+ of ARV and HIV lab
> supplies to developing countries. Before the next supplier contract
> cycle, leadership wants to know: how concentrated is our supplier risk,
> are we overpaying for shipping speed we don't need, and which
> countries/routes are quietly underperforming on lead time?

## Key findings

### 1. Vendor concentration risk

- **69 distinct manufacturers** supplied the program, but just **6 vendors
  account for ~80% of all spend** — a textbook Pareto concentration.
- The single largest supplier, **Mylan**, accounts for **26.9%** of total
  program spend ($438M of $1.63B).
- Using the **Herfindahl-Hirschman Index (HHI)** — the standard
  concentration metric used in procurement and antitrust analysis — **4 of
  6 product sub-classifications carry HIGH concentration risk (HHI ≥
  0.25)**, including:
  - **HIV test kits**: Alere supplies 47.5% of a $213M category (HHI 0.306)
  - **ACT (antimalarials)**: a single vendor supplies 89.8% of the category
    (HHI 0.816) — the most extreme single point of failure in the dataset
  - **HIV test ancillary supplies**: Alere again, at 65.4% share (HHI 0.523)

  → **Recommendation**: qualify a second supplier for ACT and HIV test
  kits before the next contract renewal — these categories have no
  meaningful backup vendor today.

### 2. Freight cost efficiency

- **Air freight costs roughly 7.7x more per kilogram than ground options**
  (truck/ocean), averaged across 21 countries with both shipment types.
- In the most extreme case (**Botswana**), air freight costs **60x** more
  per kg than ground shipping.
- Despite this, **air modes account for 77% of all recorded freight
  spend** ($67M of $87M in shipments with usable freight data).
- Median cost per kg: Air $10.00 · Air Charter $4.15 · Truck $2.60 ·
  Ocean $1.69.

  → **Recommendation**: for non-urgent replenishment shipments to
  countries with reliable ground infrastructure, shifting even a modest
  share of volume from air to ground freight would materially cut
  logistics cost — the multiplier makes this the single biggest cost
  lever in the dataset.

### 3. Lead time & route performance

- Overall average lead time (PO sent to delivered): **106 days**
  (median 92 days) — consistent with independent analyses of this same
  dataset.
- **Zimbabwe, Botswana, Vietnam, Côte d'Ivoire, and Congo (DRC)** are the
  five slowest countries by mean lead time (all above 125 days).
- **South Africa and Botswana** stand out as the *least predictable*
  routes (highest lead-time variance), meaning the delay problem there is
  about process consistency, not just distance — these need a different
  fix (carrier/process audit) than a chronically slow route needs
  (schedule adjustment).
- By shipment mode, **Ocean freight has the longest average lead time**
  (177 days) despite being the cheapest per kg, and **Truck the shortest**
  median (4 days) for the routes it's used on — a useful trade-off table
  for planners balancing cost against urgency.

## Repository structure

```
silk-route/
├── data/
│   ├── raw/                          # original USAID/SCMS CSV, untouched
│   └── processed/                    # cleaned dataset used by all scripts
├── scripts/
│   ├── 01_clean.py                   # cleaning & standardization
│   ├── 02_vendor_risk.py             # Pareto + HHI vendor concentration
│   ├── 03_freight_efficiency.py      # freight cost per kg by mode/country
│   └── 04_leadtime_analysis.py       # lead time by country/mode
├── outputs/
│   ├── figures/                      # generated PNG charts
│   └── tables/                       # generated CSV result tables
├── dashboard/
│   └── app.py                        # Streamlit dashboard (3 tabs)
├── requirements.txt
├── LICENSE
└── README.md
```

## How to reproduce

```bash
git clone https://github.com/noob-shahriar/Silk-Route---Global-Health-Supply-Chain-Risk-Cost-Intelligence.git
cd Silk-Route---Global-Health-Supply-Chain-Risk-Cost-Intelligence
pip install -r requirements.txt

python scripts/01_clean.py
python scripts/02_vendor_risk.py
python scripts/03_freight_efficiency.py
python scripts/04_leadtime_analysis.py

# then launch the dashboard
streamlit run dashboard/app.py
```

## Data cleaning notes (worth knowing before you trust a number)

Real procurement data is messy on purpose — several fields mix numbers
with process notes. This project treats that mixing as a finding, not
noise:

- **`Freight Cost (USD)`** and **`Weight (Kilograms)`** contain text
  placeholders like *"Freight Included in Commodity Cost"*, *"Invoiced
  Separately"*, and *"See DN-XXXX"* alongside numeric values. These are
  split into a numeric column plus a category flag (see
  `freight_cost_flag` / `weight_flag`) rather than being silently dropped
  or coerced to zero. **Only 60% of rows have a usable numeric freight
  cost** — every freight-cost finding above is based on that 60%, and the
  README states that explicitly rather than implying full coverage.
- **Dates** mix two formats (`4/29/11` and `5-Sep-11`) in the same column
  and are parsed with `pandas`' mixed-format date parser.
- **Lead time** is only computable for **44% of rows**, because many
  shipments routed "From RDC" (regional distribution center) have
  `"N/A - From RDC"` in the PO-sent-to-vendor date field. This is a real
  limitation of the source data, not a bug in this pipeline — the
  lead-time findings above reflect the subset where both dates exist.
- **Manufacturer names** are inconsistent (`"Aurobindo Unit III, India"`
  vs. `"Aurobindo Unit VII, IN"`) and are standardized into one vendor
  group per company before the concentration analysis, so risk isn't
  artificially split across cosmetic naming variants of the same
  supplier.

The dataset's own documentation also cautions that cost/lead-time
conclusions by specific product-country pairs should be read with
context — this project treats country- and category-level aggregates as
directional signals for a procurement conversation, not precise
guarantees.

## Tech stack

Python · pandas · matplotlib · Streamlit · Plotly

## Data source

USAID Supply Chain Shipment Pricing Data / SCMS Delivery History —
originally released by USAID, mirrored on Kaggle. Source:
https://data.usaid.gov/d/a3rc-nmf6
