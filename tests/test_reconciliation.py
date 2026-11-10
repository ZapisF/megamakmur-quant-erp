import unittest
from pathlib import Path

from megamakmur.reconciliation import extract_reference_code, reconcile_workshop_ledger
from megamakmur.storage import load_bank_mutations_from_csv, load_workshop_jobs_from_csv


JOBS_CSV = Path(__file__).resolve().parent.parent / "data" / "workshop_jobs_2026_10.csv"
MUTATIONS_CSV = Path(__file__).resolve().parent.parent / "data" / "bank_qris_mutations_2026_10.csv"


class TestReconciliationEngine(unittest.TestCase):
    def test_extract_reference_code(self) -> None:
        self.assertEqual(extract_reference_code("QRIS Settlement BK-202610-001 B 2612 TBO"), "BK-202610-001")
        self.assertEqual(extract_reference_code("Pelunasan unit MB-2026-005 Innova"), "MB-2026-005")
        self.assertIsNone(extract_reference_code("Transfer tanpa kode referensi"))

    def test_reconcile_october_workshop_ledger(self) -> None:
        jobs = load_workshop_jobs_from_csv(JOBS_CSV)
        mutations = load_bank_mutations_from_csv(MUTATIONS_CSV)
        summary = reconcile_workshop_ledger(jobs, mutations)

        self.assertEqual(summary.total_jobs_count, 4)
        self.assertEqual(summary.total_invoiced_idr, 8_150_000)
        self.assertEqual(summary.total_material_hpp_idr, 4_475_000)
        self.assertEqual(summary.total_gross_profit_idr, 3_675_000)
        self.assertEqual(summary.outstanding_receivables_idr, 2_400_000)
        self.assertEqual(summary.unpaid_job_codes, ["BK-202610-004"])
        self.assertEqual(summary.total_unmatched_mutation_idr, 0)

        m_903 = next(m for m in summary.matches if m.mutation_id == "MUT-202610-903")
        self.assertEqual(m_903.job_code, "BK-202610-003")
        self.assertEqual(m_903.match_type, "FUZZY_AMOUNT_DATE")


if __name__ == "__main__":
    unittest.main()
