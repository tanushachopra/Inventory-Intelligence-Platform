"""
Inventory logic module — the core industrial-engineering math layered on top
of the ML forecast.

Formulas used (standard operations/industrial engineering formulas):
  - Safety Stock   = Z * sigma_demand * sqrt(lead_time) * criticality_multiplier
  - Reorder Point  = (avg_daily_demand * lead_time_days) + Safety Stock
  - EOQ            = sqrt( (2 * annual_demand * ordering_cost) / holding_cost_per_unit )
  - Downtime Cost Impact = downtime_cost_per_hour * estimated_downtime_hours_if_stockout

Criticality multiplier: machines with criticality_score 1-5 get a safety stock
buffer multiplier from 1.0x (least critical) to 1.8x (most critical) on top of
the standard variability-based safety stock — this is the "mechanical core"
layer that goes beyond a plain textbook formula.
"""

import pandas as pd
import numpy as np
from scipy.stats import norm

DATA_DIR = "data/processed"

# Service level -> Z-score (95% service level is a common industry default)
SERVICE_LEVEL = 0.95
Z_SCORE = norm.ppf(SERVICE_LEVEL)

# Assumed generic cost parameters (documented assumptions, adjustable)
ORDERING_COST_PER_ORDER = 500       # INR, cost to place one purchase order
HOLDING_COST_RATE = 0.20            # 20% of unit cost held per year (standard industry assumption)
ASSUMED_DOWNTIME_HOURS_IF_STOCKOUT = 8   # assumption: a stockout causes ~1 shift (8 hrs) of downtime

CRITICALITY_MULTIPLIER = {1: 1.0, 2: 1.15, 3: 1.3, 4: 1.55, 5: 1.8}


def load_data():
    machines = pd.read_csv(f"{DATA_DIR}/machines.csv")
    components = pd.read_csv(f"{DATA_DIR}/components.csv")
    consumption = pd.read_csv(f"{DATA_DIR}/consumption.csv", parse_dates=["date"])
    forecast = pd.read_csv(f"{DATA_DIR}/forecast_next_30_days.csv", parse_dates=["date"])
    return machines, components, consumption, forecast


def compute_demand_stats(consumption):
    """Historical average daily demand and standard deviation, per machine-component."""
    daily = (
        consumption.groupby(["date", "machine_id", "component_id"], as_index=False)
        .agg(qty_consumed=("qty_consumed", "sum"))
    )
    stats = (
        daily.groupby(["machine_id", "component_id"])["qty_consumed"]
        .agg(avg_daily_demand="mean", std_daily_demand="std")
        .reset_index()
    )
    stats["std_daily_demand"] = stats["std_daily_demand"].fillna(0)
    return stats


def compute_current_stock(demand_stats, seed=7):
    """
    Simulate a 'current stock level' snapshot for each item (since we don't have
    a live warehouse feed). Stock is set relative to typical demand so the mix of
    urgent/healthy items is realistic, not arbitrary.
    """
    rng = np.random.default_rng(seed)
    n = len(demand_stats)
    # random multiplier of ~(3 to 25) days worth of average demand currently in stock
    days_of_stock = rng.uniform(3, 25, size=n)
    current_stock = (demand_stats["avg_daily_demand"] * days_of_stock).round(1)
    return current_stock


def build_inventory_recommendations():
    machines, components, consumption, forecast = load_data()
    demand_stats = compute_demand_stats(consumption)

    df = demand_stats.merge(components, left_on="component_id", right_on="component_id")
    df = df.merge(machines, left_on="linked_machine_id", right_on="machine_id", suffixes=("", "_m"))

    df["current_stock"] = compute_current_stock(df)

    # --- Safety Stock: variability + criticality weighted ---
    df["criticality_multiplier"] = df["criticality_score"].map(CRITICALITY_MULTIPLIER)
    df["safety_stock"] = (
        Z_SCORE * df["std_daily_demand"] * np.sqrt(df["lead_time_days"]) * df["criticality_multiplier"]
    ).round(1)

    # --- Reorder Point ---
    df["reorder_point"] = (
        df["avg_daily_demand"] * df["lead_time_days"] + df["safety_stock"]
    ).round(1)

    # --- EOQ ---
    df["annual_demand"] = df["avg_daily_demand"] * 365
    df["holding_cost_per_unit"] = df["unit_cost"] * HOLDING_COST_RATE
    df["eoq"] = np.sqrt(
        (2 * df["annual_demand"] * ORDERING_COST_PER_ORDER) / df["holding_cost_per_unit"]
    ).round(0)

    # --- Days until stockout (using near-term forecast, not just historical avg) ---
    forecast_totals = (
        forecast.groupby(["machine_id", "component_id"])["forecast_qty"]
        .apply(list)
        .reset_index()
        .rename(columns={"forecast_qty": "forecast_series"})
    )
    df = df.merge(forecast_totals, on=["machine_id", "component_id"], how="left")

    def days_to_stockout(row):
        stock = row["current_stock"]
        series = row["forecast_series"]
        if not isinstance(series, list):
            return np.nan
        for i, qty in enumerate(series, start=1):
            stock -= qty
            if stock <= 0:
                return i
        return None  # doesn't stock out within forecast horizon

    df["days_to_stockout"] = df.apply(days_to_stockout, axis=1)

    # --- Reorder status flag ---
    def reorder_status(row):
        if pd.notna(row["days_to_stockout"]) and row["days_to_stockout"] <= row["lead_time_days"]:
            return "URGENT - Order Now"
        elif row["current_stock"] <= row["reorder_point"]:
            return "Reorder Soon"
        else:
            return "Healthy"

    df["reorder_status"] = df.apply(reorder_status, axis=1)

    # --- Downtime cost impact (only meaningful for urgent items) ---
    df["estimated_downtime_cost"] = np.where(
        df["reorder_status"] == "URGENT - Order Now",
        df["downtime_cost_per_hour"] * ASSUMED_DOWNTIME_HOURS_IF_STOCKOUT,
        0
    )

    # --- Recommended order quantity: max(EOQ, enough to reach reorder point + safety stock) ---
    df["recommended_order_qty"] = np.maximum(
        df["eoq"], (df["reorder_point"] - df["current_stock"]).clip(lower=0)
    ).round(0)

    final_cols = [
        "component_id", "component_name", "category", "linked_machine_id", "machine_type",
        "criticality_score", "current_stock", "avg_daily_demand", "std_daily_demand",
        "lead_time_days", "safety_stock", "reorder_point", "eoq",
        "days_to_stockout", "reorder_status", "recommended_order_qty",
        "downtime_cost_per_hour", "estimated_downtime_cost",
    ]
    result = df[final_cols].sort_values(
        by=["reorder_status", "days_to_stockout"],
        key=lambda s: s.map({"URGENT - Order Now": 0, "Reorder Soon": 1, "Healthy": 2}) if s.name == "reorder_status" else s
    )

    result.to_csv(f"{DATA_DIR}/inventory_recommendations.csv", index=False)
    print(f"Saved inventory_recommendations.csv -> {result.shape[0]} rows")
    print(f"\nStatus breakdown:\n{result['reorder_status'].value_counts()}")
    print(f"\nTop 5 most urgent items:")
    print(result[result.reorder_status == "URGENT - Order Now"].head(5)[
        ["component_id", "machine_type", "criticality_score", "days_to_stockout", "estimated_downtime_cost"]
    ].to_string(index=False))

    return result


if __name__ == "__main__":
    build_inventory_recommendations()
