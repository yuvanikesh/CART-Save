"""
CartGuard AI - M2 AI/LLM Engineer Test Suite
Tests covering prompt rendering, specialized reasoning agents, session caching,
rule-based fallback engine, self-check validator, and agent orchestrator synthesis.
"""

import sys
import os
import unittest
import asyncio

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.prompts import (
    PAYMENT_FAILURE_PROMPT,
    PRICE_SENSITIVITY_PROMPT,
    BEHAVIORAL_HESITATION_PROMPT,
    INTENT_RECOVERY_PROMPT,
    SELF_CHECK_VALIDATION_PROMPT,
)
from agents.caching import SessionCache, session_cache
from agents.fallback import RuleBasedFallbackEngine
from agents.llm_agents import (
    PaymentFailureAnalyzer,
    PriceSensitivityAnalyzer,
    BehavioralHesitationAnalyzer,
    IntentRecoveryAnalyzer,
    SelfCheckValidator,
    AgentOrchestrator,
)
from agents.orchestrator import orchestrator


class TestM2LLMAgents(unittest.TestCase):

    def setUp(self):
        self.session_cache = SessionCache()
        self.sample_payment_session = {
            "session_id": "S1001",
            "cart_value": 2499,
            "session_duration": 210,
            "product_views": 4,
            "cart_adds": 3,
            "checkout_steps_completed": 1,
            "payment_attempts": 3,
            "payment_failures": 2,
            "time_on_payment_page": 120,
            "form_field_errors": 1,
        }
        self.sample_price_session = {
            "session_id": "S1002",
            "cart_value": 899,
            "session_duration": 540,
            "product_views": 14,
            "cart_adds": 2,
            "cart_removes": 3,
            "tab_switches": 4,
            "category_switches": 5,
        }
        self.sample_hesitation_session = {
            "session_id": "S1003",
            "cart_value": 3499,
            "session_duration": 420,
            "product_views": 5,
            "cart_adds": 4,
            "checkout_steps_completed": 1,
            "form_field_errors": 3,
            "hesitation_score": 0.85,
        }

    def test_prompts_library_rendering(self):
        """Test that all 5 prompt templates render correctly without key errors."""
        p1 = PAYMENT_FAILURE_PROMPT.format(
            payment_attempts=2,
            payment_failures=1,
            time_on_payment=45,
            session_duration=120,
            cart_value=1500,
            checkout_stage=2,
            form_field_errors=0,
        )
        self.assertIn("THINKING CHAIN", p1)

        p2 = PRICE_SENSITIVITY_PROMPT.format(
            product_views=10,
            unique_categories=3,
            cart_adds=2,
            cart_removals=1,
            cart_value_changes=2,
            session_duration=300,
            tab_loss_count=2,
            cart_value=999,
        )
        self.assertIn("is_price_sensitive", p2)

        p3 = BEHAVIORAL_HESITATION_PROMPT.format(
            checkout_steps=1,
            time_per_step=180,
            scroll_speed=100,
            form_interactions=5,
            abandoned_fields=2,
            mouse_velocity=0.4,
            hesitation_score=0.75,
        )
        self.assertIn("hesitation_level", p3)

        p4 = INTENT_RECOVERY_PROMPT.format(
            cart_value=2500,
            session_duration=240,
            user_segment="REGULAR",
            is_returning_visitor=True,
            risk_score=0.7,
            primary_diagnosis="PRICE_SENSITIVITY",
            max_budget=200,
        )
        self.assertIn("bargain_hunting_score", p4)

        p5 = SELF_CHECK_VALIDATION_PROMPT.format(
            risk_score=0.8,
            root_cause="PAYMENT_FAILURE",
            confidence=0.9,
            action="ALTERNATE_PAYMENT",
            discount_amount=0,
            max_allowed_discount=0,
            channel="IN_APP",
            consent_ok=True,
            budget_ok=True,
        )
        self.assertIn("safety_score", p5)

    def test_session_cache_performance(self):
        """Test context hashing and cache hit/miss statistics."""
        ctx = self.sample_payment_session
        agent_name = "PaymentFailureAnalyzer"

        self.assertIsNone(self.session_cache.get(ctx, agent_name))
        self.assertEqual(self.session_cache.misses, 1)

        res = {"is_payment_failure": True, "confidence": 0.9}
        self.session_cache.set(ctx, agent_name, res)

        cached = self.session_cache.get(ctx, agent_name)
        self.assertIsNotNone(cached)
        self.assertTrue(cached.get("is_cached"))
        self.assertEqual(cached["is_payment_failure"], True)

        stats = self.session_cache.get_stats()
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["total_queries"], 2)
        self.assertEqual(stats["hit_rate_pct"], 50.0)

    def test_rule_based_fallback_engine(self):
        """Test fallback engine deterministic logic."""
        pay_res = RuleBasedFallbackEngine.diagnose_payment(self.sample_payment_session)
        self.assertTrue(pay_res["is_payment_failure"])
        self.assertEqual(pay_res["specific_issue"], "CARD_DECLINE")

        price_res = RuleBasedFallbackEngine.diagnose_price(self.sample_price_session)
        self.assertTrue(price_res["is_price_sensitive"])

        hes_res = RuleBasedFallbackEngine.diagnose_hesitation(self.sample_hesitation_session)
        self.assertIn("high", hes_res["hesitation_level"])

        val_res = RuleBasedFallbackEngine.validate_self_check(
            {"root_cause": "PAYMENT_FAILURE"},
            {"action_type": "LIMITED_OFFER", "discount_amount": 100},
            {"max_discount_inr": 50},
        )
        self.assertFalse(val_res["is_valid"])
        self.assertEqual(val_res["adjusted_action"], "DO_NOTHING")

    def test_specialized_agents_diagnose(self):
        """Test individual specialized agents diagnose methods asynchronously."""
        async def run_agents():
            pay_agent = PaymentFailureAnalyzer()
            res_pay = await pay_agent.diagnose(self.sample_payment_session)
            self.assertIn("is_payment_failure", res_pay)

            price_agent = PriceSensitivityAnalyzer()
            res_price = await price_agent.diagnose(self.sample_price_session)
            self.assertIn("is_price_sensitive", res_price)

            hes_agent = BehavioralHesitationAnalyzer()
            res_hes = await hes_agent.diagnose(self.sample_hesitation_session)
            self.assertIn("friction_score", res_hes)

            intent_agent = IntentRecoveryAnalyzer()
            res_intent = await intent_agent.diagnose(self.sample_payment_session)
            self.assertIn("intent_level", res_intent)

            validator = SelfCheckValidator()
            res_val = await validator.validate(
                {"root_cause": "PAYMENT_FAILURE"},
                {"action_type": "ALTERNATE_PAYMENT", "discount_amount": 0},
                {"max_discount_inr": 0},
            )
            self.assertIn("is_valid", res_val)

        asyncio.run(run_agents())

    def test_agent_orchestrator_synthesis(self):
        """Test AgentOrchestrator weighted synthesis prioritization."""
        async def run_orchestrator():
            orch = AgentOrchestrator()
            diag = await orch.diagnose_session(self.sample_payment_session)
            self.assertEqual(diag["root_cause"], "PAYMENT_FAILURE")
            self.assertLess(diag["latency_ms"], 500)

        asyncio.run(run_orchestrator())

    def test_orchestrator_pipeline_end_to_end(self):
        """Test end-to-end main orchestrator pipeline execution."""
        async def run_main_pipeline():
            res = await orchestrator.process_session(self.sample_payment_session)
            self.assertIn("session_id", res)
            self.assertIn("risk_score", res)
            self.assertIn("diagnosis", res)
            self.assertIn("self_check", res)
            self.assertEqual(res["self_check"]["status"], "PASSED")

        asyncio.run(run_main_pipeline())


if __name__ == "__main__":
    unittest.main()
