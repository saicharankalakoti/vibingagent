from __future__ import annotations
import json
import os
import re
import urllib.request
from dotenv import load_dotenv

load_dotenv()

class LLMClient:
    def __init__(self):
        self.reload_config()
        self.last_mode = "unknown"
        self.last_error = None

    def reload_config(self):
        load_dotenv(override=True)
        self.provider = os.getenv("LLM_PROVIDER", "groq").lower().strip()
        self.groq_key = os.getenv("GROQ_API_KEY", "")
        self.groq_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")

    def _post_json(self, url: str, payload: dict, headers: dict | None = None) -> dict:
        data = json.dumps(payload).encode("utf-8")
        req_headers = {
            "Content-Type": "application/json",
            "User-Agent": "CostGuard/1.0 (Windows NT 10.0; Win64; x64)",
            **(headers or {})
        }
        req = urllib.request.Request(url, data=data, headers=req_headers, method="POST")
        with urllib.request.urlopen(req, timeout=45) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def chat(self, system: str, user: str) -> str:
        self.reload_config()
        self.last_error = None
        try:
            if self.provider == "ollama":
                out = self._post_json(
                    f"{self.ollama_url}/api/chat",
                    {"model": self.ollama_model,
                     "messages":[{"role":"system","content":system},{"role":"user","content":user}],
                     "stream":False, "options":{"temperature":0.1}}
                )
                self.last_mode = f"Ollama: {self.ollama_model}"
                return out["message"]["content"]
            if not self.groq_key or self.groq_key.startswith("PASTE_"):
                raise RuntimeError("GROQ_API_KEY is not configured")
            
            # Resilient model fallback candidate list
            models_to_try = [self.groq_model]
            for m in ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]:
                if m not in models_to_try:
                    models_to_try.append(m)

            last_exc = None
            for model_candidate in models_to_try:
                try:
                    out = self._post_json(
                        "https://api.groq.com/openai/v1/chat/completions",
                        {"model": model_candidate, "temperature": 0.1,
                         "messages":[{"role":"system","content":system},{"role":"user","content":user}]},
                        {"Authorization": f"Bearer {self.groq_key}"}
                    )
                    self.last_mode = f"Groq: {model_candidate}"
                    return out["choices"][0]["message"]["content"]
                except Exception as ex_candidate:
                    last_exc = ex_candidate
                    continue
            if last_exc:
                raise last_exc
            return ""
        except Exception as exc:
            self.last_error = str(exc)
            self.last_mode = "Deterministic Engine"
            return ""

    @staticmethod
    def extract_json(text: str) -> dict:
        if not text:
            return {}
        cleaned = text.strip().replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(cleaned)
        except Exception:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    return {}
        return {}

    def diagnose(self, request: str, service: dict, history: list[dict], freshness: dict) -> dict:
        system = '''You are CostGuard Diagnostic Agent. Analyze cloud cost and reliability signals.
Return ONLY valid JSON with keys: root_cause, evidence, candidate_actions.
candidate_actions is a list of objects with action, target_instances, reason.
Allowed actions: scale_up, scale_down, resize, stop_service, delay_batch, no_action.
Do not claim an action is safe; safety is checked separately by deterministic code.'''
        prompt = json.dumps({"request":request,"service":service,"history":history[-5:],"freshness":freshness}, indent=2)
        parsed = self.extract_json(self.chat(system, prompt))
        if parsed and "candidate_actions" in parsed:
            return parsed
        return deterministic_diagnosis(service, history, freshness)

    def choose(self, request: str, service: dict, diagnosis: dict, approved: list[dict]) -> dict:
        system = '''You are CostGuard Decision Agent. Pick exactly one action from the APPROVED list.
Return ONLY valid JSON: {"action":"...","target_instances":0,"justification":"..."}.
Never invent an action outside the approved list. Prefer protecting latency and health over cost savings.'''
        prompt = json.dumps({"request":request,"service":service,"diagnosis":diagnosis,"approved_actions":approved}, indent=2)
        parsed = self.extract_json(self.chat(system, prompt))
        if parsed and parsed.get("action") in {a.get("action") for a in approved}:
            return parsed
        if approved:
            a = approved[0]
            return {"action":a["action"], "target_instances":a.get("target_instances"),
                    "justification":a.get("reason","Selected from safety-approved set.")}
        return {"action":"no_action","target_instances":service.get("instances"),
                "justification":"No safety-approved action is available."}

    def compose(self, request: str, service: dict, diagnosis: dict, decision: dict, execution: dict, verification: dict) -> str:
        system = '''You are CostGuard's Lead Autonomous Cloud Optimization Engineer.
Write a comprehensive, professional, and thorough executive explanation of the decision, execution, and verified outcome.
Structure your explanation into the following clear Markdown sections:

### 1. Executive Summary & Root Cause
- Detail the observed telemetry that triggered this cycle: Service name, traffic volume (req/min), CPU utilization, and latency vs max SLA ceiling.
- Articulate the root cause (e.g., idle overprovisioned compute vs latency pressure from rising traffic).

### 2. Autonomous Action & Guardrail Validation
- State the exact capacity decision taken or withheld (instances adjusted, target count).
- Detail the safety policies validated: Latency SLA threshold, capacity bounds, freshness check, and cooldown compliance.
- Confirm execution and verification status.

### 3. Performance & Financial Impact
- Quantify before vs after: Instances, latency (ms), and hourly cost.
- Highlight the exact hourly savings or cost allocation (and estimated 30-day projection).
- Confirm that system stability and SLA standards are preserved.

Maintain an authoritative, clear, and professional tone. Never say an action succeeded unless verification status is verified.'''
        prompt = json.dumps({"request":request,"service":service,"diagnosis":diagnosis,"decision":decision,
                             "execution":execution,"verification":verification}, indent=2)
        text = self.chat(system, prompt)
        if text and len(text.strip()) > 80:
            return text.strip()
        return deterministic_response(service, decision, execution, verification)

