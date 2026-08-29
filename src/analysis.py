"""Clean, analyze, and visualize the retail-sales dataset."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"
RAW_PATH = DATA_DIR / "retail_sales_raw.csv"
CLEAN_PATH = DATA_DIR / "retail_sales_clean.csv"

ACCENT = "#169f8d"
DARK = "#1f2933"
LIGHT = "#e8f5f2"


def load_and_clean(path: Path) -> tuple[pd.DataFrame, dict[str, int]]:
    """Load raw data, correct quality issues, and engineer analytical fields."""
    data = pd.read_csv(path)
    quality_before = {
        "raw_rows": len(data),
        "duplicate_rows": int(data.duplicated().sum()),
        "missing_discount": int(data["Discount"].isna().sum()),
        "missing_city": int(data["City"].isna().sum()),
    }

    data = data.drop_duplicates().copy()
    data["OrderDate"] = pd.to_datetime(data["OrderDate"], errors="raise")
    data["Discount"] = data["Discount"].fillna(0.0).clip(0, 0.50)
    data["City"] = data["City"].fillna("Unknown")

    numeric_columns = ["Units", "UnitPrice", "UnitCost"]
    for column in numeric_columns:
        data[column] = pd.to_numeric(data[column], errors="raise")

    invalid_rows = (
        (data["Units"] <= 0)
        | (data["UnitPrice"] <= 0)
        | (data["UnitCost"] < 0)
        | (data["UnitCost"] > data["UnitPrice"] * 1.5)
    )
    quality_before["invalid_rows_removed"] = int(invalid_rows.sum())
    data = data.loc[~invalid_rows].copy()

    data["GrossRevenue"] = data["Units"] * data["UnitPrice"]
    data["NetRevenue"] = data["GrossRevenue"] * (1 - data["Discount"])
    data["TotalCost"] = data["Units"] * data["UnitCost"]
    data["Profit"] = data["NetRevenue"] - data["TotalCost"]
    data["ProfitMarginPct"] = np.where(
        data["NetRevenue"].ne(0), 100 * data["Profit"] / data["NetRevenue"], 0
    )
    data["Month"] = data["OrderDate"].dt.to_period("M").astype(str)
    data["Quarter"] = data["OrderDate"].dt.to_period("Q").astype(str)

    money_columns = ["GrossRevenue", "NetRevenue", "TotalCost", "Profit", "ProfitMarginPct"]
    data[money_columns] = data[money_columns].round(2)
    return data, quality_before


def build_summaries(data: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Create business summary tables."""
    category_summary = (
        data.groupby("Category", as_index=False)
        .agg(
            Orders=("OrderID", "nunique"),
            Units=("Units", "sum"),
            Revenue=("NetRevenue", "sum"),
            Profit=("Profit", "sum"),
        )
        .assign(ProfitMarginPct=lambda frame: 100 * frame["Profit"] / frame["Revenue"])
        .sort_values("Revenue", ascending=False)
    )

    monthly_summary = (
        data.groupby("Month", as_index=False)
        .agg(Orders=("OrderID", "nunique"), Revenue=("NetRevenue", "sum"), Profit=("Profit", "sum"))
        .sort_values("Month")
    )
    monthly_summary["RevenueGrowthPct"] = monthly_summary["Revenue"].pct_change().mul(100)

    regional_summary = (
        data.groupby("Region", as_index=False)
        .agg(Orders=("OrderID", "nunique"), Revenue=("NetRevenue", "sum"), Profit=("Profit", "sum"))
        .assign(ProfitMarginPct=lambda frame: 100 * frame["Profit"] / frame["Revenue"])
        .sort_values("Revenue", ascending=False)
    )

    top_products = (
        data.groupby(["Product", "Category"], as_index=False)
        .agg(Units=("Units", "sum"), Revenue=("NetRevenue", "sum"), Profit=("Profit", "sum"))
        .sort_values("Revenue", ascending=False)
        .head(10)
    )

    return {
        "category": category_summary.round(2),
        "monthly": monthly_summary.round(2),
        "regional": regional_summary.round(2),
        "top_products": top_products.round(2),
    }


