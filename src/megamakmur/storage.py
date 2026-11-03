from __future__ import annotations

import csv
import sqlite3
from datetime import date
from pathlib import Path
from typing import List

from megamakmur.models import (
    BankMutation,
    JobStatus,
    TierCategory,
    VehicleListing,
    WorkshopJob,
)


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS scouting_radar (
    unit_id TEXT PRIMARY KEY,
    batch_date TEXT NOT NULL,
    tier TEXT NOT NULL,
    unit_name TEXT NOT NULL,
    manufacture_year INTEGER NOT NULL,
    plate_location TEXT NOT NULL,
    ask_price_idr INTEGER NOT NULL,
    target_buy_idr INTEGER NOT NULL,
    walk_away_idr INTEGER NOT NULL,
    recon_hpp_idr INTEGER NOT NULL,
    target_exit_idr INTEGER NOT NULL,
    credit_eligible INTEGER NOT NULL,
    leasing_partner TEXT NOT NULL,
    windfall_flag TEXT NOT NULL,
    risk_notes TEXT NOT NULL,
    variation_plan TEXT NOT NULL,
    listing_url TEXT NOT NULL,
    inspection_status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workshop_jobs (
    job_code TEXT PRIMARY KEY,
    entry_date TEXT NOT NULL,
    customer_name TEXT NOT NULL,
    whatsapp_number TEXT NOT NULL,
    vehicle_model TEXT NOT NULL,
    license_plate TEXT NOT NULL,
    service_category TEXT NOT NULL,
    service_detail TEXT NOT NULL,
    technician TEXT NOT NULL,
    price_charged_idr INTEGER NOT NULL,
    material_cost_idr INTEGER NOT NULL,
    amount_paid_idr INTEGER NOT NULL,
    status TEXT NOT NULL,
    payment_method TEXT NOT NULL,
    completion_date TEXT
);
"""


def init_database(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA_SQL)
        conn.commit()


def load_listings_from_csv(csv_path: Path) -> List[VehicleListing]:
    listings: List[VehicleListing] = []
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            listings.append(
                VehicleListing(
                    unit_id=row["unit_id"].strip(),
                    batch_date=date.fromisoformat(row["batch_date"].strip()),
                    tier=TierCategory(row["tier"].strip()),
                    unit_name=row["unit_name"].strip(),
                    manufacture_year=int(row["manufacture_year"]),
                    plate_location=row["plate_location"].strip(),
                    ask_price_idr=int(row["ask_price_idr"]),
                    target_buy_idr=int(row["target_buy_idr"]),
                    walk_away_idr=int(row["walk_away_idr"]),
                    recon_hpp_idr=int(row["recon_hpp_idr"]),
                    target_exit_idr=int(row["target_exit_idr"]),
                    credit_eligible=row["credit_eligible"].strip().lower() in ("true", "1", "ya", "yes"),
                    leasing_partner=row["leasing_partner"].strip(),
                    windfall_flag=row["windfall_flag"].strip(),
                    risk_notes=row["risk_notes"].strip(),
                    variation_plan=row["variation_plan"].strip(),
                    listing_url=row["listing_url"].strip(),
                    inspection_status=row.get("inspection_status", "Belum Dicek").strip(),
                )
            )
    return listings


def save_listings_to_db(db_path: Path, listings: List[VehicleListing]) -> int:
    init_database(db_path)
    with sqlite3.connect(db_path) as conn:
        for item in listings:
            conn.execute(
                """
                INSERT OR REPLACE INTO scouting_radar (
                    unit_id, batch_date, tier, unit_name, manufacture_year,
                    plate_location, ask_price_idr, target_buy_idr, walk_away_idr,
                    recon_hpp_idr, target_exit_idr, credit_eligible, leasing_partner,
                    windfall_flag, risk_notes, variation_plan, listing_url, inspection_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.unit_id,
                    item.batch_date.isoformat(),
                    item.tier.value,
                    item.unit_name,
                    item.manufacture_year,
                    item.plate_location,
                    item.ask_price_idr,
                    item.target_buy_idr,
                    item.walk_away_idr,
                    item.recon_hpp_idr,
                    item.target_exit_idr,
                    1 if item.credit_eligible else 0,
                    item.leasing_partner,
                    item.windfall_flag,
                    item.risk_notes,
                    item.variation_plan,
                    item.listing_url,
                    item.inspection_status,
                ),
            )
        conn.commit()
    return len(listings)


def load_workshop_jobs_from_csv(csv_path: Path) -> List[WorkshopJob]:
    jobs: List[WorkshopJob] = []
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            comp_str = row.get("completion_date", "").strip()
            jobs.append(
                WorkshopJob(
                    job_code=row["job_code"].strip(),
                    entry_date=date.fromisoformat(row["entry_date"].strip()),
                    customer_name=row["customer_name"].strip(),
                    whatsapp_number=row["whatsapp_number"].strip(),
                    vehicle_model=row["vehicle_model"].strip(),
                    license_plate=row["license_plate"].strip(),
                    service_category=row["service_category"].strip(),
                    service_detail=row["service_detail"].strip(),
                    technician=row["technician"].strip(),
                    price_charged_idr=int(row["price_charged_idr"]),
                    material_cost_idr=int(row["material_cost_idr"]),
                    amount_paid_idr=int(row["amount_paid_idr"]),
                    status=JobStatus(row["status"].strip()),
                    payment_method=row["payment_method"].strip(),
                    completion_date=date.fromisoformat(comp_str) if comp_str else None,
                )
            )
    return jobs


def load_bank_mutations_from_csv(csv_path: Path) -> List[BankMutation]:
    mutations: List[BankMutation] = []
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            mutations.append(
                BankMutation(
                    mutation_id=row["mutation_id"].strip(),
                    tx_date=date.fromisoformat(row["tx_date"].strip()),
                    channel=row["channel"].strip(),
                    amount_idr=int(row["amount_idr"]),
                    reference_Tag=row["reference_tag"].strip(),
                    payer_name=row["payer_name"].strip(),
                    raw_description=row["raw_description"].strip(),
                )
            )
    return mutations
