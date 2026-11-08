import hashlib
import hmac
from pathlib import Path

from megamakmur.arbitrage import evaluate_listing
from megamakmur.storage import load_listings_from_csv, save_listings_to_db
from megamakmur.webhooks import build_fonnte_dispatch_payload, verify_fonnte_signature


DATA_CSV = Path(__file__).resolve().parent.parent / "data" / "scouting_radar_2026_10_31.csv"


def test_fonnte_phone_normalization_and_payload():
    listings = load_listings_from_csv(DATA_CSV)
    unit = listings[0]
    val = evaluate_listing(unit)
    payload = build_fonnte_dispatch_payload("0812-9130-2199", unit, val)

    assert payload["target"] == "6281291302199"
    assert "MB-2026-001" in payload["message"]
    assert "Honda Brio Satya" in payload["message"]


def test_fonnte_hmac_verification():
    body = b'{"event":"message","sender":"6281291302199"}'
    secret = "mega_makmur_webhook_secret"
    sig = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

    assert verify_fonnte_signature(body, sig, secret) is True
    assert verify_fonnte_signature(body, "invalid_signature", secret) is False


def test_sqlite_seeding(tmp_path: Path):
    listings = load_listings_from_csv(DATA_CSV)
    db_file = tmp_path / "test_megamakmur.db"
    inserted = save_listings_to_db(db_file, listings)

    assert inserted == 10
    assert db_file.exists()
