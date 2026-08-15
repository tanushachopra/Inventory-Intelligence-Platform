"""
Data generation module for the Industrial Inventory Intelligence Platform.

Generates realistic synthetic data that mirrors two real-world dataset structures:
1. Store Item Demand Forecasting (Kaggle) -> repurposed as Machine/Component consumption
2. AI4I 2020 Predictive Maintenance Dataset (Kaggle) -> repurposed as Machine health/sensor data

If you download the real Kaggle datasets later, place them in data/raw/ and this
module can be swapped to load them instead (column names are kept compatible).
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

np.random.seed(42)

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
NUM_MACHINES = 10
NUM_COMPONENTS = 25          # raw materials / parts / consumables combined
START_DATE = datetime(2021, 1, 1)
END_DATE = datetime(2025, 12, 31)
SHIFTS = ["Morning", "Evening", "Night"]
SHIFT_SPLIT = {"Morning": 0.40, "Evening": 0.35, "Night": 0.25}

MACHINE_TYPES = [
    "CNC Lathe", "Hydraulic Press", "Injection Molder", "Welding Robot",
    "Conveyor Drive", "Stamping Press", "Assembly Robot Arm",
    "Grinding Machine", "Packaging Unit", "Compressor Unit"
]

COMPONENT_CATEGORIES = ["Raw Material", "Machine Part", "Consumable", "Sub-Assembly Item"]


def generate_machines():
    """Machine master data: id, type, criticality, downtime cost/hour."""
    rows = []
    for i in range(1, NUM_MACHINES + 1):
        m_type = MACHINE_TYPES[(i - 1) % len(MACHINE_TYPES)]
        # criticality driven by a simple rule: certain machine types are inherently
        # more critical to the line (e.g., a press or robot vs a conveyor)
        base_criticality = np.random.choice([1, 2, 3, 4, 5], p=[0.05, 0.15, 0.30, 0.30, 0.20])
        downtime_cost_per_hour = int(np.round(5000 + base_criticality * np.random.uniform(8000, 18000), -2))
        rows.append({
            "machine_id": f"M{i:02d}",
            "machine_type": m_type,
            "criticality_score": base_criticality,       # 1 (low) - 5 (high)
            "downtime_cost_per_hour": downtime_cost_per_hour,
            "install_year": np.random.choice(range(2012, 2023)),
        })
    return pd.DataFrame(rows)


def generate_components(machines_df):
    """Component master data linked to machines: id, name, category, machine linkage, lead time."""
    rows = []
    for i in range(1, NUM_COMPONENTS + 1):
        machine_id = machines_df.sample(1)["machine_id"].values[0]
        category = np.random.choice(COMPONENT_CATEGORIES, p=[0.35, 0.30, 0.25, 0.10])
        lead_time_days = int(np.random.choice([3, 5, 7, 10, 14, 21], p=[0.15, 0.25, 0.25, 0.15, 0.12, 0.08]))
        unit_cost = round(np.random.uniform(50, 5000), 2)
        rows.append({
            "component_id": f"C{i:03d}",
            "component_name": f"{category} {i:03d}",
            "category": category,
            "linked_machine_id": machine_id,
            "lead_time_days": lead_time_days,
            "unit_cost": unit_cost,
        })
    return pd.DataFrame(rows)


def generate_consumption_data(machines_df, components_df):
    """
    Daily component consumption tied to machine production cycles + shift split.
    Mirrors the Store-Item-Demand structure: date, store(=machine), item(=component), sales(=qty consumed)
    """
    dates = pd.date_range(START_DATE, END_DATE, freq="D")
    rows = []

    for _, comp in components_df.iterrows():
        machine_id = comp["linked_machine_id"]
        crit = machines_df.loc[machines_df.machine_id == machine_id, "criticality_score"].values[0]

        base_daily_cycles = np.random.uniform(80, 400)       # base production cycles/day
        consumption_per_cycle = np.random.uniform(0.05, 0.6)  # units of component per cycle

        for d in dates:
            # yearly seasonality + weekday effect + slow growth trend + random noise
            day_of_year = d.timetuple().tm_yday
            seasonal = 1 + 0.15 * np.sin(2 * np.pi * day_of_year / 365)
            weekday_factor = 0.4 if d.weekday() >= 5 else 1.0     # lower output on weekends
            trend = 1 + 0.00015 * (d - START_DATE).days
            noise = np.random.normal(1, 0.08)

            daily_cycles = max(0, base_daily_cycles * seasonal * weekday_factor * trend * noise)

            for shift in SHIFTS:
                shift_cycles = daily_cycles * SHIFT_SPLIT[shift] * np.random.normal(1, 0.05)
                qty_consumed = max(0, round(shift_cycles * consumption_per_cycle, 1))
                rows.append({
                    "date": d,
                    "machine_id": machine_id,
                    "component_id": comp["component_id"],
                    "shift": shift,
                    "production_cycles": round(shift_cycles, 1),
                    "qty_consumed": qty_consumed,
                })

    return pd.DataFrame(rows)


def generate_machine_health_data(machines_df):
    """
    Machine sensor/health data mirroring AI4I 2020 structure:
    air temp, process temp, rotational speed, torque, tool wear -> failure label
    Generates a degrading trend so 'remaining useful life' style logic has signal.
    """
    dates = pd.date_range(START_DATE, END_DATE, freq="D")
    rows = []

    for _, m in machines_df.iterrows():
        # each machine has a random "cycle length" until a maintenance/failure event
        cycle_length = np.random.randint(60, 180)
        day_in_cycle = np.random.randint(0, cycle_length)

        for d in dates:
            wear_fraction = day_in_cycle / cycle_length  # 0 = just maintained, 1 = due for failure

            air_temp = np.random.normal(298, 2) + wear_fraction * 3
            process_temp = air_temp + np.random.normal(10, 1) + wear_fraction * 4
            rot_speed = np.random.normal(1500, 100) - wear_fraction * 150
            torque = np.random.normal(40, 5) + wear_fraction * 10
            tool_wear = wear_fraction * np.random.uniform(180, 250)

            # simple composite health score (100 = perfect, 0 = failing)
            health_score = max(0, round(100 - wear_fraction * 100 + np.random.normal(0, 3), 1))
            failure_risk = round(wear_fraction ** 2, 3)  # accelerating risk near end of cycle

            rows.append({
                "date": d,
                "machine_id": m["machine_id"],
                "air_temperature_K": round(air_temp, 1),
                "process_temperature_K": round(process_temp, 1),
                "rotational_speed_rpm": round(rot_speed, 1),
                "torque_Nm": round(torque, 1),
                "tool_wear_min": round(tool_wear, 1),
                "health_score": health_score,
                "failure_risk": failure_risk,
            })

            day_in_cycle += 1
            if day_in_cycle >= cycle_length:
                day_in_cycle = 0
                cycle_length = np.random.randint(60, 180)  # new cycle after "maintenance"

    return pd.DataFrame(rows)


def generate_maintenance_calendar(machines_df, health_df):
    """Scheduled maintenance events, roughly every 60-120 days per machine.
    Extends 1 year beyond END_DATE so there's always a 'next scheduled maintenance'
    to compare against when projecting risk forward from the most recent sensor data."""
    calendar_end = END_DATE + timedelta(days=365)
    rows = []
    for _, m in machines_df.iterrows():
        current = START_DATE + timedelta(days=int(np.random.uniform(10, 60)))
        while current < calendar_end:
            rows.append({
                "machine_id": m["machine_id"],
                "scheduled_date": current,
                "maintenance_type": np.random.choice(
                    ["Routine Inspection", "Part Replacement", "Full Overhaul"],
                    p=[0.55, 0.35, 0.10]
                ),
            })
            current += timedelta(days=int(np.random.uniform(60, 120)))
    return pd.DataFrame(rows)


def build_all(save_dir="data/processed"):
    machines = generate_machines()
    components = generate_components(machines)
    consumption = generate_consumption_data(machines, components)
    health = generate_machine_health_data(machines)
    maintenance = generate_maintenance_calendar(machines, health)

    machines.to_csv(f"{save_dir}/machines.csv", index=False)
    components.to_csv(f"{save_dir}/components.csv", index=False)
    consumption.to_csv(f"{save_dir}/consumption.csv", index=False)
    health.to_csv(f"{save_dir}/machine_health.csv", index=False)
    maintenance.to_csv(f"{save_dir}/maintenance_calendar.csv", index=False)

    print("Generated files:")
    for name, df in [("machines", machines), ("components", components),
                      ("consumption", consumption), ("machine_health", health),
                      ("maintenance_calendar", maintenance)]:
        print(f"  {name}.csv -> {df.shape[0]} rows, {df.shape[1]} columns")

    return machines, components, consumption, health, maintenance


if __name__ == "__main__":
    build_all()
