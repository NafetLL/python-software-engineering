import json
import os
import random
import time
import requests
from dotenv import load_dotenv

load_dotenv()


class LLMRouter:
    """
    Network & QoS Resilience Layer.
    Routes requests across SLM (fast/cheap) and Frontier (deep reasoning) model tiers,
    enforces proactive RPM cooldowns, fails over on 429/503 circuit breaks, and tracks QoS health.
    """

    def __init__(self, pacing_cooldown_sec: float = 4.0, circuit_breaker_threshold: int = 3) -> None:
        self.primary_key = os.getenv("GEMINI_API_KEY", "")
        self.secondary_key = os.getenv("GEMINI_API_KEY_SECONDARY", self.primary_key)

# Ordered provider routes per computational tier
        self.routes = {
            "slm_fast": [
                {
                    "name": "gemini-3.8-flash-primary",
                    "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent",
                    "api_key": self.primary_key,
                },
                {
                    "name": "gemini-3.8-flash-secondary",
                    "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent",
                    "api_key": self.secondary_key,
                },
            ],
            "frontier_deep": [
                {
                    "name": "gemini-3.8-flash-deep-primary",
                    "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent",
                    "api_key": self.primary_key,
                },
                {
                    "name": "gemini-3.8-flash-deep-secondary",
                    "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent",
                    "api_key": self.secondary_key,
                },
            ],
        }

        self.pacing_cooldown_sec = pacing_cooldown_sec
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self._last_call_ts = 0.0

        # QoS Telemetry Counters
        self.total_calls = 0
        self.successful_calls = 0
        self.error_breakdown = {"429": 0, "503": 0, "other": 0}
        self.latencies: list[float] = []

    def _enforce_proactive_pacing(self) -> None:
        """Sleeps only if needed to respect proactive Requests-Per-Minute pacing."""
        elapsed = time.time() - self._last_call_ts
        if elapsed < self.pacing_cooldown_sec:
            time.sleep(self.pacing_cooldown_sec - elapsed)

    def generate_json(
        self,
        system_instruction: str,
        user_prompt: str,
        tier: str = "slm_fast",
        max_cycles: int = 2,
    ) -> dict:
        """
        Sends a structured prompt enforcing strict JSON output with multi-route circuit-breaker failover.
        """
        candidates = self.routes.get(tier, self.routes["slm_fast"])
        payload = {
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.2,
            },
        }

        last_error: Exception | None = None

        for cycle in range(1, max_cycles + 1):
            for route in candidates:
                if not route["api_key"]:
                    continue

                consecutive_transient = 0

                while consecutive_transient < self.circuit_breaker_threshold:
                    self._enforce_proactive_pacing()
                    self.total_calls += 1
                    self._last_call_ts = time.time()
                    t0 = time.perf_counter()

                    headers = {
                        "Content-Type": "application/json",
                        "X-goog-api-key": route["api_key"],
                    }

                    try:
                        resp = requests.post(route["url"], headers=headers, json=payload, timeout=145)
                        resp.raise_for_status()
                        latency = round(time.perf_counter() - t0, 3)

                        self.successful_calls += 1
                        self.latencies.append(latency)

                        raw_json = resp.json()
                        text_out = raw_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                        return json.loads(text_out)

                    except requests.exceptions.HTTPError as err:
                        last_error = err
                        status = err.response.status_code if err.response is not None else 0

                        if status in (429, 503, 502, 504):
                            key = "429" if status == 429 else "503"
                            self.error_breakdown[key] += 1
                            consecutive_transient += 1

                            # Exponential backoff with stochastic jitter
                            backoff = min(2 ** consecutive_transient, 30) + random.uniform(0.2, 1.2)
                            print(
                                f"⚠️ [{route['name']}] HTTP {status} "
                                f"({consecutive_transient}/{self.circuit_breaker_threshold}). "
                                f"Backoff {backoff:.1f}s..."
                            )
                            time.sleep(backoff)
                        else:
                            # Unrecoverable 400/401/403 -> fail fast immediately
                            self.error_breakdown["other"] += 1
                            raise err

                    except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError) as err:
                        last_error = err
                        self.error_breakdown["other"] += 1
                        consecutive_transient += 1
                        backoff = min(2 ** consecutive_transient, 15)
                        print(f"⚠️ [{route['name']}] Transient parse/net error: {err}. Retrying in {backoff}s...")
                        time.sleep(backoff)

                print(f"🔌 Circuit Breaker Tripped on '{route['name']}'. Failing over to next provider route...")

        raise RuntimeError(f"❌ All API routes exhausted after {max_cycles} failover cycles: {last_error}")

    def get_qos_snapshot(self) -> dict:
        """Returns compressed Quality of Service health metrics for Planner & Reporter."""
        health = (
            round(self.successful_calls / self.total_calls, 4)
            if self.total_calls > 0
            else 1.0
        )
        avg_lat = round(sum(self.latencies) / len(self.latencies), 3) if self.latencies else 0.0
        return {
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "qos_health": health,
            "traffic_health_percentage": round(health * 100, 2),
            "avg_latency_sec": avg_lat,
            "error_breakdown": dict(self.error_breakdown),
        }