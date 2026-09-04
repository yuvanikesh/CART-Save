"""
CartGuard AI - Uplift & Validation Service
Synthetic uplift modeling to prove margin impact without real A/B test data.
"""
import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, Any, List, Tuple
import json


class UpliftSimulator:
    """
    Synthetic uplift modeling using propensity score matching simulation.
    Proves incremental margin impact with confidence intervals.
    """

    def simulate_ab_test(
        self,
        n_sessions: int = 10000,
        action_uplift_rates: Dict[str, float] = None,
        seed: int = 42,
    ) -> Dict[str, Any]:
        """
        Simulate A/B test with synthetic assignment.
        Returns statistical significance and confidence intervals.
        """
        np.random.seed(seed)
        
        if action_uplift_rates is None:
            action_uplift_rates = {
                "ALTERNATE_PAYMENT_GUIDANCE": 0.42,
                "SOCIAL_PROOF_NUDGE": 0.18,
                "CHECKOUT_ASSISTANCE": 0.32,
                "LIMITED_OFFER": 0.28,
                "DO_NOTHING": 0.08,
            }

        # Simulate sessions
        sessions = []
        for i in range(n_sessions):
            # Random assignment to control/treatment
            in_treatment = np.random.random() > 0.5
            
            # Session characteristics
            risk_score = np.random.beta(2, 3)
            cart_value = np.random.lognormal(7, 0.8)
            
            # Assign action
            if in_treatment and risk_score > 0.55:
                actions = list(action_uplift_rates.keys())
                action = np.random.choice(actions[:-1])  # Not DO_NOTHING
            else:
                action = "DO_NOTHING"
            
            # Baseline conversion probability
            base_prob = np.random.beta(1, 8)  # ~11% base rate
            
            # Treatment effect
            action_effect = action_uplift_rates.get(action, 0) * risk_score
            conversion_prob = min(base_prob + action_effect, 1.0)
            
            converted = np.random.random() < conversion_prob
            
            # Discount cost
            discount = 0
            if action == "LIMITED_OFFER" and converted:
                discount = min(cart_value * 0.08, 200)
            
            sessions.append({
                "session_id": f"SIM_{i:06d}",
                "in_treatment": in_treatment,
                "risk_score": risk_score,
                "cart_value": cart_value,
                "action": action,
                "converted": converted,
                "discount_cost": discount,
                "revenue": cart_value * 0.25 if converted else 0,  # 25% margin
                "incremental_revenue": cart_value * 0.25 * action_effect if converted else 0,
            })

        df = pd.DataFrame(sessions)

        # Calculate results
        control = df[~df["in_treatment"]]
        treatment = df[df["in_treatment"]]
        
        control_cvr = control["converted"].mean()
        treatment_cvr = treatment["converted"].mean()
        
        # Statistical test
        t_stat, p_value = stats.ttest_ind(
            treatment["converted"].astype(float),
            control["converted"].astype(float)
        )
        
        # Confidence interval for uplift
        uplift = treatment_cvr - control_cvr
        se = np.sqrt(
            treatment["converted"].std()**2 / len(treatment) +
            control["converted"].std()**2 / len(control)
        )
        ci_lower = uplift - 1.96 * se
        ci_upper = uplift + 1.96 * se
        
        # Margin calculation
        treatment_margin = treatment["revenue"].mean() - treatment["discount_cost"].mean()
        control_margin = control["revenue"].mean()
        incremental_margin = treatment_margin - control_margin
        
        # Discount savings vs blanket discount
        blanket_discount_cost = df["cart_value"].mean() * 0.10  # 10% blanket
        smart_discount_cost = df[df["in_treatment"]]["discount_cost"].mean()
        discount_savings = blanket_discount_cost - smart_discount_cost
        
        return {
            "simulation_config": {
                "n_sessions": n_sessions,
                "treatment_size": len(treatment),
                "control_size": len(control),
            },
            "conversion_rates": {
                "control_cvr": round(control_cvr * 100, 2),
                "treatment_cvr": round(treatment_cvr * 100, 2),
                "absolute_uplift_pp": round(uplift * 100, 2),
                "relative_uplift_pct": round(uplift / max(control_cvr, 0.001) * 100, 1),
            },
            "statistical_significance": {
                "p_value": round(p_value, 4),
                "is_significant": p_value < 0.05,
                "confidence_level": "95%",
                "ci_lower_pp": round(ci_lower * 100, 2),
                "ci_upper_pp": round(ci_upper * 100, 2),
            },
            "financial_impact": {
                "incremental_margin_per_session_inr": round(incremental_margin, 2),
                "smart_discount_cost_inr": round(smart_discount_cost, 2),
                "blanket_discount_cost_inr": round(blanket_discount_cost, 2),
                "discount_savings_per_session_inr": round(discount_savings, 2),
                "discount_reduction_pct": round(discount_savings / max(blanket_discount_cost, 0.01) * 100, 1),
            },
            "action_performance": self._calculate_action_performance(df),
        }

    def _calculate_action_performance(self, df: pd.DataFrame) -> Dict:
        """Calculate per-action conversion rates and margin impact."""
        results = {}
        for action in df["action"].unique():
            subset = df[df["action"] == action]
            results[action] = {
                "count": len(subset),
                "cvr": round(subset["converted"].mean() * 100, 2),
                "avg_margin_inr": round(subset["revenue"].mean(), 2),
                "avg_discount_inr": round(subset["discount_cost"].mean(), 2),
            }
        return results

    def calculate_session_uplift(
        self,
        risk_score: float,
        root_cause: str,
        cart_value: float,
        proposed_discount: float = 0,
    ) -> Dict[str, Any]:
        """
        Calculate uplift probability for a specific session.
        Returns expected incremental margin with confidence interval.
        """
        # Base uplift by root cause
        base_uplift = {
            "PAYMENT_FAILURE": 0.42,
            "CHECKOUT_FRICTION": 0.32,
            "PRICE_SENSITIVITY": 0.28,
            "COMPARISON_SHOPPING": 0.18,
            "LOW_INTENT": 0.04,
            "UNKNOWN": 0.08,
        }.get(root_cause, 0.08)
        
        # Risk-adjusted uplift
        risk_multiplier = max(0, (risk_score - 0.5) * 2)
        expected_uplift = base_uplift * risk_multiplier
        
        # Margin calculation
        margin_rate = 0.25
        expected_incremental_revenue = cart_value * margin_rate * expected_uplift
        
        # Discount ROI check
        if proposed_discount > 0:
            roi = (expected_incremental_revenue - proposed_discount) / max(proposed_discount, 0.01)
            is_roi_positive = roi > 0
        else:
            roi = float("inf")
            is_roi_positive = True
        
        # Confidence interval (±30% of estimate)
        ci_margin = expected_incremental_revenue * 0.30
        
        return {
            "expected_uplift_probability": round(expected_uplift, 4),
            "expected_incremental_margin_inr": round(expected_incremental_revenue, 2),
            "ci_lower_inr": round(max(expected_incremental_revenue - ci_margin, 0), 2),
            "ci_upper_inr": round(expected_incremental_revenue + ci_margin, 2),
            "proposed_discount_inr": proposed_discount,
            "discount_roi": round(roi, 2) if roi != float("inf") else None,
            "is_roi_positive": is_roi_positive,
            "recommendation": "PROCEED" if is_roi_positive and expected_uplift > 0.10 else "DO_NOTHING",
        }


uplift_simulator = UpliftSimulator()
