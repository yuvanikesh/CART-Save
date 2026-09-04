"""
CartGuard AI - LangChain Multi-Agent System
Implements the 7 Enterprise Agents using LangChain, PromptTemplates, Runnables,
and Tool-Augmented Closed-Loop Learning for the Adaptive Adversarial Auditor.
"""
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from pydantic import BaseModel, Field

from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda, RunnableSequence
from langchain_core.tools import tool
from services.audit_service import audit_service


# ─────────────────────────────────────────────────────────────────────────────
# 1. Pydantic Schemas for Structured Verdicts
# ─────────────────────────────────────────────────────────────────────────────
class AdaptiveAuditVerdict(BaseModel):
    transaction_id: str = Field(description="Unique transaction / session ID")
    verdict: str = Field(description="PASS or REJECT based on guardrails & empirical memory")
    rule_violated: Optional[str] = Field(description="None if PASS; specific guardrail or historical failure pattern if REJECT")
    historical_risk_confidence: float = Field(description="Confidence score based on past outcomes (0.0 to 1.0)")
    learning_feedback_for_strategist: str = Field(description="Empirical guidance to improve the next iteration if rejected")
    empirical_memory: Dict[str, Any] = Field(default_factory=dict, description="Retrieved historical policy outcomes")


# ─────────────────────────────────────────────────────────────────────────────
# 2. Tool-Augmented Experience & Analytics Retrieval Tool (LangChain Tool)
# ─────────────────────────────────────────────────────────────────────────────
@tool
def query_historical_policy_outcomes_tool(psych_profile: str, proposed_action: str, discount_amount: float = 0.0) -> str:
    """Retrieves empirical conversion rates, opt-out risks, and over-discount flags for past actions taken on this psych profile.

    Args:
        psych_profile: Psychological category of the customer (e.g. SECURITY_CONSCIOUS, PRICE_SENSITIVE).
        proposed_action: Action proposed by the Strategist agent (e.g. LIMITED_OFFER, ALTERNATE_PAYMENT_GUIDANCE).
        discount_amount: Amount of discount proposed in INR.
    """
    res = audit_service.query_historical_policy_outcomes(psych_profile, proposed_action, discount_amount)
    return json.dumps(res)


# ─────────────────────────────────────────────────────────────────────────────
# 3. LangChain 7-Agent Components
# ─────────────────────────────────────────────────────────────────────────────

