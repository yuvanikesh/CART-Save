"""
CartGuard AI - Specialized AI/LLM Agent System
Implements the 5 specialized reasoning agents, conversation flow, self-check validator,
caching layer, and fallback rules according to Member M2 technical specifications.
"""

import json
import time
import asyncio
from typing import Dict, Any, List, Optional

from agents.prompts import (
    PAYMENT_FAILURE_PROMPT,
    PRICE_SENSITIVITY_PROMPT,
    BEHAVIORAL_HESITATION_PROMPT,
    INTENT_RECOVERY_PROMPT,
    SELF_CHECK_VALIDATION_PROMPT,
)
from agents.caching import session_cache
from agents.fallback import fallback_engine


class CartGuardLLMAgent:
    """Base LLM Agent with chain-of-thought reasoning capabilities."""

    def __init__(self, agent_name: str = "BaseLLMAgent", model_path: Optional[str] = None):
        self.agent_name = agent_name
        self.model_path = model_path
        self.cache = session_cache
        self.messages: List[Dict[str, Any]] = []

    async def reason_async(self, context: Dict[str, Any], prompt_template: str, model_size: str = "small") -> Dict[str, Any]:
        """Execute chain-of-thought reasoning with caching and fallback handling.

        model_size: 'small' (cheap/fast, e.g. gpt-4o-mini) for routine per-agent
        classification calls; 'large' (gpt-4o) reserved for genuinely ambiguous
        cases escalated by the caller (e.g. SelfCheckValidator on borderline confidence).
        """
        start_time = time.time()

        # Step 1: Check cache first (80% hit target)
        cached = self.cache.get(context, self.agent_name)
        if cached:
            cached["latency_ms"] = round((time.time() - start_time) * 1000, 2)
            return cached

        # Step 2: Render prompt
        try:
            prompt = self._render_prompt(prompt_template, context)
        except KeyError as e:
            # Missing context field fallback
            return self._execute_fallback(context)

        # Step 3: LLM Execution or Rule-Based Fallback
        try:
            from agents.orchestrator import llm_client
            llm_res = await llm_client.complete(prompt, model_size=model_size)
            text = llm_res.get("text", "")
            result = self._parse_response(text)
        except Exception:
            result = self._execute_fallback(context)

        # Step 4: Cache result and add latency
        result["latency_ms"] = round((time.time() - start_time) * 1000, 2)
        self.cache.set(context, self.agent_name, result)
        return result

    def reason(self, context: Dict[str, Any], prompt_template: str) -> Dict[str, Any]:
        """Synchronous wrapper for reasoning execution."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If event loop is already running, run inline or fallback safely
                return self._execute_fallback(context)
            return loop.run_until_complete(self.reason_async(context, prompt_template))
        except Exception:
            return self._execute_fallback(context)

    def _render_prompt(self, template: str, context: Dict[str, Any]) -> str:
        """Safely format prompt template with context defaults."""
        defaults = {
            "payment_attempts": context.get("payment_attempts", 0),
            "payment_failures": context.get("payment_failures", 0),
            "time_on_payment": context.get("time_on_payment_page", context.get("time_on_payment", 0)),
            "session_duration": context.get("session_duration", 0),
            "cart_value": context.get("cart_value", 0),
            "checkout_stage": context.get("checkout_steps_completed", context.get("checkout_steps", 1)),
            "form_field_errors": context.get("form_field_errors", 0),
            "product_views": context.get("product_views", 0),
            "unique_categories": context.get("category_switches", 1),
            "cart_adds": context.get("cart_adds", 0),
            "cart_removals": context.get("cart_removes", context.get("cart_removals", 0)),
            "cart_value_changes": context.get("cart_changes", 0),
            "tab_loss_count": context.get("tab_switches", context.get("tab_loss_count", 0)),
            "checkout_steps": context.get("checkout_steps_completed", 1),
            "time_per_step": round(context.get("session_duration", 0) / max(1, context.get("checkout_steps_completed", 1)), 1),
            "scroll_speed": 120,
            "form_interactions": context.get("form_field_errors", 0) + 1,
            "abandoned_fields": context.get("form_field_errors", 0),
            "mouse_velocity": 0.5,
            "hesitation_score": context.get("hesitation_score", 0.0),
            "user_segment": context.get("user_segment", "REGULAR"),
            "is_returning_visitor": context.get("is_returning_visitor", False),
            "risk_score": context.get("risk_score", 0.5),
            "primary_diagnosis": context.get("primary_diagnosis", "UNKNOWN"),
            "max_budget": context.get("max_budget", 500),
            "root_cause": context.get("root_cause", "UNKNOWN"),
            "confidence": context.get("confidence", 0.5),
            "action": context.get("action", "DO_NOTHING"),
            "discount_amount": context.get("discount_amount", 0),
            "max_allowed_discount": context.get("max_allowed_discount", 0),
            "channel": context.get("channel", "IN_APP"),
            "consent_ok": context.get("consent_ok", True),
            "budget_ok": context.get("budget_ok", True),
        }
        return template.format(**defaults)

    def _parse_response(self, text: str) -> Dict[str, Any]:
        """Extract structured JSON from LLM thinking chain output."""
        if "</thinking>" in text:
            text = text.split("</thinking>")[-1]

        if "{" in text and "}" in text:
            json_str = text[text.index("{") : text.rindex("}") + 1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        return self._execute_fallback({})

    def _execute_fallback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Override in subclasses to provide domain-specific fallback logic."""
        return {"root_cause": "UNKNOWN", "confidence": 0.5, "is_fallback": True}