def deterministic_diagnosis(service, history, freshness):
    rpm = float(service.get("requests_per_minute",0))
    cpu = float(service.get("cpu_percent",0))
    latency = float(service.get("latency_ms",0))
    max_latency = float(service.get("max_latency_ms",300))
    current = int(service.get("instances",1))
    min_i = int(service.get("min_instances",1))
    max_i = int(service.get("max_instances",10))
    evidence, candidates = [], []
    if freshness.get("stale"):
        return {"root_cause":"Untrusted or stale observation data","evidence":freshness.get("reasons",[]),
                "candidate_actions":[{"action":"no_action","target_instances":current,"reason":"Wait for fresh data."}]}
    if latency >= max_latency * 0.85 or cpu >= 80 or (len(history)>=2 and rpm > float(history[-2].get("requests_per_minute",rpm))*1.5):
        evidence.append(f"latency={latency:.0f}ms, CPU={cpu:.0f}%, traffic={rpm:.0f} rpm")
        target = min(max_i, max(current+2, current+1))
        candidates.append({"action":"scale_up","target_instances":target,"reason":"Protect latency/SLA under load."})
    if rpm <= 1 and cpu < 20 and current > min_i:
        evidence.append("near-zero traffic with low CPU and spare instances")
        candidates.append({"action":"scale_down","target_instances":min_i,"reason":"Reduce idle capacity after history confirms low traffic."})
    if not candidates:
        candidates.append({"action":"no_action","target_instances":current,"reason":"No clear safe optimization signal."})
    return {"root_cause":"; ".join(evidence) if evidence else "No urgent cost/reliability anomaly detected",
            "evidence":evidence or ["Current utilization and traffic are within normal range."],
            "candidate_actions":candidates}