def save_charts(summaries: dict[str, pd.DataFrame]) -> None:
    """Export three decision-ready charts."""
    plt.style.use("seaborn-v0_8-whitegrid")

    monthly = summaries["monthly"]
    fig, axis = plt.subplots(figsize=(11, 5.5))
    axis.plot(monthly["Month"], monthly["Revenue"], marker="o", linewidth=2.5, color=ACCENT)
    axis.fill_between(monthly["Month"], monthly["Revenue"], color=LIGHT, alpha=0.8)
    axis.set_title("Monthly Net Revenue", fontsize=16, fontweight="bold", color=DARK)
    axis.set_ylabel("Revenue")
    axis.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "monthly_revenue.png", dpi=180)
    plt.close(fig)

    category = summaries["category"].sort_values("Revenue")
    fig, axis = plt.subplots(figsize=(9, 5.5))
    axis.barh(category["Category"], category["Revenue"], color=ACCENT)
    axis.set_title("Revenue by Product Category", fontsize=16, fontweight="bold", color=DARK)
    axis.set_xlabel("Net revenue")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "category_performance.png", dpi=180)
    plt.close(fig)

    regional = summaries["regional"].sort_values("ProfitMarginPct")
    fig, axis = plt.subplots(figsize=(9, 5.5))
    axis.barh(regional["Region"], regional["ProfitMarginPct"], color=ACCENT)
    axis.set_title("Profit Margin by Region", fontsize=16, fontweight="bold", color=DARK)
    axis.set_xlabel("Profit margin (%)")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "regional_profit_margin.png", dpi=180)
    plt.close(fig)


def write_report(
    data: pd.DataFrame,
    quality: dict[str, int],
    summaries: dict[str, pd.DataFrame],
) -> None:
    """Write a concise Markdown report from the calculated results."""
    total_revenue = data["NetRevenue"].sum()
    total_profit = data["Profit"].sum()
    profit_margin = 100 * total_profit / total_revenue
    top_category = summaries["category"].iloc[0]
    top_region = summaries["regional"].iloc[0]
    top_product = summaries["top_products"].iloc[0]
    best_month = summaries["monthly"].sort_values("Revenue", ascending=False).iloc[0]

    report = f"""# Retail Sales Analysis Report

## Executive summary

- **Net revenue:** ${total_revenue:,.2f}
- **Profit:** ${total_profit:,.2f}
- **Overall profit margin:** {profit_margin:,.1f}%
- **Orders analyzed:** {data['OrderID'].nunique():,}
- **Units sold:** {int(data['Units'].sum()):,}

## Data quality

- Raw rows: {quality['raw_rows']:,}
- Duplicate rows removed: {quality['duplicate_rows']:,}
- Missing discounts replaced with 0: {quality['missing_discount']:,}
- Missing cities labeled Unknown: {quality['missing_city']:,}
- Invalid rows removed: {quality['invalid_rows_removed']:,}

## Key findings

1. **{top_category['Category']}** is the leading category by revenue at ${top_category['Revenue']:,.2f}.
2. **{top_region['Region']}** is the highest-revenue region at ${top_region['Revenue']:,.2f}.
3. **{top_product['Product']}** is the top product by revenue at ${top_product['Revenue']:,.2f}.
4. **{best_month['Month']}** is the strongest month with ${best_month['Revenue']:,.2f} in net revenue.
5. Category and regional profit margins should be reviewed alongside revenue to avoid prioritizing sales volume at the expense of profitability.

## Recommended actions

- Protect stock availability for the leading products and categories.
- Review campaigns used during the strongest months and reuse the most effective patterns.
- Investigate regions with strong revenue but below-average margins.
- Track channel and customer-segment performance in the next reporting cycle.
"""
    (OUTPUT_DIR / "analysis_report.md").write_text(report, encoding="utf-8")


def main() -> None:
    if not RAW_PATH.exists():
        raise FileNotFoundError("Raw data not found. Run src/generate_data.py first.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    data, quality = load_and_clean(RAW_PATH)
    summaries = build_summaries(data)

    data.to_csv(CLEAN_PATH, index=False)
    summaries["category"].to_csv(OUTPUT_DIR / "category_summary.csv", index=False)
    summaries["monthly"].to_csv(OUTPUT_DIR / "monthly_summary.csv", index=False)
    summaries["regional"].to_csv(OUTPUT_DIR / "regional_summary.csv", index=False)
    summaries["top_products"].to_csv(OUTPUT_DIR / "top_products.csv", index=False)
    save_charts(summaries)
    write_report(data, quality, summaries)

    print(f"Analysis complete. Clean rows: {len(data):,}")
    print(f"Net revenue: ${data['NetRevenue'].sum():,.2f}")
    print(f"Profit: ${data['Profit'].sum():,.2f}")


if __name__ == "__main__":
    main()
