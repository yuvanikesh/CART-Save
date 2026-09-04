"""
CartGuard AI - Member M3 Test Suite
Tests FastAPI endpoints, WebSocket connection, Policy Engine, Redis Service, and Audit Logging.
"""
import unittest
import asyncio
import time
import json
from fastapi.testclient import TestClient

from main import app
from services.redis_service import redis_service, RedisService
from services.audit_service import audit_service
from services.notification_service import notification_service
from agents.orchestrator import PolicyEngine


class TestM3Backend(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.policy_engine = PolicyEngine()

    def test_health_endpoint(self):
        """Test GET /health returns status ok."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertIn("timestamp", data)

    def test_metrics_endpoint(self):
        """Test GET /metrics returns Prometheus-style metrics."""
        response = self.client.get("/metrics")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("total_sessions", data)
        self.assertIn("p95_latency_ms", data)
        self.assertIn("recovery_rate", data)
        self.assertIn("avg_risk_score", data)

    def test_score_session_endpoint_payment_failure(self):
        """Test POST /score-session for payment failure scenario."""
        payload = {
            "session_id": "M3_TEST_S1001",
            "cart_value": 2499,
            "session_duration": 210,
            "product_views": 4,
            "cart_adds": 3,
            "checkout_reached": 1,
            "payment_attempts": 2,
            "payment_failures": 2,
            "email_opt_in": True,
            "whatsapp_opt_in": False,
            "mouse_velocity": 0.8,
            "scroll_speed": 120,
            "form_hesitation": 0.9,
            "tab_loss_count": 1
        }
        response = self.client.post("/score-session", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["session_id"], "M3_TEST_S1001")
        self.assertIn("risk_score", data)
        self.assertIn("reason", data)
        self.assertIn("action", data)
        self.assertIn("self_check", data)
        self.assertEqual(data["self_check"], "PASSED")

    def test_score_session_endpoint_low_risk(self):
        """Test POST /score-session for low risk session."""
        payload = {
            "session_id": "M3_TEST_S1003",
            "cart_value": 1599,
            "session_duration": 45,
            "product_views": 2,
            "cart_adds": 1,
            "checkout_reached": 1,
            "payment_attempts": 0,
            "payment_failures": 0,
            "email_opt_in": True,
            "whatsapp_opt_in": False,
            "mouse_velocity": 0.2,
            "scroll_speed": 80,
            "form_hesitation": 0.1,
            "tab_loss_count": 0
        }
        response = self.client.post("/score-session", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["session_id"], "M3_TEST_S1003")

    def test_audit_log_endpoint(self):
        """Test GET /audit-log/{session_id} retrieval."""
        session_id = "M3_AUDIT_CHECK_99"
        audit_service.log_decision(
            {
                "session_id": session_id,
                "risk_score": 0.82,
                "risk_level": "HIGH",
                "diagnosis": {"root_cause": "PAYMENT_FAILURE", "confidence": 0.9},
                "action": {"action_type": "ALTERNATE_PAYMENT", "channel": "IN_APP", "discount_amount": 0},
                "policy": {"uplift_probability": 0.4, "expected_incremental_margin_inr": 0},
                "self_check": {"status": "PASSED"},
                "metrics": {"total_latency_ms": 115, "total_cost_inr": 0.05}
            },
            {"user_id": "U123"}
        )
        response = self.client.get(f"/audit-log/{session_id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["session_id"], session_id)
        self.assertEqual(data["root_cause"], "PAYMENT_FAILURE")

    def test_policy_engine_rules(self):
        """Test PolicyEngine rules 1 through 5."""
        # Rule 1: Low risk -> DO_NOTHING
        r1 = self.policy_engine.decide({"risk_score": 0.2}, {"root_cause": "UNKNOWN"})
        self.assertEqual(r1["action"], "DO_NOTHING")

        # Rule 2: Payment failure -> ALTERNATE_PAYMENT (0 discount)
        r2 = self.policy_engine.decide({"risk_score": 0.8}, {"root_cause": "PAYMENT_FAILURE"})
        self.assertEqual(r2["action"], "ALTERNATE_PAYMENT")
        self.assertEqual(r2["discount"], 0)

        # Rule 3: Price shopping with risk < 0.7 -> VALUE_REASSURANCE
        r3 = self.policy_engine.decide({"risk_score": 0.6}, {"root_cause": "PRICE_SHOPPING"})
        self.assertEqual(r3["action"], "VALUE_REASSURANCE")

        # Rule 4: High risk (> 0.7) + budget -> LIMITED_DISCOUNT
        r4 = self.policy_engine.decide({"risk_score": 0.85}, {"root_cause": "PRICE_SHOPPING"}, {"remaining": 100, "min_discount": 10})
        self.assertEqual(r4["action"], "LIMITED_DISCOUNT")
        self.assertGreater(r4["discount"], 0)

        # Rule 5: Checkout friction -> CHECKOUT_HELP
        r5 = self.policy_engine.decide({"risk_score": 0.65}, {"root_cause": "CHECKOUT_FRICTION"})
        self.assertEqual(r5["action"], "CHECKOUT_HELP")

    def test_redis_service_fallback(self):
        """Test Redis service fallback cache and rate limiting."""
        async def run_redis_tests():
            rs = RedisService()
            # Cache set/get in fallback mode
            await rs.cache_set("key_1", {"hello": "world"}, ttl_seconds=60)
            val = await rs.cache_get("key_1")
            self.assertEqual(val, {"hello": "world"})

            # Rate limit in fallback mode
            limited = await rs.is_rate_limited("user_1", max_requests=2, window_seconds=60)
            self.assertFalse(limited)
            await rs.is_rate_limited("user_1", max_requests=2, window_seconds=60)
            limited_now = await rs.is_rate_limited("user_1", max_requests=2, window_seconds=60)
            self.assertTrue(limited_now)

        asyncio.run(run_redis_tests())

    def test_notification_consent_check(self):
        """Test NotificationService consent enforcement."""
        # DND registered user for SMS
        consent = notification_service._check_consent({"is_dnd_registered": True}, "SMS")
        self.assertFalse(consent)

        # Opted out email user
        email_consent = notification_service._check_consent({"email_opt_in": False}, "EMAIL")
        self.assertFalse(email_consent)


if __name__ == "__main__":
    unittest.main()
