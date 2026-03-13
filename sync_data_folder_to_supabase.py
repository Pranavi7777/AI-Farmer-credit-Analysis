"""
Sync local data folder CSV files into Supabase/PostgreSQL.

What it does:
1) Imports farmer summary values from data/farmer_transactions.csv into farmers table.
2) Archives every CSV row from data/*.csv into data_lake_records table.

This script is idempotent for data_lake_records using record_hash dedup.
"""

import csv
import hashlib
import json
from pathlib import Path

from utils.database import init_database, Farmer, DataLakeRecord

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
FARMER_TX_CSV = DATA_DIR / "farmer_transactions.csv"


def _stable_hash(source_file: str, row: dict) -> str:
    payload = json.dumps(row, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(f"{source_file}|{payload}".encode("utf-8")).hexdigest()


def _to_float(value, default=0.0):
    try:
        if value is None or value == "":
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _extract_farmer_fields(row: dict):
    farmer_unique_id = row.get("FarmerUniqueID") or row.get("farmer_unique_id") or ""
    village_code = row.get("VillageCode") or row.get("village_code") or "VILL001"

    if not farmer_unique_id:
        mobile = str(row.get("mobile") or "0000000000")
        farmer_unique_id = f"{mobile}{village_code}"
    else:
        mobile = farmer_unique_id[:10] if len(farmer_unique_id) >= 10 else str(row.get("mobile") or "0000000000")

    return {
        "farmer_unique_id": farmer_unique_id,
        "mobile": mobile,
        "village_code": village_code,
        "total_purchases": _to_float(row.get("TotalPurchase") or row.get("total_purchases"), 0.0),
        "total_credit_taken": _to_float(row.get("CreditTaken") or row.get("credit_taken"), 0.0),
        "total_payments": _to_float(row.get("PaymentDone") or row.get("payments_made"), 0.0),
        "current_outstanding": _to_float(row.get("OutstandingAmount") or row.get("outstanding_balance"), 0.0),
    }


def sync_farmer_summaries(session):
    imported = 0
    updated = 0

    if not FARMER_TX_CSV.exists():
        return imported, updated

    with FARMER_TX_CSV.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fields = _extract_farmer_fields(row)
            if not fields["farmer_unique_id"]:
                continue

            farmer = session.query(Farmer).filter_by(farmer_unique_id=fields["farmer_unique_id"]).first()
            if farmer:
                farmer.total_purchases = fields["total_purchases"]
                farmer.total_credit_taken = fields["total_credit_taken"]
                farmer.total_payments = fields["total_payments"]
                farmer.current_outstanding = fields["current_outstanding"]
                updated += 1
            else:
                farmer = Farmer(
                    farmer_unique_id=fields["farmer_unique_id"],
                    mobile=fields["mobile"],
                    village_code=fields["village_code"],
                    farmer_name="Imported Farmer",
                    total_purchases=fields["total_purchases"],
                    total_credit_taken=fields["total_credit_taken"],
                    total_payments=fields["total_payments"],
                    current_outstanding=fields["current_outstanding"],
                )
                session.add(farmer)
                imported += 1

    return imported, updated


def sync_all_csv_to_data_lake(session):
    inserted = 0
    skipped = 0

    for csv_file in sorted(DATA_DIR.glob("*.csv")):
        with csv_file.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                record_hash = _stable_hash(csv_file.name, row)
                exists = session.query(DataLakeRecord).filter_by(
                    source_file=csv_file.name,
                    record_hash=record_hash,
                ).first()
                if exists:
                    skipped += 1
                    continue

                rec = DataLakeRecord(
                    source_file=csv_file.name,
                    record_hash=record_hash,
                    payload_json=json.dumps(row, sort_keys=True, ensure_ascii=True),
                )
                session.add(rec)
                inserted += 1

    return inserted, skipped


def main():
    engine, SessionLocal = init_database(use_postgresql=True)

    db_host = str(engine.url.host or "")
    if "supabase.com" not in db_host:
        raise RuntimeError(f"Refusing to sync: active DB host is not Supabase ({db_host})")

    session = SessionLocal()
    try:
        imported, updated = sync_farmer_summaries(session)
        lake_inserted, lake_skipped = sync_all_csv_to_data_lake(session)
        session.commit()

        print("SYNC_TARGET_HOST", db_host)
        print("FARMERS_IMPORTED", imported)
        print("FARMERS_UPDATED", updated)
        print("DATA_LAKE_INSERTED", lake_inserted)
        print("DATA_LAKE_SKIPPED", lake_skipped)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
