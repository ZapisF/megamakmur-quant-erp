from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from megamakmur.models import BankMutation, WorkshopJob


JOB_CODE_PATTERN = re.compile(r"\b(BK-\d{4,6}-\d{3}|BK-\d{3,6})\b", re.IGNORECASE)
CAR_CODE_PATTERN = re.compile(r"\b(MB-\d{4}-\d{3}|MB-\d{3,6})\b", re.IGNORECASE)


@dataclass(frozen=True)
class ReconciliationMatch:
    mutation_id: str
    job_code: Optional[str]
    match_type: str  # EXACT_CODE, FUZZY_AMOUNT_NAME, UNMATCHED_MUTATION
    mutation_amount_idr: int
    expected_amount_idr: int
    variance_idr: int
    notes: str


@dataclass(frozen=True)
class MonthlyReconciliationSummary:
    total_jobs_count: int
    total_invoiced_idr: int
    total_material_hpp_idr: int
    total_gross_profit_idr: int
    total_gross_margin_pct: float
    total_mutations_received_idr: int
    total_matched_idr: int
    total_unmatched_mutation_idr: int
    outstanding_receivables_idr: int
    matches: List[ReconciliationMatch]
    unpaid_job_codes: List[str]


def extract_reference_code(text: str) -> Optional[str]:
    """Extracts standardized BK-... or MB-... reference code from mutation text."""
    if not text:
        return None
    job_match = JOB_CODE_PATTERN.search(text)
    if job_match:
        return job_match.group(1).upper()
    car_match = CAR_CODE_PATTERN.search(text)
    if car_match:
        return car_match.group(1).upper()
    return None


def reconcile_workshop_ledger(
    jobs: List[WorkshopJob],
    mutations: List[BankMutation],
) -> MonthlyReconciliationSummary:
    """
    Cross-references Workshop POS jobs (sheet Pekerjaan) against BCA/QRIS
    settlement mutations (sheet BankQRIS) using deterministic code matching
    followed by fuzzy customer/amount heuristics.
    """
    jobs_by_code: Dict[str, WorkshopJob] = {j.job_code.upper(): j for j in jobs}
    matched_job_codes = set()
    matches: List[ReconciliationMatch] = []

    total_matched_idr = 0
    total_unmatched_idr = 0

    for mut in mutations:
        code = extract_reference_code(mut.reference_Tag) or extract_reference_code(mut.raw_description)
        if code and code in jobs_by_code:
            job = jobs_by_code[code]
            matched_job_codes.add(code)
            variance = mut.amount_idr - job.price_charged_idr
            total_matched_idr += mut.amount_idr
            matches.append(
                ReconciliationMatch(
                    mutation_id=mut.mutation_id,
                    job_code=job.job_code,
                    match_type="EXACT_CODE",
                    mutation_amount_idr=mut.amount_idr,
                    expected_amount_idr=job.price_charged_idr,
                    variance_idr=variance,
                    notes="Matched via standardized BK reference tag" if variance == 0 else f"Partial/DP variance: {variance:+,} IDR",
                )
            )
            continue

        # Fallback: fuzzy match by exact amount + same/subsequent day + payer name substring
        fuzzy_candidate: Optional[WorkshopJob] = None
        for job in jobs:
            if job.job_code.upper() in matched_job_codes:
                continue
            date_diff = abs((mut.tx_date - job.entry_date).days)
            name_overlap = (
                job.customer_name
                and job.customer_name != "-"
                and job.customer_name.lower() in mut.payer_name.lower()
            )
            if mut.amount_idr == job.price_charged_idr and (date_diff <= 2 or name_overlap):
                fuzzy_candidate = job
                break

        if fuzzy_candidate:
            matched_job_codes.add(fuzzy_candidate.job_code.upper())
            total_matched_idr += mut.amount_idr
            matches.append(
                ReconciliationMatch(
                    mutation_id=mut.mutation_id,
                    job_code=fuzzy_candidate.job_code,
                    match_type="FUZZY_AMOUNT_DATE",
                    mutation_amount_idr=mut.amount_idr,
                    expected_amount_idr=fuzzy_candidate.price_charged_idr,
                    variance_idr=0,
                    notes=f"Fuzzy matched to {fuzzy_candidate.vehicle_model} ({fuzzy_candidate.license_plate})",
                )
            )
        else:
            total_unmatched_idr += mut.amount_idr
            matches.append(
                ReconciliationMatch(
                    mutation_id=mut.mutation_id,
                    job_code=None,
                    match_type="UNMATCHED_MUTATION",
                    mutation_amount_idr=mut.amount_idr,
                    expected_amount_idr=0,
                    variance_idr=mut.amount_idr,
                    notes=f"Untagged mutation from {mut.payer_name} ({mut.channel})",
                )
            )

    total_invoiced = sum(j.price_charged_idr for j in jobs)
    total_hpp = sum(j.material_cost_idr for j in jobs)
    total_gross_profit = total_invoiced - total_hpp
    gross_margin_pct = round((total_gross_profit / total_invoiced) * 100.0, 2) if total_invoiced > 0 else 0.0
    outstanding_receivables = sum(j.outstanding_balance_idr for j in jobs)
    unpaid_codes = [j.job_code for j in jobs if j.outstanding_balance_idr > 0]

    return MonthlyReconciliationSummary(
        total_jobs_count=len(jobs),
        total_invoiced_idr=total_invoiced,
        total_material_hpp_idr=total_hpp,
        total_gross_profit_idr=total_gross_profit,
        total_gross_margin_pct=gross_margin_pct,
        total_mutations_received_idr=sum(m.amount_idr for m in mutations),
        total_matched_idr=total_matched_idr,
        total_unmatched_mutation_idr=total_unmatched_idr,
        outstanding_receivables_idr=outstanding_receivables,
        matches=matches,
        unpaid_job_codes=unpaid_codes,
    )
