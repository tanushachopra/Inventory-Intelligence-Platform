"""
Forecasting module — predicts future component consumption using XGBoost.

Approach:
1. Aggregate consumption to daily level per (machine, component)
2. Engineer time-based features: day of week, month, lag values, rolling averages
3. Train/test split chronologically (train on past, test on most recent period)
4. Train an XGBoost regressor per-feature-set (single global model with machine/component as features)
5. Evaluate with MAE / RMSE
6. Save trained model + a forward forecast for use by the inventory logic module
"""

import pandas as pd
import numpy as np
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
import joblib
import os

DATA_DIR = "data/processed"
MODEL_DIR = "data/processed"


def load_and_aggregate():
    """Load consumption data and aggregate shifts into daily totals per machine-component."""
    df = pd.read_csv(f"{DATA_DIR}/consumption.csv", parse_dates=["date"])
    daily = (
        df.groupby(["date", "machine_id", "component_id"], as_index=False)
        .agg(qty_consumed=("qty_consumed", "sum"), production_cycles=("production_cycles", "sum"))
    )
    return daily


def engineer_features(daily):
    """Create time-based and lag/rolling features per machine-component series."""
    daily = daily.sort_values(["machine_id", "component_id", "date"]).copy()

    daily["day_of_week"] = daily["date"].dt.dayofweek
    daily["month"] = daily["date"].dt.month
    daily["day_of_year"] = daily["date"].dt.dayofyear
    daily["is_weekend"] = (daily["day_of_week"] >= 5).astype(int)

    group = daily.groupby(["machine_id", "component_id"])["qty_consumed"]

    # lag features (yesterday, last week)
    daily["lag_1"] = group.shift(1)
    daily["lag_7"] = group.shift(7)

    # rolling averages (past 7-day and 30-day, shifted so no leakage)
    daily["rolling_mean_7"] = group.transform(lambda s: s.shift(1).rolling(7).mean())
    daily["rolling_mean_30"] = group.transform(lambda s: s.shift(1).rolling(30).mean())

    # encode machine_id / component_id as categorical codes for the model
    daily["machine_code"] = daily["machine_id"].astype("category").cat.codes
    daily["component_code"] = daily["component_id"].astype("category").cat.codes

    daily = daily.dropna().reset_index(drop=True)
    return daily


def train_model(daily, test_days=90):
    """Chronological train/test split and XGBoost training."""
    feature_cols = [
        "day_of_week", "month", "day_of_year", "is_weekend",
        "lag_1", "lag_7", "rolling_mean_7", "rolling_mean_30",
        "machine_code", "component_code", "production_cycles",
    ]
    target_col = "qty_consumed"

    cutoff_date = daily["date"].max() - pd.Timedelta(days=test_days)
    train = daily[daily["date"] <= cutoff_date]
    test = daily[daily["date"] > cutoff_date]

    X_train, y_train = train[feature_cols], train[target_col]
    X_test, y_test = test[feature_cols], test[target_col]

    model = XGBRegressor(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    mean_actual = y_test.mean()

    print(f"Test period: {test['date'].min().date()} to {test['date'].max().date()} ({len(test)} rows)")
    print(f"MAE:  {mae:.2f}  (avg actual consumption: {mean_actual:.2f})")
    print(f"RMSE: {rmse:.2f}")
    print(f"MAE as % of average consumption: {100 * mae / mean_actual:.1f}%")

    return model, feature_cols, {"mae": mae, "rmse": rmse, "mean_actual": mean_actual}


def forecast_forward(model, daily, feature_cols, horizon_days=30):
    """
    Generate a forward forecast per machine-component for the next `horizon_days`.
    Uses a simple recursive approach: predict one day, feed it back in as a lag for the next.
    """
    last_date = daily["date"].max()
    results = []

    for (machine_id, component_id), group in daily.groupby(["machine_id", "component_id"]):
        group = group.sort_values("date")
        history = group["qty_consumed"].tolist()
        machine_code = group["machine_code"].iloc[-1]
        component_code = group["component_code"].iloc[-1]
        avg_cycles = group["production_cycles"].tail(30).mean()

        for i in range(1, horizon_days + 1):
            forecast_date = last_date + pd.Timedelta(days=i)
            lag_1 = history[-1]
            lag_7 = history[-7] if len(history) >= 7 else np.mean(history)
            rolling_mean_7 = np.mean(history[-7:])
            rolling_mean_30 = np.mean(history[-30:]) if len(history) >= 30 else np.mean(history)

            feat = pd.DataFrame([{
                "day_of_week": forecast_date.dayofweek,
                "month": forecast_date.month,
                "day_of_year": forecast_date.dayofyear,
                "is_weekend": int(forecast_date.dayofweek >= 5),
                "lag_1": lag_1,
                "lag_7": lag_7,
                "rolling_mean_7": rolling_mean_7,
                "rolling_mean_30": rolling_mean_30,
                "machine_code": machine_code,
                "component_code": component_code,
                "production_cycles": avg_cycles,
            }])[feature_cols]

            pred = max(0, model.predict(feat)[0])
            history.append(pred)

            results.append({
                "date": forecast_date,
                "machine_id": machine_id,
                "component_id": component_id,
                "forecast_qty": round(pred, 1),
            })

    return pd.DataFrame(results)


def run_pipeline():
    daily = load_and_aggregate()
    featured = engineer_features(daily)
    model, feature_cols, metrics = train_model(featured)

    forecast_df = forecast_forward(model, featured, feature_cols, horizon_days=30)
    forecast_df.to_csv(f"{DATA_DIR}/forecast_next_30_days.csv", index=False)

    joblib.dump(model, f"{MODEL_DIR}/xgb_consumption_model.pkl")
    joblib.dump(feature_cols, f"{MODEL_DIR}/xgb_feature_cols.pkl")

    print(f"\nForecast saved: {forecast_df.shape[0]} rows -> forecast_next_30_days.csv")
    print(f"Model saved: xgb_consumption_model.pkl")

    return model, metrics, forecast_df


if __name__ == "__main__":
    run_pipeline()
