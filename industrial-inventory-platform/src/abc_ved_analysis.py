"""
ABC-VED Analysis module.

ABC classification: ranks components by annual consumption VALUE (unit_cost x
annual demand) using the Pareto principle.
    A = top items contributing ~70% of cumulative value (tight control)
    B = next items contributing ~20% of cumulative value (moderate control)
    C = remaining items contributing ~10% of cumulative value (loose control)

VED classification: ranks components by operational CRITICALITY (independent
of cost).
    V (Vital)     = criticality_score 4-5 -> stockout stops production
    E (Essential) = criticality_score 3   -> stockout causes significant disruption
    D (Desirable) = criticality_score 1-2 -> stockout is manageable

Combining both into a 3x3 matrix (AV, AE, AD, BV, BE, BD, CV, CE, CD) gives a
standard operations-management prioritization used in real procurement/
inventory control -- items that are both high-value AND vital get the
strictest control policy, while low-value/desirable items get the loosest.
"""

import pandas as pd
import numpy as np

DATA_DIR = "data/processed"

VED_MAP = {5: "V", 4: "V", 3: "E", 2: "D", 1: "D"}

CONTROL_POLICY = {
    "AV": "Tight control: continuous review, frequent audits, low safety stock buffer needed due to close monitoring",
    "AE": "Tight control: periodic review, monitor closely",
    "AD": "Moderate control: periodic review despite high value, since impact of stockout is low",
    "BV": "Tight control: this is a Vital item despite moderate value -- treat with priority",
    "BE": "Moderate control: standard periodic review",
    "BD": "Moderate control: standard periodic review",
    "CV": "Tight control: low value but Vital -- keep adequate buffer stock, cheap insurance against stoppage",
    "CE": "Loose control: simple two-bin system sufficient",
    "CD": "Loose control: minimal monitoring, order in bulk infrequently",
}


def load_data():
    inventory = pd.read_csv(f"{DATA_DIR}/inventory_recommendations.csv")
    components = pd.read_csv(f"{DATA_DIR}/components.csv")
    return inventory, components


def classify_abc(df, value_col="annual_value"):
    """Classic Pareto ABC classification based on cumulative % of value."""
    df = df.sort_values(value_col, ascending=False).reset_index(drop=True)
    total_value = df[value_col].sum()
    df["cumulative_value"] = df[value_col].cumsum()
    df["cumulative_pct"] = 100 * df["cumulative_value"] / total_value

    def bucket(pct):
        if pct <= 70:
            return "A"
        elif pct <= 90:
            return "B"
        else:
            return "C"

    df["abc_class"] = df["cumulative_pct"].apply(bucket)
    return df


def build_abc_ved_analysis():
    inventory, components = load_data()

    df = inventory.merge(
        components[["component_id", "unit_cost"]], on="component_id", how="left"
    )

    # annual consumption value = avg daily demand x 365 x unit cost
    df["annual_value"] = df["avg_daily_demand"] * 365 * df["unit_cost"]

    df = classify_abc(df, value_col="annual_value")

    df["ved_class"] = df["criticality_score"].map(VED_MAP)
    df["abc_ved"] = df["abc_class"] + df["ved_class"]
    df["control_policy"] = df["abc_ved"].map(CONTROL_POLICY)

    result_cols = [
        "component_id", "component_name", "machine_type", "criticality_score",
        "unit_cost", "avg_daily_demand", "annual_value", "cumulative_pct",
        "abc_class", "ved_class", "abc_ved", "control_policy", "reorder_status",
    ]
    result = df[result_cols].sort_values("annual_value", ascending=False)

    result.to_csv(f"{DATA_DIR}/abc_ved_classification.csv", index=False)

    print(f"Saved abc_ved_classification.csv -> {result.shape[0]} rows")
    print("\nABC breakdown:")
    print(result["abc_class"].value_counts())
    print("\nVED breakdown:")
    print(result["ved_class"].value_counts())
    print("\nABC-VED matrix (item counts):")
    print(pd.crosstab(result["abc_class"], result["ved_class"]))
    print("\nHighest priority items (AV / BV / CV - all Vital regardless of value class):")
    print(result[result["ved_class"] == "V"][
        ["component_id", "machine_type", "abc_ved", "annual_value"]
    ].to_string(index=False))

    return result


if __name__ == "__main__":
    build_abc_ved_analysis()