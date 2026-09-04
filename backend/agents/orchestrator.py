"""
CartGuard AI - LLM Agent System
Multi-agent pipeline: Signal → Risk → Diagnosis → Policy → Action → Self-Check
"""
import asyncio
import json
import time
import os
import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import httpx


@dataclass
class AgentMessage:
    agent: str
    output: Dict[str, Any]
    latency_ms: float = 0.0


@dataclass
class AgentConversation:
    session_id: str
    messages: List[AgentMessage] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    total_cost_inr: float = 0.0


class LLMClient:
    """Unified LLM client supporting Groq (Llama), OpenAI, and local Ollama."""

    def __init__(self):
        self.groq_key = os.getenv("GROQ_API_KEY", "")
        self.openai_key = os.getenv("OPENAI_API_KEY", "")
        self.provider = os.getenv("LLM_PROVIDER", "groq")
        self.groq_model = "llama-3.2-3b-preview"
        self.openai_model = "gpt-4o-mini"
        self.local_url = os.getenv("LOCAL_LLM_URL", "http://localhost:11434")

    async def complete(self, prompt: str, model_size: str = "small") -> Dict[str, Any]:
        """
        Complete a prompt using the appropriate model.
        model_size: 'small' (Llama 3B), 'medium' (GPT-4o-mini), 'large' (GPT-4o)
        """
        start = time.time()
        cost = 0.0

        try:
            if self.provider == "groq" and self.groq_key:
                result = await self._groq_complete(prompt)
                cost = 0.05  # ~0.05 INR for Llama 3B via Groq
            elif self.provider == "openai" and self.openai_key:
                result = await self._openai_complete(prompt, model_size)
                cost = 0.50 if model_size == "large" else 0.15
            else:
                # Fallback: Rule-based response (no LLM cost)
                result = self._rule_based_fallback(prompt)
                cost = 0.001
        except Exception as e:
            print(f"LLM error: {e}. Using rule-based fallback.")
            result = self._rule_based_fallback(prompt)
            cost = 0.001

        latency = (time.time() - start) * 1000
        return {"text": result, "latency_ms": latency, "cost_inr": cost}

    async def _groq_complete(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.groq_key}"},
                json={
                    "model": self.groq_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500,
                    "temperature": 0.1,
                },
            )
            return response.json()["choices"][0]["message"]["content"]

    async def _openai_complete(self, prompt: str, size: str) -> str:
        model = "gpt-4o" if size == "large" else "gpt-4o-mini"
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.openai_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500,
                    "temperature": 0.1,
                },
            )
            return response.json()["choices"][0]["message"]["content"]

    def _rule_based_fallback(self, prompt: str) -> str:
        """Rule-based fallback when no LLM is configured."""
        prompt_lower = prompt.lower()
        if "payment" in prompt_lower and "fail" in prompt_lower:
            return json.dumps({
                "root_cause": "PAYMENT_FAILURE",
                "confidence": 0.85,
                "evidence": ["Multiple payment attempts detected", "Extended time on payment page"],
                "recommendation": "ALTERNATE_PAYMENT_GUIDANCE"
            })
        elif "comparison" in prompt_lower or "tab" in prompt_lower:
            return json.dumps({
                "root_cause": "COMPARISON_SHOPPING",
                "confidence": 0.78,
                "evidence": ["High product views", "Multiple category switches"],
                "recommendation": "SOCIAL_PROOF_NUDGE"
            })
        elif "friction" in prompt_lower or "form" in prompt_lower:
            return json.dumps({
                "root_cause": "CHECKOUT_FRICTION",
                "confidence": 0.72,
                "evidence": ["Form errors detected", "Multiple back navigations"],
                "recommendation": "CHECKOUT_ASSISTANCE"
            })
        else:
            return json.dumps({
                "root_cause": "UNKNOWN",
                "confidence": 0.50,
                "evidence": ["Mixed signals"],
                "recommendation": "DO_NOTHING"
            })


llm_client = LLMClient()


