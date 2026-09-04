"""
CartGuard AI - Rule-Based Fallback Engine
Provides 100% deterministic fallback logic for specialized AI agents
when LLM services are offline, rate-limited, or return unparseable outputs.
"""

from typing import Dict, Any


class RuleBasedFallbackEngine:
    """
    Fallback reasoning engine. Evaluates behavioral signals against calibrated business rules
    to output structured JSON matching the specialized LLM agent contracts.
    """

    @staticmethod
    def diagnose_payment(session: Dict[str, Any]) -> Dict[str, Any]:
        payment_attempts = session.get("payment_attempts", 0)
        payment_failures = session.get("payment_failures", 0)
        time_on_page = session.get("time_on_payment", 0) or session.get("time_on_payment_page", 0)

        is_fail = payment_failures > 0 or payment_attempts >= 2
        frustration = min(10, payment_attempts * 3 + int(time_on_page / 30))

        specific_issue = "NONE"
        if payment_failures >= 2:
            specific_issue = "CARD_DECLINE"
        elif payment_attempts > 1 and time_on_page > 60:
            specific_issue = "UPI_TIMEOUT"
        elif payment_failures == 1:
            specific_issue = "NETBANKING_ERROR"

        action = "DO_NOTHING"
        if is_fail:
            action = "ALTERNATE_PAYMENT"

        return {
            "is_payment_failure": is_fail,
            "confidence": 0.88 if is_fail else 0.20,
            "frustration_score": max(1, frustration),
            "evidence": [
                f"Payment attempts: {payment_attempts}",
                f"Payment failures: {payment_failures}",
                f"Time on payment page: {time_on_page}s",
            ] if is_fail else ["No payment issues detected"],
            "specific_issue": specific_issue,
            "recommended_action": action,
            "is_fallback": True,
        }

    @staticmethod
    def diagnose_price(session: Dict[str, Any]) -> Dict[str, Any]:
        product_views = session.get("product_views", 0)
        cart_adds = session.get("cart_adds", 0)
        cart_removals = session.get("cart_removals", 0) or session.get("cart_removes", 0)
        tab_loss = session.get("tab_loss_count", 0) or session.get("tab_switches", 0)

        is_sensitive = (product_views >= 8 and cart_adds <= 2) or tab_loss >= 3 or cart_removals >= 2
        score = min(10, int(product_views * 0.5 + tab_loss * 1.5 + cart_removals * 2))

        pattern = "none"
        if tab_loss >= 3:
            pattern = "cross_site"
        elif product_views >= 8:
            pattern = "price_shopping"
        elif cart_removals >= 2:
            pattern = "cross_category"

        action = "DO_NOTHING"
        if is_sensitive:
            action = "VALUE_REASSURANCE" if session.get("cart_value", 0) > 2000 else "LIMITED_OFFER"

        return {
            "is_price_sensitive": is_sensitive,
            "confidence": 0.82 if is_sensitive else 0.30,
            "price_sensitivity_score": max(1, score),
            "comparison_pattern": pattern,
            "evidence": [
                f"Product views: {product_views}",
                f"Tab loss count: {tab_loss}",
                f"Cart removals: {cart_removals}",
            ] if is_sensitive else ["Normal browsing behavior"],
            "recommended_action": action,
            "is_fallback": True,
        }

    @staticmethod
    def diagnose_hesitation(session: Dict[str, Any]) -> Dict[str, Any]:
        checkout_steps = session.get("checkout_steps", 1)
        duration = session.get("session_duration", 0)
        form_errors = session.get("form_field_errors", 0)
        hesitation_score = session.get("form_hesitation", 0) or session.get("hesitation_score", 0)

        friction_score = min(10, int(form_errors * 3 + hesitation_score * 5 + (duration / 120)))
        level = "high" if friction_score >= 7 else "medium" if friction_score >= 4 else "low"

        friction_points = []
        if form_errors > 0:
            friction_points.append("form_validation_error")
        if duration > 300:
            friction_points.append("excessive_dwell_time")
        if hesitation_score > 0.6:
            friction_points.append("field_hesitation")

        action = "CHECKOUT_HELP" if level in ["high", "medium"] else "DO_NOTHING"

        return {
            "friction_points": friction_points if friction_points else ["none"],
            "friction_score": max(1, friction_score),
            "hesitation_level": level,
            "evidence": [
                f"Form field errors: {form_errors}",
                f"Session duration: {duration}s",
                f"Hesitation score: {hesitation_score}",
            ],
            "recommended_action": action,
            "is_fallback": True,
        }

    @staticmethod
    def diagnose_intent(session: Dict[str, Any]) -> Dict[str, Any]:
        cart_value = session.get("cart_value", 0)
        cart_adds = session.get("cart_adds", 0)
        duration = session.get("session_duration", 0)

        is_high_intent = cart_adds > 0 and cart_value > 500 and duration > 60
        intent_level = "high" if is_high_intent else "medium" if cart_adds > 0 else "low"

        return {
            "intent_level": intent_level,
            "bargain_hunting_score": 6 if cart_value > 2000 else 3,
            "confidence": 0.85 if is_high_intent else 0.40,
            "evidence": [
                f"Cart value: ₹{cart_value}",
                f"Cart additions: {cart_adds}",
            ],
            "recommended_action": "IN_APP_NUDGE" if is_high_intent else "DO_NOTHING",
            "is_fallback": True,
        }

    @staticmethod
    def validate_self_check(
        diagnosis: Dict[str, Any],
        action: Dict[str, Any],
        policy: Dict[str, Any],
    ) -> Dict[str, Any]:
        root_cause = diagnosis.get("root_cause", "UNKNOWN")
        discount = action.get("discount_amount", 0) or action.get("discount", 0)
        max_discount = policy.get("max_discount_inr", 0)

        violations = []
        if root_cause in ["PAYMENT_FAILURE", "CHECKOUT_FRICTION"] and discount > 0:
            violations.append(f"No discount permitted for {root_cause}")
        if discount > max_discount:
            violations.append(f"Discount ₹{discount} exceeds limit ₹{max_discount}")

        is_valid = len(violations) == 0
        adjusted = action.get("action_type", "DO_NOTHING") if is_valid else "DO_NOTHING"

        return {
            "is_valid": is_valid,
            "safety_score": 1.0 if is_valid else 0.0,
            "violations": violations,
            "adjusted_action": adjusted,
            "reasoning": "Passed deterministic rule validation" if is_valid else f"Violations detected: {violations}",
            "is_fallback": True,
        }


fallback_engine = RuleBasedFallbackEngine()
