"""
CartGuard AI - Session & Signal Caching Layer
High-performance similarity and fingerprint caching for LLM agent responses.
Target: >80% cache hit rate for similar session patterns with <10ms cached latency.
"""

import hashlib
import json
import time
from typing import Dict, Any, Optional, Tuple


class SessionCache:
    """
    Session and Behavioral Signal Cache.
    Generates deterministic hash keys by quantizing session metrics to enable
    high cache hit rates across similar user behavioral fingerprints.
    """

    def __init__(self, ttl_seconds: int = 3600, max_entries: int = 10000):
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self.store: Dict[str, Tuple[Dict[str, Any], float]] = {}
        self.hits = 0
        self.misses = 0

    def _hash_context(self, context: Dict[str, Any], agent_name: str) -> str:
        """
        Quantize context metrics to create a stable hash key for similar sessions.
        """
        cart_value = round(float(context.get("cart_value", 0)) / 100) * 100  # Bucket by ₹100
        duration = round(float(context.get("session_duration", 0)) / 30) * 30  # Bucket by 30s
        payment_attempts = int(context.get("payment_attempts", 0))
        payment_failures = int(context.get("payment_failures", 0))
        product_views = int(context.get("product_views", 0))
        cart_adds = int(context.get("cart_adds", 0))
        tab_loss = int(context.get("tab_loss_count", 0))
        hesitation = round(float(context.get("hesitation_score", 0)), 1)
        checkout_steps = int(context.get("checkout_steps", 1))

        key_components = {
            "agent": agent_name,
            "cart_bucket": cart_value,
            "dur_bucket": duration,
            "pay_att": payment_attempts,
            "pay_fail": payment_failures,
            "prod_views": min(product_views, 20),
            "cart_adds": min(cart_adds, 10),
            "tab_loss": min(tab_loss, 5),
            "hesitation": hesitation,
            "checkout_step": checkout_steps,
        }

        key_bytes = json.dumps(key_components, sort_keys=True).encode("utf-8")
        return hashlib.sha256(key_bytes).hexdigest()

    def get(self, context: Dict[str, Any], agent_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached diagnosis if valid and not expired."""
        key = self._hash_context(context, agent_name)
        if key in self.store:
            data, timestamp = self.store[key]
            if time.time() - timestamp <= self.ttl_seconds:
                self.hits += 1
                result = dict(data)
                result["is_cached"] = True
                return result
            else:
                del self.store[key]

        self.misses += 1
        return None

    def set(self, context: Dict[str, Any], agent_name: str, response: Dict[str, Any]) -> None:
        """Store agent response in cache."""
        if len(self.store) >= self.max_entries:
            # Simple eviction: remove oldest key
            oldest_key = min(self.store.keys(), key=lambda k: self.store[k][1])
            del self.store[oldest_key]

        key = self._hash_context(context, agent_name)
        self.store[key] = (response, time.time())

    def get_stats(self) -> Dict[str, Any]:
        """Return cache performance metrics."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0.0
        return {
            "hits": self.hits,
            "misses": self.misses,
            "total_queries": total,
            "hit_rate_pct": round(hit_rate, 2),
            "cache_size": len(self.store),
        }

    def clear(self) -> None:
        """Clear all cached entries."""
        self.store.clear()
        self.hits = 0
        self.misses = 0


# Global session cache instance
session_cache = SessionCache()
