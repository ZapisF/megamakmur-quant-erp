from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Optional

from megamakmur.arbitrage import evaluate_listing, optimize_capital_allocation
from megamakmur.reconciliation import reconcile_workshop_ledger
from megamakmur.storage import (
    load_bank_mutations_from_csv,
    load_listings_from_csv,
    load_workshop_jobs_from_csv,
    save_listings_to_db,
)
from megamakmur.webhooks import build_fonnte_dispatch_payload


def cmd_radar(args: argparse.Namespace) -> int:
    listings = load_listings_from_csv(Path(args.csv))
    valuations = [evaluate_listing(item) for item in listings]

    if args.json:
        print(json.dumps([v.__dict__ for v in valuations], indent=2, default=str))
        return 0

    print("=" * 108)
    print(f"{'UNIT ID':<12} {'VEHICLE UNIT':<36} {'TIER':<7} {'TARGET BUY':>14} {'NET PROFIT':>14} {'ROI %':>7} {'ALPHA':>7} {'DECISION'}")
    print("=" * 108)
    for v in sorted(valuations, key=lambda x: x.composite_alpha_score, reverse=True):
        print(
            f"{v.unit_id:<12} {v.unit_name[:35]:<36} {v.tier.value:<7} "
            f"Rp {v.target_buy_idr:>11,} Rp {v.net_profit_at_target_idr:>11,} "
            f"{v.roi_at_target_pct:>6.2f}% {v.composite_alpha_score:>7.2f} {v.recommendation}"
        )
    print("=" * 108)
    return 0


def cmd_allocate(args: argparse.Namespace) -> int:
    listings = load_listings_from_csv(Path(args.csv))
    result = optimize_capital_allocation(
        listings,
        capital_ceiling_idr=args.capital,
        max_tier3_share=args.max_tier3_share,
    )

    print("=" * 96)
    print(f"MEGA MAKMUR PORTFOLIO ALLOCATOR | CEILING: Rp {result.capital_ceiling_idr:,}")
    print("=" * 96)
    print(f"Capital Deployed     : Rp {result.capital_deployed_idr:,}")
    print(f"Capital Unallocated  : Rp {result.capital_unallocated_idr:,}")
    print(f"Expected Net Profit  : Rp {result.total_expected_net_profit_idr:,}")
    print(f"Blended Portfolio ROI: {result.portfolio_roi_pct:.2f}%")
    print(f"Tier Mix             : {result.tier_distribution}")
    print("-" * 96)
    for idx, u in enumerate(result.selected_units, start=1):
        print(
            f"{idx:2d}. [{u.unit_id}] {u.unit_name:<38} "
            f"All-In: Rp {u.all_in_cost_at_target_idr:>13,} | "
            f"Net: Rp {u.net_profit_at_target_idr:>11,} ({u.roi_at_target_pct:.2f}%)"
        )
    print("=" * 96)
    return 0


def cmd_reconcile(args: argparse.Namespace) -> int:
    jobs = load_workshop_jobs_from_csv(Path(args.jobs))
    mutations = load_bank_mutations_from_csv(Path(args.mutations))
    summary = reconcile_workshop_ledger(jobs, mutations)

    print("=" * 92)
    print("MEGA MAKMUR WORKSHOP POS & BANK/QRIS RECONCILIATION SUMMARY")
    print("=" * 92)
    print(f"Total Jobs Logged        : {summary.total_jobs_count}")
    print(f"Total Revenue Invoiced   : Rp {summary.total_invoiced_idr:,}")
    print(f"Total Material HPP       : Rp {summary.total_material_hpp_idr:,}")
    print(f"Gross Profit (Laba Kotor): Rp {summary.total_gross_profit_idr:,} ({summary.total_gross_margin_pct:.2f}%)")
    print(f"Mutations Matched        : Rp {summary.total_matched_idr:,}")
    print(f"Outstanding Receivables  : Rp {summary.outstanding_receivables_idr:,} (Unpaid: {summary.unpaid_job_codes})")
    print("-" * 92)
    for m in summary.matches:
        code_lbl = m.job_code or "UNASSIGNED"
        print(
            f"[{m.mutation_id}] -> {code_lbl:<15} | {m.match_type:<18} | "
            f"Rp {m.mutation_amount_idr:>10,} | {m.notes}"
        )
    print("=" * 92)
    return 0


def cmd_seed(args: argparse.Namespace) -> int:
    listings = load_listings_from_csv(Path(args.csv))
    count = save_listings_to_db(Path(args.db), listings)
    print(f"Seeded {count} vehicle listings into SQLite database at {args.db}")
    return 0


def cmd_alert_preview(args: argparse.Namespace) -> int:
    listings = load_listings_from_csv(Path(args.csv))
    target_unit = next((u for u in listings if u.unit_id == args.unit_id), listings[0])
    valuation = evaluate_listing(target_unit)
    payload = build_fonnte_dispatch_payload(args.phone, target_unit, valuation)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="megamakmur",
        description="Mega Makmur Quantitative Automotive Arbitrage & Workshop ERP CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_radar = sub.add_parser("radar", help="Evaluate scouting radar listings and rank by composite alpha")
    p_radar.add_argument("--csv", required=True, help="Path to scouting radar CSV")
    p_radar.add_argument("--json", action="store_true", help="Emit JSON output")
    p_radar.set_defaults(func=cmd_radar)

    p_alloc = sub.add_parser("allocate", help="Optimize vehicle acquisitions under capital ceiling")
    p_alloc.add_argument("--csv", required=True, help="Path to scouting radar CSV")
    p_alloc.add_argument("--capital", type=int, default=1_000_000_000, help="Working capital ceiling in IDR")
    p_alloc.add_argument("--max-tier3-share", type=float, default=0.60, help="Max Tier 3 capital share (0.0-1.0)")
    p_alloc.set_defaults(func=cmd_allocate)

    p_recon = sub.add_parser("reconcile", help="Reconcile workshop POS jobs against BCA/QRIS mutations")
    p_recon.add_argument("--jobs", required=True, help="Path to workshop jobs CSV")
    p_recon.add_argument("--mutations", required=True, help="Path to bank/QRIS mutations CSV")
    p_recon.set_defaults(func=cmd_reconcile)

    p_seed = sub.add_parser("seed", help="Seed scouting radar CSV into SQLite database")
    p_seed.add_argument("--csv", required=True, help="Path to scouting radar CSV")
    p_seed.add_argument("--db", default="data/megamakmur.db", help="Path to SQLite DB")
    p_seed.set_defaults(func=cmd_seed)

    p_alert = sub.add_parser("alert-preview", help="Preview Fonnte WhatsApp payload for a unit")
    p_alert.add_argument("--csv", required=True, help="Path to scouting radar CSV")
    p_alert.add_argument("--unit-id", default="MB-2026-005", help="Unit ID to preview")
    p_alert.add_argument("--phone", default="081291302199", help="Recipient WhatsApp number")
    p_alert.set_defaults(func=cmd_alert_preview)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
