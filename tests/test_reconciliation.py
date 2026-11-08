from pathlib import Path

from megamakmur.reconciliation import extract_reference_code, reconcile_workshop_ledger
from megamakmur.storage import load_bank_mutations_from_csv, load_workshop_jobs_from_csv


JOBS_CSV = Path(__file__).resolve().parent.parent / "data" / "workshop_jobs_2026_10.csv"
MUTATIONS_CSV = Path(__file__).resolve().parent.parent / "data" / "bank_qris_mutations_2026_10.csv"


def test_extract_reference_code():
    assert extract_reference_code("QRIS Settlement BK-202610-001 B 2612 TBO") == "BK-202610-001"
    assert extract_reference_code("Pelunasan unit MB-2026-005 Innova") == "MB-2026-005"
    assert extract_reference_code("Transfer tanpa kode referensi") is None


def test_reconcile_october_workshop_ledger():
    jobs = load_workshop_jobs_from_csv(JOBS_CSV)
    mutations = load_bank_mutations_from_csv(MUTATIONS_CSV)
    summary = reconcile_workshop_ledger(jobs, mutations)

    assert summary.total_jobs_count == 4
    assert summary.total_invoiced_idr == 8_150_000
    assert summary.total_material_hpp_idr == 4_475_000
    assert summary.total_gross_profit_idr == 3_675_000
    assert summary.outstanding_receivables_idr == 2_400_000
    assert summary.unpaid_job_codes == ["BK-202610-004"]
    assert summary.total_unmatched_mutation_idr == 0

    # Verify fuzzy match worked on Hendra's Hyundai i20 AC repair (MUT-202610-903)
    m_903 = next(m for m in summary.matches if m.mutation_id == "MUT-202610-903")
    assert m_903.job_code == "BK-202610-003"
    assert m_903.match_type == "FUZZY_AMOUNT_DATE"