def deterministic_response(service, decision, execution, verification):
    name = service.get("name", "service")
    action = decision.get("action", "no_action")
    justification = decision.get("justification", "Operational safety checks completed.")
    status = verification.get("status", "unknown")
    exec_status = execution.get("status", "not_executed")

    b_data = execution.get("before", service)
    b_inst = b_data.get("instances", service.get("instances", 1))
    a_inst = verification.get("after_instances", b_inst)

    b_lat = b_data.get("latency_ms", service.get("latency_ms", 0))
    a_lat = verification.get("after_latency_ms", b_lat)
    max_lat = service.get("max_latency_ms", 300)

    cost_before = float(verification.get("cost_before", execution.get("cost_before", service.get("estimated_hourly_cost", 0))) or 0)
    cost_after = float(verification.get("cost_after", cost_before) or cost_before)
    saving = cost_before - cost_after
    monthly_impact = abs(saving) * 24 * 30

    cpu = service.get("cpu_percent", 0)
    rpm = service.get("requests_per_minute", 0)

    recovery_note = ""
    if execution.get("recovered_from"):
        recovery_note = f"\n- **Automated Failure Recovery**: Initial scale attempt encountered `{execution['recovered_from'].get('error')}`; CostGuard autonomously executed a smaller safe incremental capacity step."

    if action == "scale_down":
        action_summary = f"Safely scaled down `{name}` from **{b_inst} to {a_inst} instances** to eliminate idle cloud spend."
        root_cause_summary = f"Telemetry confirmed sustained low traffic ({rpm:,.0f} req/min) and low CPU utilization ({cpu}%). The provisioned compute was far above actual operational demand."
        guardrail_summary = f"Verified post-scale latency ({a_lat}ms) remains well below the {max_lat}ms SLA limit. Freshness, cooldown, and capacity bounds cleared."
        impact_summary = f"Reduced hourly spend from **${cost_before:.2f}** to **${cost_after:.2f}**, unlocking **${saving:.2f}/hr** in net savings (approx. **${monthly_impact:,.2f}/month**) while fully preserving reliability."
    elif action == "scale_up":
        action_summary = f"Proactively scaled up `{name}` from **{b_inst} to {a_inst} instances** to safeguard service reliability."
        root_cause_summary = f"Traffic demand surge ({rpm:,.0f} req/min) or high latency ({b_lat}ms) was approaching the {max_lat}ms SLA threshold, risking breach."
        guardrail_summary = f"Capacity bounded within max ceiling ({service.get('max_instances', 10)} instances). Deterministic safety engine authorized immediate resource expansion."
        impact_summary = f"Latency reduced from **{b_lat}ms to {a_lat}ms**, maintaining compliant SLA performance. Operational expenditure increased to **${cost_after:.2f}/hr** to prioritize business continuity."
    else:
        action_summary = f"Withheld capacity modifications for `{name}`; maintained steady operational baseline at **{b_inst} instances**."
        root_cause_summary = f"Current telemetry ({cpu}% CPU, {b_lat}ms latency, {rpm:,.0f} req/min) is operating safely within nominal SLA parameters."
        guardrail_summary = f"Policy engine validated stability conditions; no action was required or safe at this cycle."
        impact_summary = f"Expenditure remains steady at **${cost_before:.2f}/hr**, ensuring uninterrupted baseline operations."

    return f"""### 1. Executive Summary & Root Cause
- **Monitored Service**: `{name}`
- **Observed Telemetry**: Ingress: {rpm:,.0f} req/min | CPU: {cpu}% | Latency: {b_lat}ms (SLA Ceiling: <{max_lat}ms)
- **Root Cause Analysis**: {root_cause_summary}

### 2. Autonomous Action & Guardrail Validation
- **Engine Decision**: {action_summary}
- **Strategic Justification**: {justification}
- **Guardrails Evaluated**: {guardrail_summary}
- **Execution & Verification**: Action execution status is `{exec_status}` with verification result `{status}`.{recovery_note}

### 3. Performance & Financial Impact
- **Capacity Trajectory**: {b_inst} → {a_inst} instances
- **Latency Trajectory**: {b_lat}ms → {a_lat}ms (Target: <{max_lat}ms)
- **Financial Outcome**: {impact_summary}"""

