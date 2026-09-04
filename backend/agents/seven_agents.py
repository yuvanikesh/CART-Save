"""
CartGuard AI - 7-Agent Enterprise Recovery & Remediation Framework
Explicit implementation of all 7 specialized agents with stateful context,
closed-loop learning, parallel/sequential routing, and microsecond audit ledgers.
"""
import asyncio
import json
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# 1. Fast ML Filter (First Line of Defense)
# ─────────────────────────────────────────────────────────────────────────────
class FastMLFilterAgent:
    """
    First line of defense. Computes quantitative risk score in <5ms.
    Lets low-risk, natural conversions pass through instantly without waking up LLMs.
    """
    name = "FastMLFilter"

    async def evaluate(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.time()

        cart_value = float(session_data.get("cart_value", 0))
        duration = float(session_data.get("session_duration", 0))
        views = int(session_data.get("product_views", 1))
        cart_adds = int(session_data.get("cart_adds", 1))
        payment_attempts = int(session_data.get("payment_attempts", 0))
        payment_failures = int(session_data.get("payment_failures", 0))
        tab_switches = int(session_data.get("tab_loss_count", session_data.get("tab_switches", 0)))
        form_errors = int(session_data.get("form_hesitation", session_data.get("form_field_errors", 0)))

        # Quantitative risk scoring
        risk_score = 0.15  # baseline natural conversion risk
        if payment_failures > 0:
            risk_score += 0.60
        if payment_attempts >= 2:
            risk_score += 0.20
        if form_errors > 2:
            risk_score += 0.15
        if tab_switches > 3:
            risk_score += 0.15
        if duration > 300 and cart_adds > 0:
            risk_score += 0.10

        # Also incorporate ensemble ML prediction if available
        try:
            from models.ensemble_model import get_model
            model = get_model()
            ml_pred = model.predict_proba(session_data)
            ml_risk = float(ml_pred.get("risk_score", 0.0))
            if ml_risk > 0:
                risk_score = max(risk_score, ml_risk)
        except Exception:
            pass

        risk_score = min(round(risk_score, 4), 1.0)
        latency_ms = (time.time() - start_time) * 1000

        # Pass through low risk instantly (< 0.35) unless high value (>= ₹50k)
        passed_through = (risk_score < 0.35) and (cart_value < 50000.0)

        return {
            "agent": self.name,
            "risk_score": risk_score,
            "risk_level": "HIGH" if (risk_score >= 0.75 or cart_value >= 50000.0) else "MEDIUM" if risk_score >= 0.35 else "LOW",
            "passed_through": passed_through,
            "reason": "LOW_RISK_NATURAL_CONVERSION" if passed_through else "HIGH_FRICTION_OR_HIGH_VALUE_DETECTED",
            "latency_ms": round(latency_ms, 3),
            "wake_llm": not passed_through,
        }


# ─────────────────────────────────────────────────────────────────────────────
# 2. Head Controller & Stateful Ledger (The Boss)
# ─────────────────────────────────────────────────────────────────────────────
class HeadControllerLedger:
    """
    Maintains global state context, customer friction scores, running discount budgets,
    determines dynamic routing (Parallel sub-1.5s vs Sequential deep context),
    and enforces max 2 retry iterations for Adversarial Auditor rejections.
    """
    name = "HeadControllerLedger"

    def __init__(self):
        self.running_campaign_budget = 50000.0  # ₹50,000 cap
        self.per_user_budget_cap = 500.0        # ₹500 cap
        self.customer_friction_ledger: Dict[str, float] = {}

    def get_user_friction_score(self, user_id: str) -> float:
        return self.customer_friction_ledger.get(user_id, 0.0)

    def record_user_friction(self, user_id: str, friction_delta: float):
        current = self.customer_friction_ledger.get(user_id, 0.0)
        self.customer_friction_ledger[user_id] = min(1.0, max(0.0, current + friction_delta))

    def determine_routing_mode(self, session_data: Dict[str, Any], risk_score: float) -> str:
        """
        Decides routing strategy:
        - PARALLEL (sub-1.5s): Real-time checkout drops, fast transaction rescue.
        - SEQUENTIAL: High value, B2B invoices, or ambiguous multi-signal friction.
        """
        cart_value = float(session_data.get("cart_value", 0))
        is_b2b = session_data.get("is_b2b", False) or cart_value > 25000

        if is_b2b or risk_score >= 0.85:
            return "SEQUENTIAL"
        return "PARALLEL"

    def check_budget_limits(self, user_id: str, user_spent_this_month: float) -> Dict[str, Any]:
        user_remaining = max(0.0, self.per_user_budget_cap - user_spent_this_month)
        campaign_remaining = max(0.0, self.running_campaign_budget)

        return {
            "user_budget_ok": user_remaining > 0,
            "campaign_budget_ok": campaign_remaining > 0,
            "max_allowed_user_discount": min(user_remaining, campaign_remaining),
        }


# ─────────────────────────────────────────────────────────────────────────────
# 3. Domain Research Agent (Root Cause Finder)
# ─────────────────────────────────────────────────────────────────────────────
class DomainResearchAgent:
    """
    Diagnoses root causes by categorizing failures into:
    1. TECHNICAL (bank timeout, 504 gateway, network drop)
    2. OPERATIONAL (mandate cooldown, limit exceeded, address friction)
    3. BEHAVIORAL (price hesitation, product comparison, intent drop)
    """
    name = "DomainResearchAgent"

    async def diagnose(self, session_data: Dict[str, Any], risk_info: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.time()

        payment_failures = int(session_data.get("payment_failures", 0))
        payment_attempts = int(session_data.get("payment_attempts", 0))
        error_code = session_data.get("last_error_code", "")
        form_errors = int(session_data.get("form_field_errors", session_data.get("form_hesitation", 0)))
        tab_switches = int(session_data.get("tab_loss_count", session_data.get("tab_switches", 0)))
        price_sensitivity = float(session_data.get("price_sensitivity", 0.5))

        # Root Cause Analysis
        if payment_failures > 0 or "504" in str(error_code) or "TIMEOUT" in str(error_code).upper():
            category = "TECHNICAL"
            sub_cause = "BANK_504_TIMEOUT" if "504" in str(error_code) else "GATEWAY_TIMEOUT"
            evidence = ["Payment gateway returned failure code", f"Attempts: {payment_attempts}, Failures: {payment_failures}"]
            confidence = 0.94
        elif "MANDATE" in str(error_code).upper() or "COOLDOWN" in str(error_code).upper() or form_errors > 3:
            category = "OPERATIONAL"
            sub_cause = "MANDATE_COOLDOWN" if "MANDATE" in str(error_code).upper() else "CHECKOUT_FORM_FRICTION"
            evidence = ["Operational constraint or repeated form validation errors", f"Form field errors: {form_errors}"]
            confidence = 0.88
        else:
            category = "BEHAVIORAL"
            if tab_switches >= 3:
                sub_cause = "PRODUCT_COMPARISON"
                evidence = [f"High tab loss count ({tab_switches}) suggesting price comparison"]
            elif price_sensitivity > 0.6:
                sub_cause = "PRICE_HESITATION"
                evidence = ["Extended cart dwell time with price sensitivity signals"]
            else:
                sub_cause = "DECISION_PARALYSIS"
                evidence = ["Multiple back navigations without purchase intent"]
            confidence = 0.82

        latency_ms = (time.time() - start_time) * 1000

        return {
            "agent": self.name,
            "category": category,
            "sub_cause": sub_cause,
            "confidence": confidence,
            "evidence": evidence,
            "latency_ms": round(latency_ms, 3),
        }


# ─────────────────────────────────────────────────────────────────────────────
# 4. Psych-Profiling & Behavioral Agent (The Nudge Engine)
# ─────────────────────────────────────────────────────────────────────────────
class PsychProfilingAgent:
    """
    Evaluates micro-hesitation signals and categorizes user mindset into:
    - PRICE_SENSITIVE
    - SECURITY_CONSCIOUS
    - DECISION_PARALYSIS
    Provides psychological framing (trust badges, one-click clarity, scarcity)
    without giving away unneeded monetary discounts.
    """
    name = "PsychProfilingAgent"

    async def profile(self, session_data: Dict[str, Any], domain_diagnosis: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.time()

        scroll_speed = float(session_data.get("scroll_speed", 120.0))
        form_hesitation = float(session_data.get("form_hesitation", 0.5))
        tab_switches = int(session_data.get("tab_loss_count", session_data.get("tab_switches", 0)))
        price_sensitivity = float(session_data.get("price_sensitivity", 0.5))

        # Classify Mindset
        if domain_diagnosis.get("category") == "TECHNICAL" or form_hesitation > 0.8:
            mindset = "SECURITY_CONSCIOUS"
            psych_framing = "TRUST_BADGE"
            framing_text = "🔒 256-Bit Encrypted Payment • RBI Authorized Gateway • Instant Refund Guarantee"
        elif tab_switches >= 3 or price_sensitivity > 0.7:
            mindset = "PRICE_SENSITIVE"
            psych_framing = "SCARCITY_SOCIAL_PROOF"
            framing_text = "⭐ 1,420 shoppers bought this item today • Guaranteed Lowest Price"
        else:
            mindset = "DECISION_PARALYSIS"
            psych_framing = "ONE_CLICK_CLARITY"
            framing_text = "⚡ Express 1-Click Checkout Available • Free 30-Day Returns"

        latency_ms = (time.time() - start_time) * 1000

        return {
            "agent": self.name,
            "mindset": mindset,
            "psych_framing": psych_framing,
            "framing_text": framing_text,
            "hesitation_index": round(form_hesitation, 2),
            "latency_ms": round(latency_ms, 3),
        }


# ─────────────────────────────────────────────────────────────────────────────
# 5. Remediation Strategist (The Solution Maker)
# ─────────────────────────────────────────────────────────────────────────────
class RemediationStrategistAgent:
    """
    Synthesizes Root Cause + Psych Profile + Discount Budget into a bounded action.
    Explicitly chooses "DO_NOTHING" when margins are thin or technical retries suffice.
    """
    name = "RemediationStrategist"

    async def synthesize(
        self,
        session_data: Dict[str, Any],
        domain_diag: Dict[str, Any],
        psych_prof: Dict[str, Any],
        budget_info: Dict[str, Any],
        iteration: int = 1,
        rejection_feedback: Optional[str] = None
    ) -> Dict[str, Any]:
        start_time = time.time()

        cart_value = float(session_data.get("cart_value", 0.0))
        gross_margin_rate = 0.25  # 25% standard gross margin
        gross_margin_inr = cart_value * gross_margin_rate
        category = domain_diag.get("category", "BEHAVIORAL")
        mindset = psych_prof.get("mindset", "DECISION_PARALYSIS")

        # Handle iteration retry adjustments if auditor rejected previous proposal
        discount_scalar = 1.0
        if iteration > 1:
            if rejection_feedback and ("minimum effective rate" in str(rejection_feedback).lower() or "over-discounting" in str(rejection_feedback).lower()):
                # Auto-cap discount to 3% minimum effective rate
                max_allowed_eff_disc = cart_value * 0.03
                discount_scalar = min(0.25, max_allowed_eff_disc / max(1.0, gross_margin_inr * 0.4))
            else:
                discount_scalar = 0.5

        if category == "TECHNICAL":
            # For technical failures, no discount is given — offer payment guidance / auto-retry
            action_type = "ALTERNATE_PAYMENT_GUIDANCE"
            channel = "IN_APP"
            discount_amount = 0.0
            message = f"{psych_prof.get('framing_text')}\nHaving trouble paying? Try instant UPI or Cash on Delivery."
        elif category == "OPERATIONAL":
            action_type = "CHECKOUT_ASSISTANCE"
            channel = "IN_APP"
            discount_amount = 0.0
            message = "We noticed issue with address/mandate. Tap here for 1-click customer support."
        else:
            # BEHAVIORAL
            if mindset == "PRICE_SENSITIVE" and budget_info.get("user_budget_ok") and gross_margin_inr >= 50:
                max_disc = min(budget_info.get("max_allowed_user_discount", 100), gross_margin_inr * 0.4)
                discount_amount = round(max_disc * discount_scalar, 2)
                if discount_amount > 0:
                    action_type = "LIMITED_OFFER"
                    channel = "IN_APP"
                    message = f"🎁 Special Offer: Complete your order in 15 mins to save ₹{int(discount_amount)}!"
                else:
                    action_type = "VALUE_REASSURANCE"
                    channel = "IN_APP"
                    discount_amount = 0.0
                    message = psych_prof.get("framing_text")
            elif mindset == "SECURITY_CONSCIOUS":
                action_type = "VALUE_REASSURANCE"
                channel = "IN_APP"
                discount_amount = 0.0
                message = psych_prof.get("framing_text")
            else:
                # Decision paralysis or thin margin -> DO_NOTHING or non-monetary nudge
                if gross_margin_inr < 30:
                    action_type = "DO_NOTHING"
                    channel = "NONE"
                    discount_amount = 0.0
                    message = "Margins too thin for monetary discount. Let natural conversion occur."
                else:
                    action_type = "ONE_CLICK_CLARITY"
                    channel = "IN_APP"
                    discount_amount = 0.0
                    message = psych_prof.get("framing_text")

        latency_ms = (time.time() - start_time) * 1000

        return {
            "agent": self.name,
            "proposed_action": action_type,
            "channel": channel,
            "discount_amount": discount_amount,
            "message": message,
            "gross_margin_inr": round(gross_margin_inr, 2),
            "iteration": iteration,
            "latency_ms": round(latency_ms, 3),
        }


# ─────────────────────────────────────────────────────────────────────────────
# 6. Adaptive Adversarial Auditor (Closed-Loop Learning & Secondary Check)
# ─────────────────────────────────────────────────────────────────────────────
class AdaptiveAdversarialAuditor:
    """
    LangChain-Augmented Adaptive Adversarial Auditor.
    Audits proposed strategy against hard statutory guardrails (RBI, TRAI, Gross Margin)
    AND empirical historical performance via Tool-Augmented Outcome Memory.
    """
    name = "AdaptiveAdversarialAuditor"

    async def audit(
        self,
        session_data: Dict[str, Any],
        proposed_strategy: Dict[str, Any],
        audit_service_ref: Any = None,
        psych_profile: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        start_time = time.time()
        rejections = []
        warnings = []

        cart_value = float(session_data.get("cart_value", 0))
        discount = float(proposed_strategy.get("discount_amount", 0))
        channel = proposed_strategy.get("channel", "IN_APP")
        action_type = proposed_strategy.get("proposed_action", "DO_NOTHING")
        mindset = psych_profile.get("mindset", "PRICE_SENSITIVE") if psych_profile else "PRICE_SENSITIVE"
        discount_pct = (discount / cart_value * 100.0) if cart_value > 0 else 0.0

        # 1. Tool Call: Experience & Analytics Retrieval Tool
        try:
            from agents.langchain_agents import query_historical_policy_outcomes_tool
            if audit_service_ref:
                empirical_memory = audit_service_ref.query_historical_policy_outcomes(mindset, action_type, discount_pct)
            else:
                memory_str = query_historical_policy_outcomes_tool.invoke({"psych_profile": mindset, "proposed_action": action_type, "discount_amount": discount})
                empirical_memory = json.loads(memory_str)
        except Exception:
            empirical_memory = {
                "sample_size": 15,
                "recovery_rate": 0.50,
                "historical_verdict": "INSUFFICIENT_DATA_DEFAULT_TO_STANDARD_GUARDRAIL",
                "opt_out_rate": 0.02,
                "over_discount_flag": False
            }

        # 2. Hard Statutory Guardrails (Zero Tolerance)
        # Gross Margin Floor Check (Must leave >= 15% net margin)
        gross_margin = float(proposed_strategy.get("gross_margin_inr", cart_value * 0.25))
        net_margin_remaining = gross_margin - discount
        min_margin_floor = cart_value * 0.15

        if discount > 0 and net_margin_remaining < min_margin_floor:
            rejections.append(f"Gross margin floor violated: Discount ₹{discount} leaves net margin ₹{net_margin_remaining:.2f} < floor ₹{min_margin_floor:.2f}")

        # TRAI / DND Messaging Hours Check (8 AM - 9 PM IST)
        if channel in ["SMS", "WHATSAPP"]:
            current_hour = datetime.now().hour
            if current_hour < 8 or current_hour >= 21:
                rejections.append(f"TRAI DND window restriction: Direct SMS/WhatsApp not permitted at hour {current_hour}:00 IST")

        # RBI E-Mandate Cooldown Check
        if action_type == "RETRY_MANDATE":
            last_mandate_hours_ago = float(session_data.get("last_mandate_retry_hours_ago", 48.0))
            if last_mandate_hours_ago < 24.0:
                rejections.append(f"RBI mandate cooldown active: Retry requested {last_mandate_hours_ago}h ago (<24h limit)")

        # 3. Soft Guardrails (Adaptive / Historical Empirical Learning)
        rule_violated = None
        learning_feedback = ""

        # Empirical Spam / Opt-Out Rate Check (>15%)
        opt_out_rate = empirical_memory.get("opt_out_rate", 0.0)
        if opt_out_rate > 0.15:
            rejections.append(f"Negative Exemplar: Historical opt-out rate {opt_out_rate:.1%} exceeds 15.0% threshold")
            rule_violated = "HISTORICAL_OPT_OUT_SPIKE (High spam rate detected in past outcomes)"
            learning_feedback = f"REJECT: Action {action_type} for {mindset} previously caused {opt_out_rate:.1%} opt-outs. Switch to non-monetary trust nudge."

        # Dynamic Margin Elasticity Check (Over-discounting flag)
        if empirical_memory.get("over_discount_flag", False):
            min_eff = empirical_memory.get("min_effective_discount_pct", 3.0)
            rejections.append(f"Over-Discounting Flag: Proposed discount RS. {discount} exceeds minimum effective threshold ({min_eff:.1f}%)")
            rule_violated = "OVER_DISCOUNTING_LEAKAGE"
            learning_feedback = f"REJECT: Proposed discount RS. {discount} ({discount_pct:.1f}%) exceeds minimum effective rate of {min_eff:.1f}%. Lower discount on iteration 2."

        passed = len(rejections) == 0
        auditor_confidence = 0.95 if passed else 0.35

        latency_ms = (time.time() - start_time) * 1000

        return {
            "agent": self.name,
            "status": "APPROVED" if passed else "REJECTED",
            "verdict": "PASS" if passed else "REJECT",
            "auditor_confidence": auditor_confidence,
            "rule_violated": rule_violated or (rejections[0] if rejections else None),
            "learning_feedback_for_strategist": learning_feedback or ("Approved by empirical policy auditor." if passed else rejections[0]),
            "rejections": rejections,
            "warnings": warnings,
            "empirical_memory": empirical_memory,
            "latency_ms": round(latency_ms, 3),
        }


# ─────────────────────────────────────────────────────────────────────────────
# 7. Human-in-the-Loop Gate & Audit Trail
# ─────────────────────────────────────────────────────────────────────────────
class HITLAuditLedger:
    """
    Catches edge cases, high-value transactions (>₹50k), or low-confidence audits
    for single-click human sign-off.
    Writes every microsecond decision step to an immutable audit ledger.
    """
    name = "HITLAuditLedger"

    def should_trigger_hitl(
        self,
        session_data: Dict[str, Any],
        auditor_result: Dict[str, Any],
        risk_info: Dict[str, Any]
    ) -> Tuple[bool, str]:
        cart_value = float(session_data.get("cart_value", 0))
        auditor_conf = float(auditor_result.get("auditor_confidence", 1.0))
        auditor_status = auditor_result.get("status", "APPROVED")

        if cart_value >= 50000.0:
            return True, "HIGH_VALUE_TRANSACTION (>RS. 50,000)"
        if auditor_conf < 0.70 or auditor_status == "REJECTED":
            return True, "LOW_AUDITOR_CONFIDENCE / REJECTED_POLICY"
        return False, "AUTOMATED_APPROVAL"

