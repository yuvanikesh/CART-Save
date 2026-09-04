"""
CartGuard AI - Demo Runner
Run all 6 demo scenarios and show results.
Usage: python scripts/run_demo.py
"""
import sys
import os
import asyncio
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from agents.orchestrator import orchestrator

DEMO_SESSIONS = [
    {
        "name": "1. Complex Payment Failure",
        "expected": "ALTERNATE_PAYMENT_GUIDANCE",
        "data": {
            "session_id": "DEMO_001",
            "session_duration": 240,
            "product_views": 4,
            "cart_adds": 2,
            "cart_changes": 2,
            "cart_value": 3500,
            "category_switches": 0,
            "tab_switches": 1,
            "page_revisits": 3,
            "checkout_steps_completed": 4,
            "checkout_time": 120,
            "payment_attempts": 2,
            "payment_failures": 1,
            "time_on_payment_page": 180,
            "payment_method_switches": 2,
            "form_field_errors": 0,
            "is_returning_visitor": True,
            "session_recency_minutes": 5,
        },
    },
    {
        "name": "2. Comparison Shopping",
        "expected": "SOCIAL_PROOF_NUDGE",
        "data": {
            "session_id": "DEMO_002",
            "session_duration": 480,
            "product_views": 12,
            "cart_adds": 1,
            "cart_changes": 3,
            "cart_value": 1200,
            "category_switches": 5,
            "tab_switches": 8,
            "checkout_steps_completed": 0,
            "payment_attempts": 0,
            "payment_failures": 0,
            "is_returning_visitor": False,
            "session_recency_minutes": 15,
        },
    },
    {
        "name": "3. Checkout Friction",
        "expected": "CHECKOUT_ASSISTANCE",
        "data": {
            "session_id": "DEMO_003",
            "session_duration": 360,
            "product_views": 3,
            "cart_adds": 2,
            "cart_changes": 2,
            "cart_value": 800,
            "checkout_steps_completed": 2,
            "checkout_time": 240,
            "payment_attempts": 0,
            "payment_failures": 0,
            "form_field_errors": 5,
            "back_navigations": 6,
            "is_returning_visitor": False,
            "session_recency_minutes": 8,
        },
    },
    {
        "name": "4. Mixed Signals → DO_NOTHING",
        "expected": "DO_NOTHING",
        "data": {
            "session_id": "DEMO_004",
            "session_duration": 300,
            "product_views": 5,
            "cart_adds": 2,
            "cart_removes": 1,
            "cart_changes": 5,
            "cart_value": 1500,
            "original_cart_value": 2200,
            "category_switches": 2,
            "tab_switches": 3,
            "checkout_steps_completed": 3,
            "payment_attempts": 2,
            "payment_failures": 1,
            "time_on_payment_page": 90,
            "is_returning_visitor": True,
        },
    },
    {
        "name": "5. Low Intent → DO_NOTHING",
        "expected": "DO_NOTHING",
        "data": {
            "session_id": "DEMO_005",
            "session_duration": 720,
            "product_views": 15,
            "cart_adds": 0,
            "cart_changes": 0,
            "cart_value": 0,
            "category_switches": 4,
            "tab_switches": 10,
            "checkout_steps_completed": 0,
            "payment_attempts": 0,
            "payment_failures": 0,
            "is_returning_visitor": False,
            "session_recency_minutes": 30,
        },
    },
    {
        "name": "6. Urgent Bargain Hunter → LIMITED_OFFER",
        "expected": "LIMITED_OFFER",
        "data": {
            "session_id": "DEMO_006",
            "session_duration": 180,
            "product_views": 8,
            "cart_adds": 3,
            "cart_removes": 2,
            "cart_changes": 8,
            "cart_value": 900,
            "original_cart_value": 1200,
            "category_switches": 2,
            "tab_switches": 5,
            "checkout_steps_completed": 1,
            "is_returning_visitor": True,
            "session_recency_minutes": 3,
            "user_segment": "BARGAIN",
        },
    },
]


async def run_demos():
    print("=" * 70)
    print("CartGuard AI — Demo Scenario Runner")
    print("=" * 70)
    
    results = []
    for scenario in DEMO_SESSIONS:
        print(f"\n🔍 Running: {scenario['name']}")
        print(f"   Expected: {scenario['expected']}")
        
        try:
            result = await orchestrator.process_session(scenario["data"])
            
            risk = result.get("risk_score", 0)
            root_cause = result.get("diagnosis", {}).get("root_cause", "?")
            action = result.get("action", {}).get("action_type", "?")
            self_check = result.get("self_check", {}).get("status", "?")
            latency = result.get("metrics", {}).get("total_latency_ms", 0)
            
            match = "✅" if action == scenario["expected"] else "⚠️ "
            
            print(f"   Risk: {risk:.2%} | Cause: {root_cause} | Action: {action} {match}")
            print(f"   Self-Check: {self_check} | Latency: {latency:.0f}ms")
            
            if result.get("action", {}).get("message"):
                print(f"   Message: {result['action']['message'][:80]}...")
            
            results.append({
                "scenario": scenario["name"],
                "expected": scenario["expected"],
                "actual": action,
                "match": action == scenario["expected"],
                "risk_score": risk,
                "root_cause": root_cause,
                "latency_ms": latency,
            })
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results.append({"scenario": scenario["name"], "error": str(e)})
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    matches = sum(1 for r in results if r.get("match", False))
    print(f"Scenarios matched: {matches}/{len(DEMO_SESSIONS)}")
    avg_latency = sum(r.get("latency_ms", 0) for r in results) / len(results)
    print(f"Average latency: {avg_latency:.0f}ms")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_demos())