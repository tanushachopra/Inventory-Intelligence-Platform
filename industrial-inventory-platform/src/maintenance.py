"""
Maintenance module — trains an ML model on machine sensor data to predict
failure risk, projects it forward to estimate days-until-critical per machine,
and cross-references that with the maintenance calendar and linked components
to flag "maintenance-triggered" reorders — independent of demand-based logic.
"""

import pandas as pd
import numpy as np
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
import joblib

DATA_DIR = "data/processed"

FAILURE_RISK_THRESHOLD = 0.55   # above this, a machine is considered at real risk of failure
PROJECTION_DAYS = 30            # how far ahead to project the health trend


def load_data():
    health = pd.read_csv(f"{DATA_DIR}/machine_health.csv", parse_dates=["date"])
    machines = pd.read_csv(f"{DATA_DIR}/machines.csv")
    components = pd.read_csv(f"{DATA_DIR}/components.csv")
    maintenance = pd.read_csv(f"{DATA_DIR}/maintenance_calendar.csv", parse_dates=["scheduled_date"])
    return health, machines, components, maintenance


def train_failure_risk_model(health):
    """Train a regressor: sensor readings -> failure_risk."""
    feature_cols = [
        "air_temperature_K", "process_temperature_K",
        "rotational_speed_rpm", "torque_Nm", "tool_wear_min",
    ]
    X = health[feature_cols]
    y = health["failure_risk"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = XGBRegressor(
        n_estimators=250, max_depth=5, learning_rate=0.08,
        subsample=0.8, colsample_bytree=0.8, random_state=42, n_jobs=-1,
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    r2 = r2_score(y_test, preds)
    print(f"Failure risk model -> MAE: {mae:.4f}, R2: {r2:.4f}")

    joblib.dump(model, f"{DATA_DIR}/failure_risk_model.pkl")
    joblib.dump(feature_cols, f"{DATA_DIR}/failure_risk_features.pkl")

    return model, feature_cols, {"mae": mae, "r2": r2}


def project_days_to_critical(health, model, feature_cols):
    """
    For each machine, use its most recent sensor trend to project forward and
    estimate how many days until predicted failure_risk crosses the threshold.
    Uses simple linear extrapolation of each sensor feature's recent trend,
    then runs the trained model on the projected sensor values.
    """
    results = []

    for machine_id, grp in health.groupby("machine_id"):
        grp = grp.sort_values("date").tail(30).reset_index(drop=True)  # last 30 days of history
        if len(grp) < 5:
            continue

        x = np.arange(len(grp))
        projections = {}
        for col in feature_cols:
            # fit a simple linear trend to the recent sensor values
            slope, intercept = np.polyfit(x, grp[col], 1)
            projections[col] = (slope, intercept, len(grp))

        current_risk = grp["failure_risk"].iloc[-1]
        days_to_critical = None

        for day_ahead in range(1, PROJECTION_DAYS + 1):
            future_x = projections[feature_cols[0]][2] - 1 + day_ahead
            projected_row = {
                col: projections[col][0] * future_x + projections[col][1]
                for col in feature_cols
            }
            feat_df = pd.DataFrame([projected_row])[feature_cols]
            projected_risk = model.predict(feat_df)[0]

            if projected_risk >= FAILURE_RISK_THRESHOLD:
                days_to_critical = day_ahead
                break

        results.append({
            "machine_id": machine_id,
            "current_failure_risk": round(current_risk, 3),
            "current_health_score": round(grp["health_score"].iloc[-1], 1),
            "days_to_critical_risk": days_to_critical,  # None = doesn't cross threshold within horizon
        })

    return pd.DataFrame(results)


def build_maintenance_triggers():
    health, machines, components, maintenance = load_data()
    model, feature_cols, metrics = train_failure_risk_model(health)
    risk_projection = project_days_to_critical(health, model, feature_cols)

    risk_projection = risk_projection.merge(machines, on="machine_id")

    # cross-reference with maintenance calendar: is scheduled maintenance happening
    # before the projected critical point, or is the machine going to hit risk first?
    today_ref = health["date"].max()
    upcoming_maint = (
        maintenance[maintenance["scheduled_date"] >= today_ref]
        .sort_values("scheduled_date")
        .groupby("machine_id")
        .first()
        .reset_index()[["machine_id", "scheduled_date", "maintenance_type"]]
    )
    upcoming_maint["days_to_scheduled_maintenance"] = (
        upcoming_maint["scheduled_date"] - today_ref
    ).dt.days

    risk_projection = risk_projection.merge(upcoming_maint, on="machine_id", how="left")

    def maintenance_flag(row):
        if row["days_to_critical_risk"] is not None and not pd.isna(row["days_to_critical_risk"]):
            if pd.isna(row["days_to_scheduled_maintenance"]) or row["days_to_critical_risk"] < row["days_to_scheduled_maintenance"]:
                return "AT RISK - Before Scheduled Maintenance"
            else:
                return "Monitor - Maintenance Scheduled In Time"
        return "Stable"

    risk_projection["maintenance_status"] = risk_projection.apply(maintenance_flag, axis=1)

    # link to components: which components belong to at-risk machines
    at_risk_machines = risk_projection[
        risk_projection["maintenance_status"] == "AT RISK - Before Scheduled Maintenance"
    ]["machine_id"].tolist()

    components["maintenance_triggered_reorder"] = components["linked_machine_id"].isin(at_risk_machines)

    risk_projection.to_csv(f"{DATA_DIR}/machine_risk_projection.csv", index=False)
    components.to_csv(f"{DATA_DIR}/components.csv", index=False)  # updated with trigger flag

    print(f"\nSaved machine_risk_projection.csv -> {risk_projection.shape[0]} machines")
    print(f"Machines AT RISK before scheduled maintenance: {len(at_risk_machines)}")
    print(risk_projection[["machine_id", "machine_type", "current_health_score",
                            "days_to_critical_risk", "days_to_scheduled_maintenance",
                            "maintenance_status"]].to_string(index=False))

    return risk_projection, components


if __name__ == "__main__":
    build_maintenance_triggers()
