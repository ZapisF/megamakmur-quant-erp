import hashlib
import hmac
import tempfile
import unittest
from pathlib import Path

from megamakmur.arbitrage import evaluate_listing
from megamakmur.storage import load_listings_from_csv, save_listings_to_db
from megamakmur.webhooks import build_fonnte_dispatch_payload, verify_fonnte_signature


DATA_CSV = Path(__file__).resolve().parent.parent / "data" / "scouting_radar_2026_10_31.csv"


class TestWebhooksAndStorage(unittest.TestCase):
    def test_fonnte_phone_normalization_and_payload(self) -> None:
        listings = load_listings_from_csv(DATA_CSV)
        unit = listings[0]
        val = evaluate_listing(unit)
        payload = build_fonnte_dispatch_payload("0812-9130-2199", unit, val)

        self.assertEqual(payload["target"], "6281291302199")
        self.assertIn("MB-2026-001", payload["message"])
        self.assertIn("Honda Brio Satya", payload["message"])

    def test_fonnte_hmac_verification(self) -> None:
        body = b'{"event":"message","sender":"6281291302199"}'
        secret = "mega_makmur_webhook_secret"
        sig = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

        self.assertTrue(verify_fonnte_signature(body, sig, secret))
        self.assertFalse(verify_fonnte_signature(body, "invalid_signature", secret))

    def test_sqlite_seeding(self) -> None:
        listings = load_listings_from_csv(DATA_CSV)
        with tempfile.TemporaryDirectory() as tmpdir:
            db_file = Path(tmpdir) / "test_megamakmur.db"
            inserted = save_listings_to_db(db_file, listings)
            self.assertEqual(inserted, 10)
            self.assertTrue(db_file.exists())


if __name__ == "__main__":
    unittest.main()