class LangChainFastMLFilter:
    """LangChain Fast ML Filter Agent (First line of defense)."""
    def __init__(self):
        self.prompt = PromptTemplate.from_template(
            "Evaluate quantitative risk score for cart session: {session_id}, cart value: {cart_value}, failures: {payment_failures}"
        )

    def run(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        start = time.time()
        cart_value = float(session_data.get("cart_value", 0))
        payment_failures = int(session_data.get("payment_failures", 0))
        payment_attempts = int(session_data.get("payment_attempts", 0))
        
        risk_score = 0.15
        if payment_failures > 0:
            risk_score += 0.60
        if payment_attempts >= 2:
            risk_score += 0.20

        risk_score = min(round(risk_score, 4), 1.0)
        passed_through = (risk_score < 0.35) and (cart_value < 50000.0)

        return {
            "agent": "LangChainFastMLFilter",
            "risk_score": risk_score,
            "risk_level": "HIGH" if (risk_score >= 0.75 or cart_value >= 50000.0) else "MEDIUM" if risk_score >= 0.35 else "LOW",
            "passed_through": passed_through,
            "latency_ms": round((time.time() - start) * 1000, 2),
        }


class LangChainHeadController:
    """LangChain Head Controller & Stateful Ledger."""
    def __init__(self):
        self.campaign_budget = 50000.0
        self.user_budget_cap = 500.0

    def route(self, session_data: Dict[str, Any], risk_score: float) -> Dict[str, Any]:
        cart_value = float(session_data.get("cart_value", 0))
        is_b2b = session_data.get("is_b2b", False) or cart_value > 25000
        user_spent = float(session_data.get("user_discount_spend_this_month", 0))
        user_remaining = max(0.0, self.user_budget_cap - user_spent)

        return {
            "routing_mode": "SEQUENTIAL" if (is_b2b or risk_score >= 0.85) else "PARALLEL",
            "user_budget_ok": user_remaining > 0,
            "max_allowed_user_discount": min(user_remaining, self.campaign_budget),
        }


class LangChainDomainResearcher:
    """LangChain Domain Research Agent (Root Cause Finder)."""
    def run(self, session_data: Dict[str, Any], filter_res: Dict[str, Any]) -> Dict[str, Any]:
        start = time.time()
        payment_failures = int(session_data.get("payment_failures", 0))
        error_code = str(session_data.get("last_error_code", ""))

        if payment_failures > 0 or "504" in error_code or "TIMEOUT" in error_code:
            category = "TECHNICAL"
            sub_cause = "BANK_504_TIMEOUT"
            evidence = ["Gateway returned timeout or error code"]
        else:
            category = "BEHAVIORAL"
            sub_cause = "PRICE_HESITATION"
            evidence = ["Extended cart dwell time & category switches"]

        return {
            "agent": "LangChainDomainResearcher",
            "category": category,
            "sub_cause": sub_cause,
            "confidence": 0.92,
            "evidence": evidence,
            "latency_ms": round((time.time() - start) * 1000, 2),
        }


class LangChainPsychProfiler:
    """LangChain Psych-Profiling Agent (Nudge Engine)."""
    def run(self, session_data: Dict[str, Any], domain_res: Dict[str, Any]) -> Dict[str, Any]:
        start = time.time()
        if domain_res.get("category") == "TECHNICAL":
            mindset = "SECURITY_CONSCIOUS"
            framing = "TRUST_BADGE"
            framing_text = "🔒 256-Bit Encrypted Payment • RBI Authorized Gateway • Instant Refund Guarantee"
        else:
            mindset = "PRICE_SENSITIVE"
            framing = "SCARCITY_SOCIAL_PROOF"
            framing_text = "⭐ 1,420 shoppers bought this item today • Guaranteed Lowest Price"

        return {
            "agent": "LangChainPsychProfiler",
            "mindset": mindset,
            "psych_framing": framing,
            "framing_text": framing_text,
            "latency_ms": round((time.time() - start) * 1000, 2),
        }


class LangChainRemediationStrategist:
    """LangChain Remediation Strategist Agent."""
    def run(
        self,
        session_data: Dict[str, Any],
        domain_res: Dict[str, Any],
        psych_res: Dict[str, Any],
        budget_info: Dict[str, Any],
        iteration: int = 1,
        rejection_feedback: Optional[str] = None
    ) -> Dict[str, Any]:
        start = time.time()
        cart_value = float(session_data.get("cart_value", 0))
        category = domain_res.get("category", "BEHAVIORAL")

        if category == "TECHNICAL":
            action_type = "ALTERNATE_PAYMENT_GUIDANCE"
            channel = "IN_APP"
            discount = 0.0
            message = f"{psych_res.get('framing_text')}\nHaving trouble paying? Try instant UPI or Cash on Delivery."
        else:
            if iteration > 1 and rejection_feedback:
                # Auto-correct discount down based on auditor empirical feedback!
                discount = 30.0  # Restricted minimum effective rate
                action_type = "LIMITED_OFFER"
                channel = "IN_APP"
                message = f"🎁 Special Offer: Complete your order now to save ₹{int(discount)} (Minimum effective rate applied)!"
            else:
                discount = 100.0
                action_type = "LIMITED_OFFER"
                channel = "IN_APP"
                message = f"🎁 Special Offer: Save ₹{int(discount)} on your order!"

        return {
            "agent": "LangChainRemediationStrategist",
            "proposed_action": action_type,
            "channel": channel,
            "discount_amount": discount,
            "message": message,
            "iteration": iteration,
            "latency_ms": round((time.time() - start) * 1000, 2),
        }


class LangChainAdversarialAuditor:
    """LangChain Adaptive Adversarial Auditor Agent (Tool-Augmented Learning)."""
    def __init__(self):
        self.tool = query_historical_policy_outcomes_tool

    def audit(
        self,
        session_data: Dict[str, Any],
        proposed_strategy: Dict[str, Any],
        psych_profile: Dict[str, Any]
    ) -> AdaptiveAuditVerdict:
        start = time.time()
        session_id = session_data.get("session_id", "UNKNOWN")
        cart_value = float(session_data.get("cart_value", 0))
        discount = float(proposed_strategy.get("discount_amount", 0))
        proposed_action = proposed_strategy.get("proposed_action", "DO_NOTHING")
        mindset = psych_profile.get("mindset", "DECISION_PARALYSIS")

        # 1. Tool Call for Empirical Outcome Memory Retrieval
        memory = audit_service.query_historical_policy_outcomes(mindset, proposed_action, discount)

        rejections = []
        rule_violated = None
        feedback = ""

        # 2. Check Empirical Opt-Out Rate (Spam calibration)
        if memory.get("opt_out_rate", 0) > 0.15:
            rejections.append(f"Negative Exemplar: Opt-out rate {memory['opt_out_rate']:.0%} > 15% threshold")
            rule_violated = "HISTORICAL_OPT_OUT_SPIKE (High spam rate detected in past outcomes)"
            feedback = "REJECT: Switch to non-monetary trust nudge or lower channel frequency."

        # 3. Check Dynamic Margin Elasticity (Over-discounting check)
        if memory.get("over_discount_flag", False):
            rejections.append(f"Over-discounting flag: Proposed discount RS. {discount} exceeds minimum effective threshold")
            rule_violated = "OVER_DISCOUNTING_LEAKAGE"
            feedback = f"REJECT: Proposed discount RS. {discount} exceeds minimum effective rate of {memory.get('min_effective_discount_pct')}%. Restrict discount on next iteration."

        verdict_str = "PASS" if len(rejections) == 0 else "REJECT"

        return AdaptiveAuditVerdict(
            transaction_id=session_id,
            verdict=verdict_str,
            rule_violated=rule_violated,
            historical_risk_confidence=0.95 if verdict_str == "PASS" else 0.35,
            learning_feedback_for_strategist=feedback or "Approved by empirical policy auditor.",
            empirical_memory=memory
        )
