import unittest
from pathlib import Path

from narracrime_evar.data import load_dataset


class DatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]

    def test_load_cases_and_candidate_ids(self):
        cases = load_dataset(self.root, split="Easy", limit=2)
        self.assertEqual(len(cases), 2)
        self.assertTrue(cases[0].narrative)
        self.assertTrue(cases[0].candidates)
        self.assertEqual(cases[0].candidate_ids[0], "C001")
        self.assertIn(cases[0].gold_culprit_id, cases[0].candidate_ids)

    def test_full_release_has_100_cases_per_split(self):
        for split in ["Easy", "Medium", "Complex"]:
            self.assertEqual(len(load_dataset(self.root, split=split)), 100)


if __name__ == "__main__":
    unittest.main()
