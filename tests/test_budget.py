import unittest

from narracrime_evar.evar import EVARConfig, EVARPipeline
from narracrime_evar.llm import MockLLM


class BudgetTests(unittest.TestCase):
    def test_equation_9_budget_assignment(self):
        pipeline = EVARPipeline(MockLLM(), EVARConfig(b_max=4, tau_fast=1.0, tau_step=1.0))
        self.assertEqual(pipeline._assign_budget(0.0), 0)
        self.assertEqual(pipeline._assign_budget(1.0), 0)
        self.assertEqual(pipeline._assign_budget(2.0), 1)
        self.assertEqual(pipeline._assign_budget(8.0), 4)


if __name__ == "__main__":
    unittest.main()
