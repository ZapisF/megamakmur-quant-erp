from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from megamakmur.models import ArbitrageValuation, TierCategory, VehicleListing


# Tier-specific friction parameters calibrated on Jabodetabek secondary market
TIER_PARAMETERS: Dict[TierCategory, Dict[str, float]] = {
    TierCategory.TIER_1: {
        "buyer_nego_buffer_idr": 2_500_000,
        "mechanical_reserve_idr": 1_000_000,
        "expected_turn_days": 21.0,
        "min_acceptable_roi_pct": 4.2,
        "min_net_profit_idr": 5_000_000,
    },
    TierCategory.TIER_2: {
        "buyer_nego_buffer_idr": 5_000_000,
        "mechanical_reserve_idr": 2_000_000,
        "expected_turn_days": 32.0,
        "min_acceptable_roi_pct": 5.5,
        "min_net_profit_idr": 12_000_000,
    },
    TierCategory.TIER_3: {
        "buyer_nego_buffer_idr": 6_500_000,
        "mechanical_reserve_idr": 3_000_000,
        "expected_turn_days": 45.0,
        "min_acceptable_roi_pct": 6.0,
        "min_net_profit_idr": 30_000_000,
    },
}


def compute_friction_reserves(listing: VehicleListing) -> Tuple[int, int]:
    """
    Returns (buyer_negotiation_buffer_idr, mechanical_reserve_idr) for a listing.
    Allows dynamic scaling based on target exit price and vehicle tier.
    """
    params = TIER_PARAMETERS[listing.tier]
    base_nego = int(params["buyer_nego_buffer_idr"])
    base_mech = int(params["mechanical_reserve_idr"])

    # Adjust slightly for mid-tier compact SUVs (under 200M IDR in Tier 2)
    if listing.tier == TierCategory.TIER_2 and listing.target_exit_idr < 210_000_000:
        base_nego = 4_000_000
        base_mech = 1_500_000

    return base_nego, base_mech


def evaluate_listing(listing: VehicleListing) -> ArbitrageValuation:
    """
    Performs full unit-economics valuation on a candidate vehicle listing,
    incorporating workshop HPP reconditioning, buyer negotiation buffer,
    and mechanical contingency reserves.
    """
    nego_buffer, mech_reserve = compute_friction_reserves(listing)
    params = TIER_PARAMETERS[listing.tier]
    turn_days = params["expected_turn_days"]

    friction_total = listing.recon_hpp_idr + nego_buffer + mech_reserve

    all_in_target = listing.target_buy_idr + friction_total
    all_in_walk_away = listing.walk_away_idr + friction_total
    all_in_ask = listing.ask_price_idr + friction_total

    net_target = listing.target_exit_idr - all_in_target
    net_walk_away = listing.target_exit_idr - all_in_walk_away
    net_ask = listing.target_exit_idr - all_in_ask

    roi_target = (net_target / all_in_target) * 100.0 if all_in_target > 0 else 0.0
    gross_margin_pct = (
        ((listing.target_exit_idr - listing.target_buy_idr - listing.recon_hpp_idr) / listing.target_exit_idr) * 100.0
        if listing.target_exit_idr > 0
        else 0.0
    )

    # Annualized simple IRR based on expected inventory turn days
    turns_per_year = 365.0 / turn_days
    annualized_irr = roi_target * turns_per_year

    # Windfall & financing multiplier for composite alpha ranking
    windfall_bonus = 1.15 if "WINDFALL" in listing.windfall_flag.upper() else 1.0
    credit_bonus = 1.08 if listing.credit_eligible else 0.92
    composite_alpha = round(roi_target * (turns_per_year / 10.0) * windfall_bonus * credit_bonus, 2)

    is_viable_target = (
        roi_target >= params["min_acceptable_roi_pct"]
        and net_target >= params["min_net_profit_idr"]
    )
    is_viable_walk_away = net_walk_away >= int(params["min_net_profit_idr"] * 0.75)

    if is_viable_target and "WINDFALL" in listing.windfall_flag.upper():
        rec = "STRONG_ACQUIRE_WINDFALL"
    elif is_viable_target:
        rec = "ACQUIRE_AT_TARGET"
    elif is_viable_walk_away:
        rec = "NEGO_HARD_BELOW_TARGET"
    else:
        rec = "PASS_INSUFFICIENT_MARGIN"

    return ArbitrageValuation(
        unit_id=listing.unit_id,
        unit_name=f"{listing.manufacture_year} {listing.unit_name}",
        tier=listing.tier,
        ask_price_idr=listing.ask_price_idr,
        target_buy_idr=listing.target_buy_idr,
        walk_away_idr=listing.walk_away_idr,
        recon_hpp_idr=listing.recon_hpp_idr,
        buyer_nego_buffer_idr=nego_buffer,
        mechanical_reserve_idr=mech_reserve,
        target_exit_idr=listing.target_exit_idr,
        all_in_cost_at_target_idr=all_in_target,
        all_in_cost_at_walk_away_idr=all_in_walk_away,
        net_profit_at_target_idr=net_target,
        net_profit_at_walk_away_idr=net_walk_away,
        net_profit_at_ask_idr=net_ask,
        gross_margin_pct=round(gross_margin_pct, 2),
        roi_at_target_pct=round(roi_target, 2),
        annualized_irr_pct=round(annualized_irr, 2),
        composite_alpha_score=composite_alpha,
        is_viable_at_target=is_viable_target,
        is_viable_at_walk_away=is_viable_walk_away,
        recommendation=rec,
    )


