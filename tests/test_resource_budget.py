import unittest
from resource_budget import budget_for, constrained_budget
from hardware_profiles import PROFILES


class ResourceBudgetTests(unittest.TestCase):
    def test_light_is_conservative(self):
        budget = budget_for(PROFILES["leve"])
        self.assertFalse(budget.allow_optional_3d)
        self.assertEqual(budget.background_workers, 1)

    def test_advanced_can_opt_into_future_3d(self):
        budget = budget_for("avancado")
        self.assertTrue(budget.allow_optional_3d)
        self.assertEqual(budget.max_context_tokens, 8192)

    def test_battery_saver_reduces_load(self):
        budget = constrained_budget("avancado", battery_saver=True)
        self.assertEqual(budget.avatar_fps, 12)
        self.assertFalse(budget.allow_optional_3d)
        self.assertEqual(budget.background_workers, 1)

    def test_reduced_motion_disables_advanced_effects(self):
        budget = constrained_budget("avancado", reduced_motion=True)
        self.assertFalse(budget.allow_optional_3d)
        self.assertFalse(budget.allow_advanced_effects)

    def test_invalid_profile_is_rejected(self):
        with self.assertRaises(ValueError):
            budget_for("ultra")
