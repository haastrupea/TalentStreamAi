from __future__ import annotations

import unittest

from app.services.entitlements import resolve_user_plan
from app.services.usage_limits import estimate_tailor_tokens


class EntitlementsTest(unittest.TestCase):
    def test_plan_defaults_when_claim_missing(self) -> None:
        resolved = resolve_user_plan({})
        self.assertEqual(resolved.plan_key, "free")
        self.assertGreater(resolved.limits.monthly_application_limit, 0)

    def test_plan_reads_public_metadata(self) -> None:
        claims = {"public_metadata": {"plan": "starter"}}
        resolved = resolve_user_plan(claims)
        self.assertEqual(resolved.plan_key, "starter")

    def test_tailor_estimate_is_positive(self) -> None:
        tokens = estimate_tailor_tokens(
            resume_text="A" * 1000,
            job_description_text="B" * 1800,
            llm_max_tokens=1800,
        )
        self.assertGreater(tokens, 0)


if __name__ == "__main__":
    unittest.main()
