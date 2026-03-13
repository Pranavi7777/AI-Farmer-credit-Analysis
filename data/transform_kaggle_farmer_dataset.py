"""
Transform a public credit-risk dataset into a farmer credit dataset.

Primary input (recommended): data/german_credit_data.csv (Kaggle)
Fallback input: data/farmer_transactions.csv (existing project data)
Output: data/farmer_credit_dataset.csv
"""

from __future__ import annotations

from pathlib import Path
import random
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
KAGGLE_INPUT = DATA_DIR / "german_credit_data.csv"
PROJECT_INPUT = DATA_DIR / "farmer_transactions.csv"
OUTPUT_PATH = DATA_DIR / "farmer_credit_dataset.csv"

VILLAGES = ["VILL001", "VILL002", "VILL003", "VILL004", "VILL005"]
CROPS = ["Paddy", "Cotton", "Maize", "Vegetables", "Pulses"]


def safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return float(numerator) / float(denominator)


def map_purchase_type(value: str) -> str:
    text = (value or "").lower()
    if "furniture" in text or "equipment" in text:
        return "Equipment"
    if "car" in text or "domestic" in text:
        return "Fertilizer"
    if "education" in text or "business" in text:
        return "Seeds"
    if "radio" in text or "tv" in text:
        return "Pesticide"
    return "Mixed Inputs"


def compute_score(row: pd.Series) -> int:
    repayment_ratio = min(max(row["repayment_ratio"], 0.0), 1.2)
    credit_utilization = min(max(row["credit_utilization"], 0.0), 1.2)
    outstanding_ratio = min(max(row["outstanding_ratio"], 0.0), 1.2)
    delay_factor = max(0.0, 1.0 - (min(row["payment_delay_days"], 30) / 30.0))
    consistency_factor = 1.0 if row["transaction_consistency"] == "regular" else 0.55
    weather_factor = 1.0 - min(max(row.get("weather_risk_index", 0.4), 0.0), 1.0)
    input_dependency = min(max(row.get("input_dependency", 0.5), 0.0), 1.2)
    input_factor = 1.0 - min(input_dependency, 1.0)

    crop_type = str(row.get("crop_type", "mixed")).lower()
    crop_stability = {
        "paddy": 0.8,
        "maize": 0.76,
        "wheat": 0.79,
        "pulses": 0.72,
        "vegetables": 0.68,
        "cotton": 0.63,
        "sugarcane": 0.66
    }.get(crop_type, 0.72)

    score = (
        repayment_ratio * 350
        + (1 - min(credit_utilization, 1.0)) * 250
        + (1 - min(outstanding_ratio, 1.0)) * 200
        + delay_factor * 100
        + consistency_factor * 50
        + weather_factor * 70
        + input_factor * 60
        + crop_stability * 40
    )
    return int(max(300, min(900, 300 + score)))


def classify_risk(score: int) -> str:
    if score >= 750:
        return "LOW"
    if score >= 550:
        return "MEDIUM"
    return "HIGH"


def transform_from_kaggle(df: pd.DataFrame) -> pd.DataFrame:
    result = pd.DataFrame()
    result["farmer_id"] = [f"F{idx:05d}" for idx in range(1, len(df) + 1)]
    result["farmer_age"] = df["Age"].astype(int)
    result["farmer_gender"] = df["Sex"].fillna("male").str.lower()
    result["village_code"] = [random.choice(VILLAGES) for _ in range(len(df))]

    housing_map = {"own": "owned", "rent": "rented", "free": "shared"}
    result["land_ownership"] = df["Housing"].str.lower().map(housing_map).fillna("rented")

    job_map = {0: "low", 1: "medium", 2: "high", 3: "high"}
    result["farm_activity_level"] = df["Job"].map(job_map).fillna("medium")

    result["crop_type"] = [random.choice(CROPS) for _ in range(len(df))]
    result["season_income"] = (df["Credit amount"].astype(float) * 1.75).round(2)
    result["purchase_type"] = df["Purpose"].fillna("mixed").apply(map_purchase_type)

    result["total_purchases"] = (df["Credit amount"].astype(float) * 1.28).round(2)
    result["credit_taken"] = df["Credit amount"].astype(float)

    random_ratio = [random.uniform(0.40, 0.96) for _ in range(len(df))]
    result["payments_made"] = (result["credit_taken"] * random_ratio).round(2)
    result["outstanding_balance"] = (result["credit_taken"] - result["payments_made"]).round(2)

    result["repayment_ratio"] = result.apply(
        lambda row: round(safe_div(row["payments_made"], row["credit_taken"]), 4), axis=1
    )
    result["credit_utilization"] = result.apply(
        lambda row: round(safe_div(row["credit_taken"], row["total_purchases"]), 4), axis=1
    )
    result["outstanding_ratio"] = result.apply(
        lambda row: round(safe_div(row["outstanding_balance"], row["credit_taken"]), 4), axis=1
    )

    result["payment_delay_days"] = df["Duration"].astype(int).apply(lambda x: max(0, min(45, int(x / 2))))
    result["transaction_consistency"] = result.apply(
        lambda row: "regular" if row["repayment_ratio"] >= 0.75 and row["payment_delay_days"] <= 7 else "irregular",
        axis=1,
    )

    result["weather_risk_index"] = result.apply(
        lambda row: round(
            min(
                max(
                    0.2
                    + (0.25 if row["crop_type"] in ["Paddy", "Cotton"] else 0.12)
                    + (0.1 if row["transaction_consistency"] == "irregular" else 0.0),
                    0.05,
                ),
                0.95,
            ),
            4,
        ),
        axis=1,
    )
    result["input_dependency"] = result.apply(
        lambda row: round(safe_div(row["credit_taken"], row["total_purchases"]), 4),
        axis=1,
    )

    result["source_dataset"] = "kaggle_german_credit"
    result["credit_score"] = result.apply(compute_score, axis=1)
    result["risk_level"] = result["credit_score"].apply(classify_risk)
    return result


