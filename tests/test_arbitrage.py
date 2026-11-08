from datetime import date
from pathlib import Path

from megamakmur.arbitrage import evaluate_listing, optimize_capital_allocation
from megamakmur.models import TierCategory, VehicleListing
from megamakmur.storage import load_listings_from_csv


DATA_CSV = Path(__file__).resolve().parent.parent / "data" / "scouting_radar_2026_10_31.csv"


def test_evaluate_innova_reborn_windfall():
    listings = load_listings_from_csv(DATA_CSV)
    innova = next(u for u in listings if u.unit_id == "MB-2026-005")
    val = evaluate_listing(innova)

    # Target Buy 272M + HPP 8.5M + Nego Buffer 5M + Mech Reserve 2M = 287.5M
    # Target Exit 312M - 287.5M = 24.5M net profit
    assert val.all_in_cost_at_target_idr == 287_500_000
    assert val.net_profit_at_target_idr == 24_500_000
    assert val.is_viable_at_target is True
    assert val.recommendation == "STRONG_ACQUIRE_WINDFALL"


def test_evaluate_brio_tier1_unit_economics():
    listings = load_listings_from_csv(DATA_CSV)
    brio = next(u for u in listings if u.unit_id == "MB-2026-001")
    val = evaluate_listing(brio)

    # Target Buy 121M + HPP 3.8M + Nego Buffer 2.5M + Mech Reserve 1M = 128.3M
    # Target Exit 136M - 128.3M = 7.7M net profit
    assert val.all_in_cost_at_target_idr == 128_300_000
    assert val.net_profit_at_target_idr == 7_700_000
    assert val.is_viable_at_target is True


def test_knapsack_capital_allocator_respects_1b_ceiling():
    listings = load_listings_from_csv(DATA_CSV)
    alloc = optimize_capital_allocation(listings, capital_ceiling_idr=1_000_000_000)

    assert alloc.capital_deployed_idr <= 1_000_000_000
    assert alloc.capital_unallocated_idr == 1_000_000_000 - alloc.capital_deployed_idr
    assert alloc.total_expected_net_profit_idr >= 80_000_000
    assert len(alloc.selected_units) >= 3


def test_unprofitable_listing_is_rejected():
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
    assert val.is_viable_at_target is False
    assert val.recommendation == "PASS_INSUFFICIENT_MARGIN"
