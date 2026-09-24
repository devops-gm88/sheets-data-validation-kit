import unittest

from validation_kit import Assertion, Reconcile
from validation_kit.reconcile import closing_balance_check, rollforward_check


class TestReconcile(unittest.TestCase):
    def setUp(self):
        self.suite = Reconcile([
            Assertion("assets = liabilities + equity",
                      lambda r: r["total_assets"],
                      lambda r: r["total_liabilities"] + r["total_equity"],
                      tolerance=0.01),
        ])

    def test_balanced_record_passes(self):
        record = {"total_assets": 1000.0, "total_liabilities": 400.0, "total_equity": 600.0}
        self.assertTrue(self.suite.all_pass(record))

    def test_unbalanced_record_fails(self):
        record = {"total_assets": 1000.0, "total_liabilities": 400.0, "total_equity": 599.0}
        self.assertFalse(self.suite.all_pass(record))
        failure = self.suite.failures(record)[0]
        self.assertEqual(failure.left, 1000.0)
        self.assertAlmostEqual(failure.difference, 1.0)

    def test_tolerance_is_respected(self):
        record = {"total_assets": 1000.005, "total_liabilities": 400.0, "total_equity": 600.0}
        self.assertTrue(self.suite.all_pass(record))

    def test_missing_field_is_a_failure_not_an_exception(self):
        outcomes = self.suite.check({"total_assets": 1000.0})
        self.assertFalse(outcomes[0].passed)
        self.assertIn("cannot evaluate", outcomes[0].note)

    def test_outcome_string_prints_both_sides(self):
        record = {"total_assets": 1000.0, "total_liabilities": 400.0, "total_equity": 500.0}
        text = str(self.suite.check(record)[0])
        self.assertIn("FAIL", text)
        self.assertIn("1,000.00", text)

    def test_closing_balance_helper(self):
        suite = Reconcile([closing_balance_check("opening", "inflow", "outflow", "closing")])
        self.assertTrue(suite.all_pass(
            {"opening": 100, "inflow": 50, "outflow": 30, "closing": 120}))
        self.assertFalse(suite.all_pass(
            {"opening": 100, "inflow": 50, "outflow": 30, "closing": 119}))

    def test_rollforward_helper(self):
        suite = Reconcile([rollforward_check("opening", "additions", "reductions", "closing")])
        self.assertTrue(suite.all_pass(
            {"opening": 10, "additions": 5, "reductions": 2, "closing": 13}))


if __name__ == "__main__":
    unittest.main()