def transform_from_project_sample(df: pd.DataFrame) -> pd.DataFrame:
    result = pd.DataFrame()
    result["farmer_id"] = [f"F{idx:05d}" for idx in range(1, len(df) + 1)]
    result["farmer_age"] = [random.randint(24, 62) for _ in range(len(df))]
    result["farmer_gender"] = [random.choice(["male", "female"]) for _ in range(len(df))]
    result["village_code"] = df["VillageCode"].astype(str)
    result["land_ownership"] = [random.choice(["owned", "rented"]) for _ in range(len(df))]
    result["farm_activity_level"] = [random.choice(["low", "medium", "high"]) for _ in range(len(df))]
    result["crop_type"] = [random.choice(CROPS) for _ in range(len(df))]
    result["season_income"] = (df["TotalPurchase"].astype(float) * 1.65).round(2)
    result["purchase_type"] = "Mixed Inputs"

    result["total_purchases"] = df["TotalPurchase"].astype(float)
    result["credit_taken"] = df["CreditTaken"].astype(float)
    result["payments_made"] = df["PaymentDone"].astype(float)
    result["outstanding_balance"] = df["OutstandingAmount"].astype(float)

    result["repayment_ratio"] = result.apply(
        lambda row: round(safe_div(row["payments_made"], row["credit_taken"]), 4), axis=1
    )
    result["credit_utilization"] = result.apply(
        lambda row: round(safe_div(row["credit_taken"], row["total_purchases"]), 4), axis=1
    )
    result["outstanding_ratio"] = result.apply(
        lambda row: round(safe_div(row["outstanding_balance"], row["credit_taken"]), 4), axis=1
    )

    result["payment_delay_days"] = df["DelayDays"].astype(int)
    result["transaction_consistency"] = result.apply(
        lambda row: "regular" if row["repayment_ratio"] >= 0.75 and row["payment_delay_days"] <= 7 else "irregular",
        axis=1,
    )

    result["weather_risk_index"] = result["village_code"].map(
        {
            "VILL001": 0.36,
            "VILL002": 0.31,
            "VILL003": 0.48,
            "VILL004": 0.4,
            "VILL005": 0.34,
        }
    ).fillna(0.4)
    result["input_dependency"] = result.apply(
        lambda row: round(safe_div(row["credit_taken"], row["total_purchases"]), 4),
        axis=1,
    )

    result["source_dataset"] = "project_reference_sample"
    result["credit_score"] = result.apply(compute_score, axis=1)
    result["risk_level"] = result["credit_score"].apply(classify_risk)
    return result


def main() -> None:
    random.seed(42)

    if KAGGLE_INPUT.exists():
        input_df = pd.read_csv(KAGGLE_INPUT)
        output_df = transform_from_kaggle(input_df)
        source_name = KAGGLE_INPUT.name
    elif PROJECT_INPUT.exists():
        input_df = pd.read_csv(PROJECT_INPUT)
        output_df = transform_from_project_sample(input_df)
        source_name = PROJECT_INPUT.name
    else:
        raise FileNotFoundError(
            "Input file missing. Add data/german_credit_data.csv or data/farmer_transactions.csv"
        )

    output_df.to_csv(OUTPUT_PATH, index=False)
    print(f"Input source: {source_name}")
    print(f"Rows generated: {len(output_df)}")
    print(f"Saved output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