# ─── Specialized Reasoning Agents ───────────────────────────────

class PaymentFailureAnalyzer(CartGuardLLMAgent):
    """Specialized agent for payment failure diagnosis."""

    def __init__(self, model_path: Optional[str] = None):
        super().__init__(agent_name="PaymentFailureAnalyzer", model_path=model_path)
        self.PROMPT_TEMPLATE = PAYMENT_FAILURE_PROMPT

    async def diagnose(self, session: Dict[str, Any]) -> Dict[str, Any]:
        res = await self.reason_async(session, self.PROMPT_TEMPLATE)
        if "is_payment_failure" not in res:
            return fallback_engine.diagnose_payment(session)
        return res

    def _execute_fallback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return fallback_engine.diagnose_payment(context)


class PriceSensitivityAnalyzer(CartGuardLLMAgent):
    """Specialized agent for price shopping diagnosis."""

    def __init__(self, model_path: Optional[str] = None):
        super().__init__(agent_name="PriceSensitivityAnalyzer", model_path=model_path)
        self.PROMPT_TEMPLATE = PRICE_SENSITIVITY_PROMPT

    async def diagnose(self, session: Dict[str, Any]) -> Dict[str, Any]:
        res = await self.reason_async(session, self.PROMPT_TEMPLATE)
        if "is_price_sensitive" not in res:
            return fallback_engine.diagnose_price(session)
        return res

    def _execute_fallback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return fallback_engine.diagnose_price(context)


class BehavioralHesitationAnalyzer(CartGuardLLMAgent):
    """Specialized agent for friction/hesitation diagnosis."""

    def __init__(self, model_path: Optional[str] = None):
        super().__init__(agent_name="BehavioralHesitationAnalyzer", model_path=model_path)
        self.PROMPT_TEMPLATE = BEHAVIORAL_HESITATION_PROMPT

    async def diagnose(self, session: Dict[str, Any]) -> Dict[str, Any]:
        res = await self.reason_async(session, self.PROMPT_TEMPLATE)
        if "friction_score" not in res:
            return fallback_engine.diagnose_hesitation(session)
        return res

    def _execute_fallback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return fallback_engine.diagnose_hesitation(context)


class IntentRecoveryAnalyzer(CartGuardLLMAgent):
    """Specialized agent for purchase intent and bargain recovery diagnosis."""

    def __init__(self, model_path: Optional[str] = None):
        super().__init__(agent_name="IntentRecoveryAnalyzer", model_path=model_path)
        self.PROMPT_TEMPLATE = INTENT_RECOVERY_PROMPT

    async def diagnose(self, session: Dict[str, Any]) -> Dict[str, Any]:
        res = await self.reason_async(session, self.PROMPT_TEMPLATE)
        if "intent_level" not in res:
            return fallback_engine.diagnose_intent(session)
        return res

    def _execute_fallback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return fallback_engine.diagnose_intent(context)


class SelfCheckValidator(CartGuardLLMAgent):
    """Specialized LLM self-validation guardrail layer."""

    def __init__(self, model_path: Optional[str] = None):
        super().__init__(agent_name="SelfCheckValidator", model_path=model_path)
        self.PROMPT_TEMPLATE = SELF_CHECK_VALIDATION_PROMPT

    async def validate(self, diagnosis: Dict[str, Any], action: Dict[str, Any], policy: Dict[str, Any]) -> Dict[str, Any]:
        context = {**diagnosis, **action, **policy}

        # Two-tier model routing: only pay for the expensive model when the
        # diagnosis confidence is genuinely borderline (0.45-0.65). Clear-cut
        # high/low confidence cases stay on the cheap/fast model.
        confidence = diagnosis.get("confidence", 0.5)
        model_size = "large" if 0.45 <= confidence <= 0.65 else "small"

        res = await self.reason_async(context, self.PROMPT_TEMPLATE, model_size=model_size)
        res["escalated_to_large_model"] = (model_size == "large")
        if "is_valid" not in res:
            return fallback_engine.validate_self_check(diagnosis, action, policy)
        return res

    def _execute_fallback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return fallback_engine.validate_self_check(context, context, context)


