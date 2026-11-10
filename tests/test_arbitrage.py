import unittest
from datetime import date
from pathlib import Path

from megamakmur.arbitrage import evaluate_listing, optimize_capital_allocation
from megamakmur.models import TierCategory, VehicleListing
from megamakmur.storage import load_listings_from_csv


DATA_CSV = Path(__file__).resolve().parent.parent / "data" / "scouting_radar_2026_10_31.csv"


class TestArbitrageEngine(unittest.TestCase):
    def setUp(self) -> None:
        self.listings = load_listings_from_csv(DATA_CSV)

    def test_evaluate_innova_reborn_windfall(self) -> None:
        innova = next(u for u in self.listings if u.unit_id == "MB-2026-005")
        val = evaluate_listing(innova)

        # Target Buy 272M + HPP 8.5M + Nego Buffer 5M + Mech Reserve 2M = 287.5M
        # Target Exit 312M - 287.5M = 24.5M net profit
        self.assertEqual(val.all_in_cost_at_target_idr, 287_500_000)
        self.assertEqual(val.net_profit_at_target_idr, 24_500_000)
        self.assertTrue(val.is_viable_at_target)
        self.assertEqual(val.recommendation, "STRONG_ACQUIRE_WINDFALL")

    def test_evaluate_brio_tier1_unit_economics(self) -> None:
        brio = next(u for u in self.listings if u.unit_id == "MB-2026-001")
        val = evaluate_listing(brio)

        # Target Buy 121M + HPP 3.8M + Nego Buffer 2.5M + Mech Reserve 1M = 128.3M
        # Target Exit 136M - 128.3M = 7.7M net profit
        self.assertEqual(val.all_in_cost_at_target_idr, 128_300_000)
        self.assertEqual(val.net_profit_at_target_idr, 7_700_000)
        self.assertTrue(val.is_viable_at_target)

    def test_knapsack_capital_allocator_respects_1b_ceiling(self) -> None:
        alloc = optimize_capital_allocation(self.listings, capital_ceiling_idr=1_000_000_000)

        self.assertLessEqual(alloc.capital_deployed_idr, 1_000_000_000)
        self.assertEqual(alloc.capital_unallocated_idr, 1_000_000_000 - alloc.capital_deployed_idr)
        self.assertGreaterEqual(alloc.total_expected_net_profit_idr, 80_000_000)
        self.assertGreaterEqual(len(alloc.selected_units), 3)

    def test_unprofitable_listing_is_rejected(self) -> None:
        bad_unit = VehicleListing(
            unit_id="MB-2026-999",
            batch_date=date(2026, 10, 31),
            tier=TierCategory.TIER_1,
            unit_name="Overpriced Sedan",
            manufacture_year=2016,
            plate_location="Plat B",
            ask_price_idr=150_000_000,
            target_buy_idr=145_000_000,
            walk_away_idr=146_000_000,
            recon_hpp_idr=6_000_000,
            target_exit_idr=152_000_000,
            credit_eligible=False,
            leasing_partner="None",
            windfall_flag="PRICE: Cash",
            risk_notes="Overpriced",
            variation_plan="Full Paint",
            listing_url="https://example.com",
        )
        val = evaluate_listing(bad_unit)
        self.assertFalse(val.is_viable_at_target)
        self.assertEqual(val.recommendation, "PASS_INSUFFICIENT_MARGIN")


if __name__ == "__main__":
    unittest.main()
