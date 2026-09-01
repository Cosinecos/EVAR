import json
import unittest
from pathlib import Path

from narracrime_evar.data import load_dataset
from narracrime_evar.evar import EVARPipeline
from narracrime_evar.llm import MockLLM


class MockPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.case = load_dataset(root, split="Complex", limit=1)[0]
        cls.prediction = EVARPipeline(MockLLM()).run_case(cls.case)

    def test_full_final_paper_path_runs(self):
        operators = [record["operator"] for record in self.prediction["operator_trace"]]
        self.assertIn("ATOM", operators)
        self.assertIn("TAG", operators)
        self.assertIn("GAP", operators)
        self.assertIn("HYP", operators)
        self.assertIn("CHAL", operators)
        self.assertIn("VER", operators)
        self.assertIn("SUF", operators)
        self.assertEqual(operators[-1], "ANS")
        self.assertNotIn("QUERY", operators)

    def test_initial_gap_is_reused_at_iteration_zero(self):
        self.assertGreaterEqual(self.prediction["executed_iterations"], 1)
        self.assertEqual(self.prediction["iterations"][0]["gap_source"], "reused_Z0")
        if self.prediction["executed_iterations"] == 1:
            self.assertEqual(
                sum(record["operator"] == "GAP" for record in self.prediction["operator_trace"]),
                1,
            )

    def test_answer_input_excludes_non_supporting_state(self):
        answer_input = [
            record["input"] for record in self.prediction["operator_trace"] if record["operator"] == "ANS"
        ][-1]
        self.assertEqual(
            set(answer_input),
            {"case_id", "goal", "evidence_store", "admitted_hypotheses", "candidates"},
        )
        self.assertNotIn("validation_challenge_history", answer_input)
        self.assertNotIn("quarantine_history", answer_input)
        self.assertNotIn("discard_history", answer_input)

    def test_probability_schema_and_no_gold_leakage(self):
        probabilities = self.prediction["answer"]["verdict_probabilities"]
        self.assertEqual(set(probabilities), set(self.case.candidate_ids))
        self.assertAlmostEqual(sum(probabilities.values()), 1.0, places=12)
        self.assertTrue(all(value >= 0 for value in probabilities.values()))
        serialized_trace = json.dumps(self.prediction["operator_trace"], ensure_ascii=False)
        self.assertNotIn(self.case.verdict, serialized_trace)

    def test_locked_store_fingerprint_is_stable(self):
        self.assertTrue(self.prediction["evidence_store"]["locked"])
        self.assertEqual(
            self.prediction["evidence_store"],
            self.prediction["terminal_state"]["evidence_store"],
        )


if __name__ == "__main__":
    unittest.main()
