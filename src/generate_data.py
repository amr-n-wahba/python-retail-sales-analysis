"""Generate a deterministic retail-sales dataset with realistic quality issues."""

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_PATH = DATA_DIR / "retail_sales_raw.csv"
RANDOM_SEED = 42


PRODUCTS = {
    "Laptop": [
        ("NovaBook 14", 850.0, 625.0),
        ("CreatorBook 16", 1320.0, 960.0),
        ("WorkMate 15", 710.0, 515.0),
    ],
    "Mobile": [
        ("SmartOne Pro", 780.0, 545.0),
        ("SmartOne Lite", 410.0, 285.0),
        ("Connect X", 590.0, 415.0),
    ],
    "Accessories": [
        ("Wireless Keyboard", 52.0, 29.0),
        ("Ergonomic Mouse", 38.0, 19.0),
        ("USB-C Dock", 115.0, 72.0),
        ("Noise-Canceling Headset", 145.0, 88.0),
    ],
    "Monitor": [
        ("ViewPro 24", 185.0, 124.0),
        ("ViewPro 27 QHD", 315.0, 224.0),
        ("CreatorView 32", 520.0, 381.0),
    ],
}

REGION_CITIES = {
    "Cairo": ["Cairo", "Giza", "New Cairo"],
    "Delta": ["Tanta", "Mansoura", "Zagazig"],
    "Alexandria": ["Alexandria", "Borg El Arab"],
    "Upper Egypt": ["Assiut", "Sohag", "Minya"],
}


def generate_sales(number_of_orders: int = 800) -> pd.DataFrame:
    """Create deterministic transaction-level sales records."""
    rng = np.random.default_rng(RANDOM_SEED)
    start_date = pd.Timestamp("2025-01-01")
    dates = start_date + pd.to_timedelta(rng.integers(0, 365, number_of_orders), unit="D")

    regions = rng.choice(
        list(REGION_CITIES),
        size=number_of_orders,
        p=[0.40, 0.27, 0.20, 0.13],
    )
    categories = rng.choice(
        list(PRODUCTS),
        size=number_of_orders,
        p=[0.28, 0.28, 0.27, 0.17],
    )

    rows = []
    for index, (date, region, category) in enumerate(zip(dates, regions, categories), start=1):
        product_name, base_price, base_cost = PRODUCTS[category][
            rng.integers(0, len(PRODUCTS[category]))
        ]
        seasonal_factor = 1.12 if date.month in (11, 12) else 1.0
        unit_price = round(base_price * seasonal_factor * rng.uniform(0.97, 1.04), 2)
        unit_cost = round(base_cost * rng.uniform(0.98, 1.03), 2)
        units = int(rng.integers(1, 6 if category == "Accessories" else 4))
        discount = float(rng.choice([0, 0.05, 0.10, 0.15], p=[0.54, 0.24, 0.17, 0.05]))

        rows.append(
            {
                "OrderID": f"ORD-{index:05d}",
                "OrderDate": date.strftime("%Y-%m-%d"),
                "Region": region,
                "City": rng.choice(REGION_CITIES[region]),
                "Category": category,
                "Product": product_name,
                "Units": units,
                "UnitPrice": unit_price,
                "Discount": discount,
                "UnitCost": unit_cost,
                "SalesChannel": rng.choice(["Online", "Retail Store", "Corporate"], p=[0.44, 0.39, 0.17]),
                "CustomerSegment": rng.choice(["Consumer", "Small Business", "Enterprise"], p=[0.62, 0.26, 0.12]),
            }
        )

    sales = pd.DataFrame(rows)

    # Add controlled quality issues for the cleaning stage.
    missing_discount_rows = rng.choice(sales.index, size=12, replace=False)
    missing_city_rows = rng.choice(sales.index, size=8, replace=False)
    sales.loc[missing_discount_rows, "Discount"] = np.nan
    sales.loc[missing_city_rows, "City"] = None

    duplicate_rows = sales.sample(5, random_state=RANDOM_SEED)
    sales = pd.concat([sales, duplicate_rows], ignore_index=True)
    return sales


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    sales = generate_sales()
    sales.to_csv(RAW_PATH, index=False)
    print(f"Generated {len(sales):,} raw rows at {RAW_PATH}")


if __name__ == "__main__":
    main()
