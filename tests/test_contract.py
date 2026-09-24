import unittest

from validation_kit import Field, RowContract, Min, Range, Pattern, OneOf, NotBlank


class TestRowContract(unittest.TestCase):
    def setUp(self):
        self.contract = RowContract([
            Field("account_id", required=True),
            Field("amount", rules=[Min(0)], coerce=float),
            Field("period", rules=[Pattern(r"^\d{4}-Q[1-4]$")]),
        ])

    def test_clean_row_is_accepted(self):
        result = self.contract.validate_rows(
            [{"account_id": "A1", "amount": "100.50", "period": "2026-Q1"}])
        self.assertEqual(len(result.accepted), 1)
        self.assertEqual(result.accepted[0]["amount"], 100.5)
        self.assertEqual(result.quarantined, [])

    def test_blank_required_field_is_quarantined_not_dropped(self):
        result = self.contract.validate_rows([{"account_id": "  ", "amount": "10"}])
        self.assertEqual(result.accepted, [])
        self.assertEqual(len(result.quarantined), 1)
        self.assertIn("required but blank", result.quarantined[0][1][0])

    def test_out_of_range_amount_is_quarantined(self):
        result = self.contract.validate_rows(
            [{"account_id": "A2", "amount": "-5", "period": "2026-Q2"}])
        self.assertEqual(len(result.quarantined), 1)
        self.assertIn("below minimum", result.quarantined[0][1][0])

    def test_malformed_period_is_quarantined(self):
        result = self.contract.validate_rows(
            [{"account_id": "A3", "amount": "5", "period": "Q1-2026"}])
        self.assertEqual(len(result.quarantined), 1)

    def test_nothing_is_ever_silently_lost(self):
        rows = [
            {"account_id": "A1", "amount": "1", "period": "2026-Q1"},
            {"account_id": "", "amount": "1", "period": "2026-Q1"},
            {"account_id": "A3", "amount": "x", "period": "2026-Q1"},
        ]
        result = self.contract.validate_rows(rows)
        self.assertEqual(result.total, len(rows))

    def test_flag_mode_keeps_the_row(self):
        lenient = RowContract([Field("note", rules=[NotBlank()], on_fail="flag")])
        result = lenient.validate_rows([{"note": ""}, {"note": "ok"}])
        self.assertEqual(len(result.accepted), 2)

    def test_error_counts_are_reported_per_field(self):
        result = self.contract.validate_rows([
            {"account_id": "", "amount": "1", "period": "2026-Q1"},
            {"account_id": "", "amount": "1", "period": "2026-Q1"},
        ])
        self.assertEqual(result.field_error_counts["account_id"], 2)

    def test_summary_reports_pass_rate(self):
        result = self.contract.validate_rows([
            {"account_id": "A1", "amount": "1", "period": "2026-Q1"},
            {"account_id": "", "amount": "1", "period": "2026-Q1"},
        ])
        self.assertIn("50.0%", result.summary())


class TestRules(unittest.TestCase):
    def test_one_of(self):
        contract = RowContract([Field("stage", rules=[OneOf(["open", "closed"])])])
        self.assertEqual(len(contract.validate_rows([{"stage": "open"}]).accepted), 1)
        self.assertEqual(len(contract.validate_rows([{"stage": "pending"}]).quarantined), 1)

    def test_range_catches_outliers(self):
        contract = RowContract([Field("rate", rules=[Range(0.5, 1.5)], coerce=float)])
        self.assertEqual(len(contract.validate_rows([{"rate": "1.2"}]).accepted), 1)
        self.assertEqual(len(contract.validate_rows([{"rate": "12"}]).quarantined), 1)


if __name__ == "__main__":
    unittest.main()
