import unittest
from pathlib import Path

from narracrime_evar.contracts import ContractError, validate_operator_output
from narracrime_evar.data import load_dataset
from narracrime_evar.metrics import LexicalMatcher, greedy_one_to_one_matches, role_aware_verdict_score


class MetricTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.case = load_dataset(root, split="Easy", limit=1)[0]

    def test_rvs_uses_probability_mass(self):
        probabilities = {candidate_id: 0.0 for candidate_id in self.case.candidate_ids}
        probabilities[self.case.gold_culprit_id] = 1.0
        self.assertEqual(role_aware_verdict_score(self.case, probabilities), 1.0)

    def test_greedy_match_is_one_to_one_on_both_sides(self):
        matcher = LexicalMatcher(threshold=0.2)
        matched = greedy_one_to_one_matches(
            ["hidden brass key", "hidden brass key"],
            ["brass key was hidden", "steam opened envelope"],
            matcher,
        )
        self.assertEqual(matched, 1)

    def test_answer_contract_rejects_incomplete_distribution(self):
        bad_answer = {
            "textual_answer": "Insufficient output.",
            "predicted_culprit_id": self.case.candidate_ids[0],
            "verdict_probabilities": {self.case.candidate_ids[0]: 1.0},
            "intent_propositions": [],
            "action_schema_propositions": [],
            "evidence_propositions": [],
            "claims": [],
            "insufficient_evidence": True,
        }
        with self.assertRaises(ContractError):
            validate_operator_output(
                "ANS",
                bad_answer,
                {
                    "candidate_ids": self.case.candidate_ids,
                    "unit_ids": [],
                    "hypothesis_ids": [],
                    "probability_tolerance": 1e-6,
                },
            )


if __name__ == "__main__":
    unittest.main()
