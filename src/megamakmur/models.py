from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import List, Optional


class TierCategory(str, Enum):
    """Liquidity and capital velocity tiers for Jabodetabek used vehicle arbitrage."""
    TIER_1 = "Tier 1"  # High-liquidity LCGC / compact MPV (100M - 150M IDR)
    TIER_2 = "Tier 2"  # High-margin Diesel MPV/SUV & CUV (160M - 360M IDR)
    TIER_3 = "Tier 3"  # Executive / Luxury ATPM & European (400M - 650M IDR)


class WindfallFlag(str, Enum):
    """Pricing anomaly classifications sourced from scouting radar."""
    WINDFALL_A_DISTRESS = "WINDFALL-A:DISTRESS"
    WINDFALL_B_LEASING = "WINDFALL-B:LEASING_REFUND"
    WINDFALL_C_FACELIFT = "WINDFALL-C:FACELIFT"
    PRICE_CASH_ALIGNED = "PRICE:Cash_Aligned"
    PRICE_NEGO_BU = "PRICE:Nego_BU"
    PRICE_LOW_ODO = "PRICE:Low_Odo"


class JobStatus(str, Enum):
    PENDING = "Antri"
    IN_PROGRESS = "Dikerjakan"
    COMPLETED = "Selesai"
    CANCELLED = "Batal"


@dataclass(frozen=True)
class ReconditioningItem:
    """Single workshop variation or mechanical reconditioning line item."""
    category: str
    description: str
    material_cost_idr: int
    labor_cost_idr: int = 0

    @property
    def total_hpp_idr(self) -> int:
        return self.material_cost_idr + self.labor_cost_idr


@dataclass
class VehicleListing:
    """Raw and enriched scouting radar vehicle record."""
    unit_id: str
    batch_date: date
    tier: TierCategory
    unit_name: str
    manufacture_year: int
    plate_location: str
    ask_price_idr: int
    target_buy_idr: int
    walk_away_idr: int
    recon_hpp_idr: int
    target_exit_idr: int
    credit_eligible: bool
    leasing_partner: str
    windfall_flag: str
    risk_notes: str
    variation_plan: str
    listing_url: str
    inspection_status: str = "Belum Dicek"


@dataclass(frozen=True)
class ArbitrageValuation:
    """Quantitative valuation output for a candidate vehicle acquisition."""
    unit_id: str
    unit_name: str
    tier: TierCategory
    ask_price_idr: int
    target_buy_idr: int
    walk_away_idr: int
    recon_hpp_idr: int
    buyer_nego_buffer_idr: int
    mechanical_reserve_idr: int
    target_exit_idr: int
    all_in_cost_at_target_idr: int
    all_in_cost_at_walk_away_idr: int
    net_profit_at_target_idr: int
    net_profit_at_walk_away_idr: int
    net_profit_at_ask_idr: int
    gross_margin_pct: float
    roi_at_target_pct: float
    annualized_irr_pct: float
    composite_alpha_score: float
    is_viable_at_target: bool
    is_viable_at_walk_away: bool
    recommendation: str


@dataclass
class WorkshopJob:
    """Workshop POS service order (BK-YYYYMM-XXXX)."""
    job_code: str
    entry_date: date
    customer_name: str
    whatsapp_number: str
    vehicle_model: str
    license_plate: str
    service_category: str
    service_detail: str
    technician: str
    price_charged_idr: int
    material_cost_idr: int
    amount_paid_idr: int
    status: JobStatus
    payment_method: str
    completion_date: Optional[date] = None

    @property
    def outstanding_balance_idr(self) -> int:
        return max(0, self.price_charged_idr - self.amount_paid_idr)

    @property
    def gross_profit_idr(self) -> int:
        return self.price_charged_idr - self.material_cost_idr

    @property
    def gross_margin_pct(self) -> float:
        if self.price_charged_idr <= 0:
            return 0.0
        return round((self.gross_profit_idr / self.price_charged_idr) * 100.0, 2)


@dataclass
class BankMutation:
    """Bank BCA / QRIS settlement mutation row."""
    mutation_id: str
    tx_date: date
    channel: str  # QRIS, BI-FAST, TRANSFER_BCA, CASH
    amount_idr: int
    reference_Tag: str  # e.g., BK-202610-001 or MB-2026-005
    payer_name: str
    raw_description: str
