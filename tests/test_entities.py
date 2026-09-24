import unittest

from validation_kit.entities import count_distinct, resolve


class TestResolve(unittest.TestCase):
    def test_distinct_keys_counted_once(self):
        outcome = resolve([{"child_id": "C1"}, {"child_id": "C2"}], key="child_id")
        self.assertEqual(outcome.unique_count, 2)
        self.assertEqual(outcome.inflation, 0)

    def test_repeat_key_does_not_inflate_the_count(self):
        outcome = resolve([{"child_id": "C1"}, {"child_id": "C1"}, {"child_id": "C2"}],
                          key="child_id")
        self.assertEqual(outcome.unique_count, 2)
        self.assertEqual(outcome.inflation, 1)

    def test_blank_keys_are_held_back_not_counted(self):
        outcome = resolve([{"child_id": ""}, {"child_id": None}, {"child_id": "C1"}],
                          key="child_id")
        self.assertEqual(outcome.unique_count, 1)
        self.assertEqual(len(outcome.blank_keys), 2)

    def test_case_and_whitespace_are_normalised(self):
        outcome = resolve([{"child_id": " c1 "}, {"child_id": "C1"}], key="child_id")
        self.assertEqual(outcome.unique_count, 1)

    def test_suspects_are_queued_never_merged(self):
        outcome = resolve([
            {"child_id": "C1", "full_name": "Jane Doe"},
            {"child_id": "C2", "full_name": "Jane Doe"},
        ], key="child_id", signature=["full_name"])
        self.assertEqual(outcome.unique_count, 2, "suspects must not be merged")
        self.assertEqual(len(outcome.duplicate_candidates), 1)
        self.assertEqual(outcome.duplicate_candidates[0].keys(), ["c1", "c2"])

    def test_inflation_reports_the_phantom_entities(self):
        outcome = resolve([{"child_id": "C1"}] * 5, key="child_id")
        self.assertEqual(outcome.unique_count, 1)
        self.assertEqual(outcome.inflation, 4)

    def test_count_distinct_helper(self):
        self.assertEqual(count_distinct([{"k": "a"}, {"k": "a"}, {"k": ""}], "k"), 1)


if __name__ == "__main__":
    unittest.main()
