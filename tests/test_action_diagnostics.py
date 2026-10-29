import unittest
from action_diagnostics import diagnose_failure


class FailureAdviceTests(unittest.TestCase):
    def test_missing_file_is_actionable(self):
        result = diagnose_failure(FileNotFoundError("C:/Users/secret.txt"))
        self.assertEqual(result.category, "not_found")
        self.assertTrue(result.self_repair_possible)
        self.assertNotIn("secret.txt", result.message())

    def test_permission_error(self):
        self.assertEqual(diagnose_failure(PermissionError("denied")).category, "permission")

    def test_timeout(self):
        self.assertEqual(diagnose_failure(TimeoutError()).category, "unavailable")

    def test_missing_capability_requires_update(self):
        result = diagnose_failure(None, capability_available=False)
        self.assertTrue(result.update_may_be_needed)
        self.assertFalse(result.self_repair_possible)

    def test_unknown_does_not_claim_self_update(self):
        result = diagnose_failure(RuntimeError("token=supersecret"))
        self.assertTrue(result.update_may_be_needed)
        self.assertNotIn("supersecret", result.message())