# ─── Master Agent Orchestrator ──────────────────────────────────

class AgentOrchestrator:
    """Coordinates all specialized reasoning agents and synthesizes final diagnosis."""

    def __init__(self, model_path: Optional[str] = None):
        self.agents = {
            "payment": PaymentFailureAnalyzer(model_path),
            "price": PriceSensitivityAnalyzer(model_path),
            "hesitation": BehavioralHesitationAnalyzer(model_path),
            "intent": IntentRecoveryAnalyzer(model_path),
        }
        self.self_check = SelfCheckValidator(model_path)
        self.conversation_history: List[Dict[str, Any]] = []

    async def diagnose_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run all specialized agents in parallel and synthesize results."""
        start_time = time.time()

        # Step 1: Run specialized agents in parallel
        agent_tasks = {
            name: agent.diagnose(session_data) for name, agent in self.agents.items()
        }
        diagnoses = {}
        results = await asyncio.gather(*agent_tasks.values(), return_exceptions=True)

        for name, result in zip(agent_tasks.keys(), results):
            if isinstance(result, Exception):
                diagnoses[name] = self.agents[name]._execute_fallback(session_data)
            else:
                diagnoses[name] = result

            self.conversation_history.append({
                "agent": name,
                "input": session_data,
                "output": diagnoses[name],
                "timestamp": time.time(),
            })

        # Step 2: Synthesize final root cause diagnosis
        final = self.synthesize_diagnoses(diagnoses)
        final["latency_ms"] = round((time.time() - start_time) * 1000, 2)

        self.conversation_history.append({
            "agent": "orchestrator",
            "input": diagnoses,
            "output": final,
            "timestamp": time.time(),
        })

        return final

    def synthesize_diagnoses(self, diagnoses: Dict[str, Any]) -> Dict[str, Any]:
        """Weighted priority aggregation of specialized agent outputs."""
        pay = diagnoses.get("payment", {})
        price = diagnoses.get("price", {})
        hes = diagnoses.get("hesitation", {})
        intent = diagnoses.get("intent", {})

        # Priority 1: Payment Failure (Trumps all other diagnoses)
        if pay.get("is_payment_failure"):
            return {
                "root_cause": "PAYMENT_FAILURE",
                "confidence": pay.get("confidence", 0.9),
                "evidence": pay.get("evidence", ["Payment friction detected"]),
                "recommended_action": pay.get("recommended_action", "ALTERNATE_PAYMENT"),
                "agent_details": pay,
            }

        # Priority 2: Price Sensitivity with High Confidence
        if price.get("is_price_sensitive") and price.get("confidence", 0) > 0.6:
            return {
                "root_cause": "PRICE_SHOPPING",
                "confidence": price.get("confidence", 0.8),
                "evidence": price.get("evidence", ["Price comparison signals detected"]),
                "recommended_action": price.get("recommended_action", "VALUE_REASSURANCE"),
                "agent_details": price,
            }

        # Priority 3: Friction / Hesitation with High Score
        if hes.get("friction_score", 0) >= 6:
            return {
                "root_cause": "CHECKOUT_FRICTION",
                "confidence": min(1.0, hes.get("friction_score", 6) / 10.0),
                "evidence": hes.get("evidence", ["Checkout hesitation detected"]),
                "recommended_action": hes.get("recommended_action", "CHECKOUT_HELP"),
                "agent_details": hes,
            }

        # Priority 4: High Purchase Intent Bargain Recovery
        if intent.get("intent_level") == "high":
            return {
                "root_cause": "INTENT_RECOVERY",
                "confidence": intent.get("confidence", 0.85),
                "evidence": intent.get("evidence", ["High purchase intent detected"]),
                "recommended_action": intent.get("recommended_action", "IN_APP_NUDGE"),
                "agent_details": intent,
            }

        # Default: LOW_RISK / UNKNOWN
        return {
            "root_cause": "UNKNOWN",
            "confidence": 0.5,
            "evidence": ["No high-confidence risk pattern detected"],
            "recommended_action": "DO_NOTHING",
            "agent_details": {},
        }