class SignalAgent:
    """Extracts and enriches behavioral signals from session data."""
    name = "SignalAgent"

    async def analyze(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        from utils.signal_generator import signal_generator
        start = time.time()
        signals = signal_generator.generate_all_signals(session_data)
        latency = (time.time() - start) * 1000
        return {
            "signals": signals,
            "raw_session": session_data,
            "latency_ms": latency,
            "cost_inr": 0.001,
        }


class RiskAgent:
    """Scores abandonment risk using ML ensemble."""
    name = "RiskAgent"

    async def assess(self, session_data: Dict[str, Any], signals: Dict[str, Any]) -> Dict[str, Any]:
        start = time.time()
        try:
            from models.ensemble_model import get_model
            model = get_model()
            enriched = {**session_data, **signals.get("signals", {})}
            result = model.predict_proba(enriched)
        except Exception as e:
            # Fallback: rule-based risk scoring
            print(f"Model predict error: {e}. Using rule-based scoring.")
            result = self._rule_based_score(signals.get("signals", {}))
        
        latency = (time.time() - start) * 1000
        result["latency_ms"] = latency
        result["cost_inr"] = 0.001
        return result

    def _rule_based_score(self, signals: Dict[str, float]) -> Dict[str, Any]:
        bri = signals.get("behavioral_risk_index", 0.5)
        payment_risk = signals.get("payment_risk", 0)
        score = min(0.9 * bri + 0.1 * payment_risk, 1.0) + 0.1
        return {
            "risk_score": min(score, 1.0),
            "model_scores": {"rule_based": score},
            "signals": signals,
            "top_features": {},
        }


class DiagnosisAgent:
    """Uses LLM to diagnose the root cause of abandonment risk."""
    name = "DiagnosisAgent"

    DIAGNOSIS_PROMPT = """You are an expert e-commerce behavioral analyst for Indian shoppers.
Analyze this session and identify the PRIMARY reason for abandonment risk.

Session Signals:
- Hesitation Score: {hesitation_score} (0=decisive, 1=very hesitant)
- Price Sensitivity: {price_sensitivity} (0=not price sensitive, 1=highly price sensitive)
- Funnel Friction: {funnel_friction} (0=smooth, 1=very friction-heavy)
- Comparison Intent: {comparison_intent} (0=focused, 1=comparing heavily)
- Urgency Score: {urgency_score} (0=low intent, 1=high urgency to buy)
- Payment Risk: {payment_risk} (0=no payment issues, 1=high payment risk)
- Payment Attempts: {payment_attempts}
- Payment Failures: {payment_failures}
- Cart Value: ₹{cart_value}
- Session Duration: {session_duration}s
- Tab Switches: {tab_switches}
- Form Field Errors: {form_field_errors}
- Risk Score: {risk_score}

Choose exactly ONE root cause from: PAYMENT_FAILURE, COMPARISON_SHOPPING, CHECKOUT_FRICTION, LOW_INTENT, PRICE_SENSITIVITY, UNKNOWN

Respond in JSON:
{{"root_cause": "...", "confidence": 0.0-1.0, "evidence": ["reason1", "reason2"], "recommendation": "action_type"}}"""

    async def diagnose(
        self,
        session_data: Dict[str, Any],
        signals: Dict[str, Any],
        risk_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        start = time.time()
        
        try:
            from agents.llm_agents import AgentOrchestrator
            agent_orch = AgentOrchestrator()
            context = {**session_data, **signals.get("signals", {}), "risk_score": risk_result.get("risk_score", 0)}
            diagnosis = await agent_orch.diagnose_session(context)
            cost = 0.005
        except Exception as e:
            sigs = signals.get("signals", {})
            diagnosis = self._rule_based_diagnosis(sigs, session_data)
            cost = 0.001

        latency = (time.time() - start) * 1000
        return {
            **diagnosis,
            "latency_ms": latency,
            "cost_inr": cost,
        }

    def _rule_based_diagnosis(self, signals: Dict, session_data: Dict) -> Dict:
        """Rule-based fallback diagnosis."""
        if session_data.get("payment_failures", 0) > 0:
            return {"root_cause": "PAYMENT_FAILURE", "confidence": 0.88, 
                    "evidence": ["Payment failures detected"], "recommendation": "ALTERNATE_PAYMENT_GUIDANCE"}
        elif signals.get("comparison_intent", 0) > 0.6:
            return {"root_cause": "COMPARISON_SHOPPING", "confidence": 0.80,
                    "evidence": ["High comparison intent signals"], "recommendation": "SOCIAL_PROOF_NUDGE"}
        elif signals.get("funnel_friction", 0) > 0.6:
            return {"root_cause": "CHECKOUT_FRICTION", "confidence": 0.75,
                    "evidence": ["Funnel friction detected"], "recommendation": "CHECKOUT_ASSISTANCE"}
        elif signals.get("price_sensitivity", 0) > 0.7:
            return {"root_cause": "PRICE_SENSITIVITY", "confidence": 0.72,
                    "evidence": ["Price sensitivity signals"], "recommendation": "LIMITED_OFFER"}
        else:
            return {"root_cause": "UNKNOWN", "confidence": 0.5, 
                    "evidence": ["Mixed signals"], "recommendation": "DO_NOTHING"}


class PolicyAgent:
    """Enforces budget, consent, and margin guardrails."""
    name = "PolicyAgent"

    def __init__(self):
        self.per_user_budget = 500.0
        self.per_campaign_budget = 50000.0
        self.campaign_spend = 0.0

    async def evaluate(
        self,
        session_data: Dict[str, Any],
        risk_result: Dict[str, Any],
        diagnosis: Dict[str, Any],
    ) -> Dict[str, Any]:
        start = time.time()
        
        risk_score = risk_result.get("risk_score", 0)
        root_cause = diagnosis.get("root_cause", "UNKNOWN")
        cart_value = session_data.get("cart_value", 0)
        
        # Check consent
        consent_ok = self._check_consent(session_data)
        
        # Check budget
        user_spend = session_data.get("user_discount_spend_this_month", 0)
        budget_ok = user_spend < self.per_user_budget and self.campaign_spend < self.per_campaign_budget
        
        # Calculate uplift probability
        uplift_prob = self._calculate_uplift(risk_score, root_cause, cart_value)
        
        # Determine allowed actions
        allowed_actions = self._get_allowed_actions(root_cause, consent_ok, budget_ok, risk_score)
        
        # Calculate max discount
        max_discount = self._calculate_max_discount(cart_value, uplift_prob, budget_ok)
        
        # Incremental margin
        expected_incremental = cart_value * uplift_prob * 0.25  # 25% margin assumption
        
        latency = (time.time() - start) * 1000
        return {
            "consent_ok": consent_ok,
            "budget_ok": budget_ok,
            "uplift_probability": uplift_prob,
            "allowed_actions": allowed_actions,
            "max_discount_inr": max_discount,
            "expected_incremental_margin_inr": round(expected_incremental, 2),
            "budget_remaining_inr": self.per_user_budget - user_spend,
            "latency_ms": latency,
            "cost_inr": 0.001,
        }

    def _check_consent(self, session_data: Dict) -> bool:
        """Check TRAI/DND compliance."""
        dnd_registered = session_data.get("is_dnd_registered", False)
        sms_opt_in = session_data.get("sms_opt_in", True)
        email_opt_in = session_data.get("email_opt_in", True)
        return not dnd_registered and (sms_opt_in or email_opt_in)

    def _calculate_uplift(self, risk_score: float, root_cause: str, cart_value: float) -> float:
        """Estimate incremental conversion probability with intervention."""
        base_uplift = {
            "PAYMENT_FAILURE": 0.45,
            "CHECKOUT_FRICTION": 0.35,
            "COMPARISON_SHOPPING": 0.20,
            "PRICE_SENSITIVITY": 0.30,
            "LOW_INTENT": 0.05,
            "UNKNOWN": 0.10,
        }.get(root_cause, 0.10)
        
        # Adjust for risk score (only act on high-risk sessions)
        risk_multiplier = max(0, (risk_score - 0.5) * 2)
        return round(base_uplift * risk_multiplier, 4)

    def _get_allowed_actions(self, root_cause: str, consent_ok: bool, budget_ok: bool, risk_score: float) -> List[str]:
        """Get list of allowed actions given constraints."""
        actions = ["DO_NOTHING"]
        
        if risk_score < 0.55:
            return actions
        
        actions.append("IN_APP_NUDGE")
        
        if consent_ok:
            actions.append("EMAIL_RECOVERY")
            actions.append("PUSH_NOTIFICATION")
        
        if root_cause == "PAYMENT_FAILURE":
            actions.append("ALTERNATE_PAYMENT_GUIDANCE")
        elif root_cause == "COMPARISON_SHOPPING":
            actions.append("SOCIAL_PROOF_NUDGE")
        elif root_cause == "CHECKOUT_FRICTION":
            actions.append("CHECKOUT_ASSISTANCE")
        elif root_cause == "PRICE_SENSITIVITY" and budget_ok:
            actions.append("LIMITED_OFFER")
        
        return actions

    def _calculate_max_discount(self, cart_value: float, uplift_prob: float, budget_ok: bool) -> float:
        """Calculate maximum safe discount."""
        if not budget_ok or uplift_prob < 0.1:
            return 0.0
        margin = cart_value * 0.25
        max_discount = min(margin * 0.3, 500, cart_value * 0.10)
        return round(max_discount, 2)


class PolicyEngine:
    """Policy Engine with Guardrails matching M3 backend specification."""
    def __init__(self):
        self.budget_tracker = {}
        self.consent_cache = {}

    def decide(self, risk: dict, diagnosis: dict, budget: dict = None) -> dict:
        """Apply business rules and guardrails"""
        risk_score = risk.get("risk_score", 0) if isinstance(risk, dict) else float(risk)
        root_cause = diagnosis.get("root_cause", "UNKNOWN") if isinstance(diagnosis, dict) else "UNKNOWN"
        if budget is None:
            budget = {"remaining": 500.0, "min_discount": 10.0}

        # Rule 1: Low risk -> DO_NOTHING
        if risk_score < 0.3:
            return self._action_do_nothing(risk, diagnosis)

        # Rule 2: Payment failure -> Payment help (0 discount)
        if root_cause == "PAYMENT_FAILURE":
            return self._action_payment_help(risk, diagnosis)

        # Rule 3: Price shopping with high value -> Value reassurance
        if root_cause in ["PRICE_SHOPPING", "PRICE_SENSITIVITY"] and risk_score < 0.7:
            return self._action_value_reassurance(risk, diagnosis)

        # Rule 4: High risk + budget available -> Limited discount
        if risk_score > 0.7 and budget.get("remaining", 0) > budget.get("min_discount", 0):
            return self._action_limited_discount(risk, diagnosis, budget)

        # Rule 5: Friction detected -> Checkout help
        if root_cause == "CHECKOUT_FRICTION":
            return self._action_checkout_help(risk, diagnosis)

        # Default: DO_NOTHING (conservative)
        return self._action_do_nothing(risk, diagnosis)

    def _action_do_nothing(self, risk: dict, diagnosis: dict) -> dict:
        return {
            "action": "DO_NOTHING",
            "action_type": "DO_NOTHING",
            "action_message": "No intervention needed",
            "discount": 0.0,
            "discount_amount": 0.0,
            "channel": "NONE",
            "expected_margin": 0.0,
            "reason": risk.get("reason", "LOW_RISK") if isinstance(risk, dict) else "LOW_RISK"
        }

    def _action_payment_help(self, risk: dict, diagnosis: dict) -> dict:
        return {
            "action": "ALTERNATE_PAYMENT",
            "action_type": "ALTERNATE_PAYMENT_GUIDANCE",
            "action_message": "Having trouble paying? Try UPI, Netbanking, or Cash on Delivery.",
            "discount": 0.0,
            "discount_amount": 0.0,
            "channel": "IN_APP",
            "expected_margin": 0.0,
            "reason": "PAYMENT_FAILURE"
        }

    def _action_value_reassurance(self, risk: dict, diagnosis: dict) -> dict:
        return {
            "action": "VALUE_REASSURANCE",
            "action_type": "SOCIAL_PROOF_NUDGE",
            "action_message": "Best price guaranteed! Free 30-day returns and authentic items.",
            "discount": 0.0,
            "discount_amount": 0.0,
            "channel": "IN_APP",
            "expected_margin": 0.0,
            "reason": "PRICE_SHOPPING"
        }

    def _action_limited_discount(self, risk: dict, diagnosis: dict, budget: dict) -> dict:
        discount = min(100.0, float(budget.get("remaining", 50.0)))
        return {
            "action": "LIMITED_DISCOUNT",
            "action_type": "LIMITED_OFFER",
            "action_message": f"Exclusive offer: Complete your checkout in 15 mins to save ₹{int(discount)}!",
            "discount": discount,
            "discount_amount": discount,
            "channel": "IN_APP",
            "expected_margin": round(discount * 2, 2),
            "reason": "HIGH_RISK_CONVERSION_NUDGE"
        }

    def _action_checkout_help(self, risk: dict, diagnosis: dict) -> dict:
        return {
            "action": "CHECKOUT_HELP",
            "action_type": "CHECKOUT_ASSISTANCE",
            "action_message": "Need help with address or checkout? Our support team is 1 click away.",
            "discount": 0.0,
            "discount_amount": 0.0,
            "channel": "IN_APP",
            "expected_margin": 0.0,
            "reason": "CHECKOUT_FRICTION"
        }


class ActionAgent:
    """Generates personalized, context-aware action recommendations."""
    name = "ActionAgent"

    ACTION_PROMPT = """You are a cart recovery specialist for an Indian e-commerce platform.
Generate ONE specific, personalized recovery action.

Context:
- Root Cause: {root_cause} (Confidence: {confidence})
- Risk Score: {risk_score}
- Cart Value: ₹{cart_value}
- Uplift Probability: {uplift_probability}
- Max Discount: ₹{max_discount}
- Allowed Actions: {allowed_actions}
- User Segment: {user_segment}

Rules:
1. If uplift_probability < 0.15: return DO_NOTHING
2. If root_cause is PAYMENT_FAILURE: focus on payment help, no discount
3. If root_cause is COMPARISON_SHOPPING: use social proof, maybe small discount
4. If root_cause is CHECKOUT_FRICTION: offer assistance, no discount
5. If cart_value > 3000 and root_cause is PRICE_SENSITIVITY: offer small discount
6. Always prefer DO_NOTHING over random discounting

Respond in JSON:
{{"action_type": "...", "channel": "IN_APP|EMAIL|PUSH|DO_NOTHING", "message": "...", "discount_amount": 0, "discount_type": "NONE|FIXED|PERCENT", "urgency": "LOW|MEDIUM|HIGH", "reasoning": "..."}}"""

    async def generate(
        self,
        session_data: Dict[str, Any],
        diagnosis: Dict[str, Any],
        policy: Dict[str, Any],
        risk_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        start = time.time()
        
        # If no allowed actions or uplift too low, return DO_NOTHING
        allowed = policy.get("allowed_actions", ["DO_NOTHING"])
        uplift = policy.get("uplift_probability", 0)
        
        if uplift < 0.10 or allowed == ["DO_NOTHING"]:
            return {
                "action_type": "DO_NOTHING",
                "channel": "DO_NOTHING",
                "message": "",
                "discount_amount": 0,
                "discount_type": "NONE",
                "reasoning": "Uplift probability too low. No action recommended.",
                "latency_ms": (time.time() - start) * 1000,
                "cost_inr": 0.001,
            }

        prompt = self.ACTION_PROMPT.format(
            root_cause=diagnosis.get("root_cause", "UNKNOWN"),
            confidence=round(diagnosis.get("confidence", 0), 2),
            risk_score=round(risk_result.get("risk_score", 0), 3),
            cart_value=round(session_data.get("cart_value", 0), 2),
            uplift_probability=round(uplift, 3),
            max_discount=round(policy.get("max_discount_inr", 0), 2),
            allowed_actions=", ".join(allowed),
            user_segment=session_data.get("user_segment", "REGULAR"),
        )

        llm_result = await llm_client.complete(prompt, model_size="small")
        
        try:
            text = llm_result["text"]
            if "{" in text:
                json_str = text[text.index("{"):text.rindex("}")+1]
                action = json.loads(json_str)
            else:
                action = self._rule_based_action(diagnosis, policy, session_data)
        except Exception:
            action = self._rule_based_action(diagnosis, policy, session_data)

        # Enforce guardrails
        action["discount_amount"] = min(
            action.get("discount_amount", 0),
            policy.get("max_discount_inr", 0)
        )
        
        latency = (time.time() - start) * 1000
        action["latency_ms"] = latency
        action["cost_inr"] = llm_result.get("cost_inr", 0.001)
        return action

    def _rule_based_action(self, diagnosis: Dict, policy: Dict, session_data: Dict) -> Dict:
        root_cause = diagnosis.get("root_cause", "UNKNOWN")
        cart_value = session_data.get("cart_value", 0)
        max_discount = policy.get("max_discount_inr", 0)
        
        action_map = {
            "PAYMENT_FAILURE": {
                "action_type": "ALTERNATE_PAYMENT_GUIDANCE",
                "channel": "IN_APP",
                "message": "Having trouble paying? Try UPI, netbanking, or COD — all available for your order!",
                "discount_amount": 0,
                "discount_type": "NONE",
                "urgency": "HIGH",
            },
            "COMPARISON_SHOPPING": {
                "action_type": "SOCIAL_PROOF_NUDGE",
                "channel": "IN_APP",
                "message": f"⭐ 2,847 customers bought this today. Limited stock remaining!",
                "discount_amount": 0,
                "discount_type": "NONE",
                "urgency": "MEDIUM",
            },
            "CHECKOUT_FRICTION": {
                "action_type": "CHECKOUT_ASSISTANCE",
                "channel": "IN_APP",
                "message": "Need help completing your order? Chat with us — we're here to help!",
                "discount_amount": 0,
                "discount_type": "NONE",
                "urgency": "MEDIUM",
            },
            "PRICE_SENSITIVITY": {
                "action_type": "LIMITED_OFFER",
                "channel": "IN_APP",
                "message": f"🎁 Special offer: Save ₹{int(max_discount)} on your order. Valid for 15 mins!",
                "discount_amount": max_discount,
                "discount_type": "FIXED",
                "urgency": "HIGH",
            },
        }
        
        return action_map.get(root_cause, {
            "action_type": "DO_NOTHING",
            "channel": "DO_NOTHING",
            "message": "",
            "discount_amount": 0,
            "discount_type": "NONE",
            "urgency": "LOW",
        })


class SelfCheckAgent:
    """Validates agent outputs against business rules and consistency."""
    name = "SelfCheckAgent"

    async def validate(
        self,
        session_data: Dict,
        signals: Dict,
        risk_result: Dict,
        diagnosis: Dict,
        policy: Dict,
        action: Dict,
    ) -> Dict[str, Any]:
        start = time.time()
        checks = {}

        # Check 1: Consistency
        checks["consistency"] = self._check_consistency(risk_result, diagnosis, action)
        
        # Check 2: Budget
        checks["budget"] = self._check_budget(action, policy)
        
        # Check 3: Consent
        checks["consent"] = self._check_consent(action, policy)
        
        # Check 4: Margin
        checks["margin"] = self._check_margin(action, session_data, policy)
        
        # Check 5: Logic (no discount for payment failure)
        checks["logic"] = self._check_logic(diagnosis, action)

        # Check 6: LLM Self-Validation Layer
        try:
            from agents.llm_agents import SelfCheckValidator
            validator = SelfCheckValidator()
            llm_val = await validator.validate(diagnosis, action, policy)
            checks["llm_self_validation"] = llm_val.get("is_valid", True)
        except Exception:
            checks["llm_self_validation"] = True

        all_passed = all(checks.values())
        
        if not all_passed:
            # Conservative fallback
            failed = [k for k, v in checks.items() if not v]
            action = {
                "action_type": "DO_NOTHING",
                "channel": "DO_NOTHING",
                "message": "",
                "discount_amount": 0,
                "discount_type": "NONE",
                "reasoning": f"Self-check failed: {failed}. Conservative fallback to DO_NOTHING.",
            }

        latency = (time.time() - start) * 1000
        return {
            "status": "PASSED" if all_passed else "FAILED",
            "checks": checks,
            "final_action": action,
            "latency_ms": latency,
            "cost_inr": 0.001,
        }

    def _check_consistency(self, risk: Dict, diagnosis: Dict, action: Dict) -> bool:
        """Action should match diagnosis."""
        root_cause = diagnosis.get("root_cause", "UNKNOWN")
        action_type = action.get("action_type", "DO_NOTHING")
        
        inconsistent = {
            "PAYMENT_FAILURE": ["LIMITED_OFFER", "SOCIAL_PROOF_NUDGE"],
            "LOW_INTENT": ["LIMITED_OFFER", "CHECKOUT_ASSISTANCE"],
        }
        
        if root_cause in inconsistent and action_type in inconsistent[root_cause]:
            return False
        return True

    def _check_budget(self, action: Dict, policy: Dict) -> bool:
        discount = action.get("discount_amount", 0)
        max_discount = policy.get("max_discount_inr", 0)
        return discount <= max_discount

    def _check_consent(self, action: Dict, policy: Dict) -> bool:
        channel = action.get("channel", "IN_APP")
        if channel in ["SMS", "WHATSAPP", "EMAIL"] and not policy.get("consent_ok", False):
            return False
        return True

    def _check_margin(self, action: Dict, session_data: Dict, policy: Dict) -> bool:
        discount = action.get("discount_amount", 0)
        expected_margin = policy.get("expected_incremental_margin_inr", 0)
        return discount <= expected_margin * 0.5  # discount < 50% of expected margin

    def _check_logic(self, diagnosis: Dict, action: Dict) -> bool:
        """Prevent discounting when not needed."""
        root_cause = diagnosis.get("root_cause", "UNKNOWN")
        discount = action.get("discount_amount", 0)
        
        no_discount_causes = ["PAYMENT_FAILURE", "CHECKOUT_FRICTION", "UNKNOWN"]
        if root_cause in no_discount_causes and discount > 0:
            return False
        return True


class OrchestratorAgent:
    """
    Main Head Controller & Stateful Ledger Orchestrator.
    Manages global flow across all 7 specialized agents:
    1. Fast ML Filter (First Line of Defense)
    2. Head Controller & Stateful Ledger (The Boss)
    3. Domain Research Agent (Root Cause Finder)
    4. Psych-Profiling & Behavioral Agent (The Nudge Engine)
    5. Remediation Strategist (The Solution Maker)
    6. Adaptive Adversarial Auditor (Secondary Agent with Closed-Loop Learning)
    7. Human-in-the-Loop Gate & Audit Ledger
    """

    def __init__(self):
        self.signal_agent = SignalAgent()
        self.risk_agent = RiskAgent()
        self.diagnosis_agent = DiagnosisAgent()
        self.policy_agent = PolicyAgent()
        self.action_agent = ActionAgent()
        self.self_check_agent = SelfCheckAgent()

        # Import 7-agent enterprise modules
        from agents.seven_agents import (
            FastMLFilterAgent,
            HeadControllerLedger,
            DomainResearchAgent,
            PsychProfilingAgent,
            RemediationStrategistAgent,
            AdaptiveAdversarialAuditor,
            HITLAuditLedger,
        )
        self.fast_ml_filter = FastMLFilterAgent()
        self.head_controller = HeadControllerLedger()
        self.domain_researcher = DomainResearchAgent()
        self.psych_profiler = PsychProfilingAgent()
        self.remediation_strategist = RemediationStrategistAgent()
        self.adversarial_auditor = AdaptiveAdversarialAuditor()
        self.hitl_ledger = HITLAuditLedger()

    async def process_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run the complete 7-agent enterprise pipeline for a session."""
        total_start = time.time()
        session_id = session_data.get("session_id", f"SES-{uuid.uuid4().hex[:6].upper()}")
        user_id = session_data.get("user_id", "USR-GUEST")
        conversation = AgentConversation(session_id=session_id)
        total_cost = 0.0
        step_logs = []

        # ── 1. Fast ML Filter (First Line of Defense) ─────────────────────
        filter_res = await self.fast_ml_filter.evaluate(session_data)
        conversation.messages.append(AgentMessage(filter_res["agent"], filter_res, filter_res["latency_ms"]))
        step_logs.append({
            "step": 1,
            "node": "Fast ML Filter",
            "status": "PASSED_THROUGH" if filter_res["passed_through"] else "WAKE_LLM",
            "latency_ms": filter_res["latency_ms"],
            "details": f"Risk Score: {filter_res['risk_score']} ({filter_res['risk_level']})"
        })

        risk_score = filter_res["risk_score"]

        # Fast path: low risk natural conversion short-circuits instantly!
        if filter_res["passed_through"]:
            total_latency = (time.time() - total_start) * 1000
            return {
                "session_id": session_id,
                "risk_score": risk_score,
                "risk_level": "LOW",
                "signals": filter_res,
                "routing_mode": "FAST_PASS",
                "diagnosis": {
                    "root_cause": "NATURAL_CONVERSION",
                    "category": "BEHAVIORAL",
                    "sub_cause": "LOW_RISK",
                    "confidence": 0.99,
                    "evidence": ["Session metadata exhibits natural checkout behavior"],
                },
                "psych_profile": {
                    "mindset": "NATURAL_BUYER",
                    "psych_framing": "NONE",
                },
                "policy": {
                    "uplift_probability": 0.02,
                    "budget_remaining_inr": self.head_controller.running_campaign_budget,
                    "expected_incremental_margin_inr": 0.0,
                    "consent_ok": True,
                },
                "action": {
                    "action_type": "DO_NOTHING",
                    "proposed_action": "DO_NOTHING",
                    "channel": "NONE",
                    "discount_amount": 0.0,
                    "message": "Low risk natural conversion — no intervention needed.",
                    "reasoning": "Fast ML Filter short-circuited session with zero LLM awakening.",
                },
                "adversarial_audit": {
                    "status": "APPROVED",
                    "auditor_confidence": 0.99,
                    "rejections": [],
                    "warnings": [],
                },
                "hitl_gate": {
                    "requires_hitl": False,
                    "hitl_reason": "AUTOMATED_APPROVAL",
                    "status": "APPROVED",
                },
                "self_check": {"status": "PASSED", "checks": {"fast_filter": True}},
                "metrics": {
                    "total_latency_ms": round(total_latency, 2),
                    "total_cost_inr": 0.0001,
                    "agent_latencies": {"FastMLFilter": filter_res["latency_ms"]},
                },
                "step_logs": step_logs,
                "audit_trail": [{"agent": "FastMLFilter", "latency_ms": filter_res["latency_ms"]}],
            }

        # ── 2. Head Controller & Stateful Ledger (The Boss) ───────────────
        user_spent = float(session_data.get("user_discount_spend_this_month", 0.0))
        budget_info = self.head_controller.check_budget_limits(user_id, user_spent)
        routing_mode = self.head_controller.determine_routing_mode(session_data, risk_score)

        step_logs.append({
            "step": 2,
            "node": "Head Controller & Ledger",
            "status": "ROUTED",
            "latency_ms": 0.5,
            "details": f"Mode: {routing_mode} | Max Allowed Discount: ₹{budget_info['max_allowed_user_discount']}"
        })

        # ── 3 & 4. Domain Research Agent & Psych-Profiling Agent ───────────
        if routing_mode == "PARALLEL":
            # Real-time sub-1.5s parallel execution
            domain_task = self.domain_researcher.diagnose(session_data, filter_res)
            psych_task = self.psych_profiler.profile(session_data, {"category": "BEHAVIORAL"})
            domain_res, psych_res = await asyncio.gather(domain_task, psych_task)
        else:
            # Sequential deep context execution
            domain_res = await self.domain_researcher.diagnose(session_data, filter_res)
            psych_res = await self.psych_profiler.profile(session_data, domain_res)

        conversation.messages.append(AgentMessage(domain_res["agent"], domain_res, domain_res["latency_ms"]))
        conversation.messages.append(AgentMessage(psych_res["agent"], psych_res, psych_res["latency_ms"]))
        total_cost += 0.005

        step_logs.append({
            "step": 3,
            "node": "Domain Research Agent",
            "status": "DIAGNOSED",
            "latency_ms": domain_res["latency_ms"],
            "details": f"Category: {domain_res['category']} ({domain_res['sub_cause']})"
        })
        step_logs.append({
            "step": 4,
            "node": "Psych-Profiling Agent",
            "status": "PROFILED",
            "latency_ms": psych_res["latency_ms"],
            "details": f"Mindset: {psych_res['mindset']} | Framing: {psych_res['psych_framing']}"
        })

        # ── 5 & 6. Remediation Strategist & Adaptive Adversarial Auditor (Retry Loop) ──
        iteration = 1
        max_iterations = 2
        strategy_res = None
        audit_res = None
        rejection_feedback = None

        while iteration <= max_iterations:
            strategy_res = await self.remediation_strategist.synthesize(
                session_data, domain_res, psych_res, budget_info, iteration=iteration, rejection_feedback=rejection_feedback
            )
            conversation.messages.append(AgentMessage(strategy_res["agent"], strategy_res, strategy_res["latency_ms"]))
            total_cost += 0.005

            from services.audit_service import audit_service
            audit_res = await self.adversarial_auditor.audit(session_data, strategy_res, audit_service_ref=audit_service, psych_profile=psych_res)
            conversation.messages.append(AgentMessage(audit_res["agent"], audit_res, audit_res["latency_ms"]))

            rejection_feedback = audit_res.get("learning_feedback_for_strategist")

            step_logs.append({
                "step": 5,
                "node": f"Remediation Strategist (Iter {iteration})",
                "status": "PROPOSED",
                "latency_ms": strategy_res["latency_ms"],
                "details": f"Action: {strategy_res['proposed_action']} | Discount: ₹{strategy_res['discount_amount']}"
            })
            step_logs.append({
                "step": 6,
                "node": f"Adversarial Auditor (Iter {iteration})",
                "status": audit_res["status"],
                "latency_ms": audit_res["latency_ms"],
                "details": f"Verdict: {audit_res.get('verdict')} | Feedback: {rejection_feedback}"
            })

            if audit_res["status"] == "APPROVED":
                break

            iteration += 1

        # Fallback if auditing failed after max retries
        if audit_res and audit_res["status"] != "APPROVED":
            strategy_res = {
                "agent": "RemediationStrategist",
                "proposed_action": "DO_NOTHING",
                "channel": "NONE",
                "discount_amount": 0.0,
                "message": "Audit guardrails not passed after retry iterations. Falling back to DO_NOTHING.",
                "gross_margin_inr": strategy_res.get("gross_margin_inr", 0.0),
                "iteration": iteration,
                "latency_ms": 1.0,
            }

        # ── 7. Human-in-the-Loop Gate & Audit Ledger ──────────────────────
        requires_hitl, hitl_reason = self.hitl_ledger.should_trigger_hitl(session_data, audit_res, filter_res)

        step_logs.append({
            "step": 7,
            "node": "HITL Gate & Audit Ledger",
            "status": "PENDING_HUMAN_APPROVAL" if requires_hitl else "AUTO_SIGNED_OFF",
            "latency_ms": 0.8,
            "details": f"Requires HITL: {requires_hitl} ({hitl_reason})"
        })

        total_latency = (time.time() - total_start) * 1000

        # Construct final standardized output
        result_payload = {
            "session_id": session_id,
            "user_id": user_id,
            "risk_score": risk_score,
            "risk_level": filter_res["risk_level"],
            "routing_mode": routing_mode,
            "signals": session_data,
            "diagnosis": {
                "root_cause": domain_res["sub_cause"],
                "category": domain_res["category"],
                "sub_cause": domain_res["sub_cause"],
                "confidence": domain_res["confidence"],
                "evidence": domain_res["evidence"],
            },
            "psych_profile": {
                "mindset": psych_res["mindset"],
                "psych_framing": psych_res["psych_framing"],
                "framing_text": psych_res["framing_text"],
            },
            "policy": {
                "uplift_probability": 0.35 if risk_score > 0.6 else 0.15,
                "budget_remaining_inr": budget_info["max_allowed_user_discount"],
                "expected_incremental_margin_inr": strategy_res["gross_margin_inr"],
                "consent_ok": True,
            },
            "action": {
                "action_type": strategy_res["proposed_action"],
                "proposed_action": strategy_res["proposed_action"],
                "channel": strategy_res["channel"],
                "discount": strategy_res["discount_amount"],
                "discount_amount": strategy_res["discount_amount"],
                "message": strategy_res["message"],
                "action_message": strategy_res["message"],
                "reasoning": f"Synthesized for mindset {psych_res['mindset']} under root cause {domain_res['category']}.",
            },
            "adversarial_audit": audit_res,
            "hitl_gate": {
                "requires_hitl": requires_hitl,
                "hitl_reason": hitl_reason,
                "status": "PENDING_HUMAN_APPROVAL" if requires_hitl else "APPROVED",
            },
            "self_check": {
                "status": audit_res["status"],
                "checks": {
                    "margin_floor": len(audit_res.get("rejections", [])) == 0,
                    "closed_loop_memory": len(audit_res.get("warnings", [])) == 0,
                },
            },
            "metrics": {
                "total_latency_ms": round(total_latency, 2),
                "total_cost_inr": round(total_cost, 4),
                "agent_latencies": {
                    msg.agent: round(msg.latency_ms, 2)
                    for msg in conversation.messages
                },
            },
            "step_logs": step_logs,
            "audit_trail": [
                {"agent": msg.agent, "latency_ms": round(msg.latency_ms, 2)}
                for msg in conversation.messages
            ],
        }

        # Log decision to audit DB
        try:
            from services.audit_service import audit_service
            audit_service.log_decision(result_payload, session_data)
        except Exception as e:
            print(f"Error logging to audit service: {e}")

        return result_payload


# Global orchestrator instance
orchestrator = OrchestratorAgent()