@dataclass(frozen=True)
class PortfolioAllocationResult:
    """Optimal subset of vehicles selected under a fixed working capital ceiling."""
    capital_ceiling_idr: int
    capital_deployed_idr: int
    capital_unallocated_idr: int
    total_expected_net_profit_idr: int
    portfolio_roi_pct: float
    selected_units: List[ArbitrageValuation]
    tier_distribution: Dict[str, int]


def optimize_capital_allocation(
    listings: List[VehicleListing],
    capital_ceiling_idr: int = 1_000_000_000,
    max_tier3_share: float = 0.60,
) -> PortfolioAllocationResult:
    """
    Solves the 0/1 Knapsack capital allocation problem across candidate vehicles
    to maximize total expected net profit under a working capital ceiling
    (default Rp 1,000,000,000) while enforcing a concentration cap on Tier 3 luxury units.
    """
    valuations = [evaluate_listing(u) for u in listings]
    viable = [v for v in valuations if v.is_viable_at_target and v.all_in_cost_at_target_idr <= capital_ceiling_idr]

    n = len(viable)
    best_profit = -1
    best_subset: List[ArbitrageValuation] = []

    # Exact branch-and-bound / subset evaluation for realistic scouting batch sizes (<= 25)
    for mask in range(1 << n):
        cost = 0
        tier3_cost = 0
        profit = 0
        subset: List[ArbitrageValuation] = []
        for i in range(n):
            if mask & (1 << i):
                v = viable[i]
                cost += v.all_in_cost_at_target_idr
                if cost > capital_ceiling_idr:
                    break
                if v.tier == TierCategory.TIER_3:
                    tier3_cost += v.all_in_cost_at_target_idr
                profit += v.net_profit_at_target_idr
                subset.append(v)
        else:
            if cost > 0 and (tier3_cost / capital_ceiling_idr) > max_tier3_share:
                continue
            if profit > best_profit:
                best_profit = profit
                best_subset = subset

    deployed = sum(v.all_in_cost_at_target_idr for v in best_subset)
    unallocated = capital_ceiling_idr - deployed
    portfolio_roi = (best_profit / deployed) * 100.0 if deployed > 0 else 0.0

    tier_dist: Dict[str, int] = {t.value: 0 for t in TierCategory}
    for v in best_subset:
        tier_dist[v.tier.value] += 1

    best_subset.sort(key=lambda x: x.composite_alpha_score, reverse=True)

    return PortfolioAllocationResult(
        capital_ceiling_idr=capital_ceiling_idr,
        capital_deployed_idr=deployed,
        capital_unallocated_idr=unallocated,
        total_expected_net_profit_idr=max(0, best_profit),
        portfolio_roi_pct=round(portfolio_roi, 2),
        selected_units=best_subset,
        tier_distribution=tier_dist,
    )
