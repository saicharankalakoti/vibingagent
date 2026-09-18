import json
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
from agent.graph import run_costguard
from core.tools import check_api_health
from core.store import get_all_actions, clear_db

load_dotenv()

st.set_page_config(page_title="CostGuard", page_icon="☁️", layout="wide")

st.title("CostGuard")
st.caption("Autonomous Cloud Cost-Optimization Agent  •  Investigate → Decide → Act Safely → Verify → Explain")

scenario_dir = Path(__file__).resolve().parent / "data" / "scenarios"
scenarios = {
    "Test A — Cost optimization": "test_a_cost_optimization.json",
    "Test B — Rising traffic": "test_b_rising_traffic.json",
    "Test C — Stale observation": "test_c_stale_observation.json",
    "Test D — Failed action recovery": "test_d_failed_action.json",
}

api_online = check_api_health()

with st.sidebar:
    st.header("System Status")
    if api_online:
        st.success("🟢 Mock Cloud API: Connected")
    else:
        st.error("🔴 Mock Cloud API: Offline")
        st.caption("Start it with `run_backend.bat` or `uvicorn backend.main:app --port 8000`")

    st.divider()
    st.header("Demo Controls")
    selected = st.selectbox("Judge scenario", list(scenarios))
    if st.button("Load selected scenario", use_container_width=True):
        data = json.loads((scenario_dir / scenarios[selected]).read_text(encoding="utf-8"))
        st.session_state["request"] = data.pop("request")
        st.session_state["payload"] = json.dumps(data, indent=2)
        st.rerun()

    if st.button("🔄 Reset SQLite DB & State", use_container_width=True):
        clear_db()
        st.success("Database state cleared!")
        st.rerun()

    st.divider()
    st.info("• LLM handles diagnosis, action selection and explanation.\n• Policy engine, freshness check, API execution and verification use deterministic code.")

# Prepare initial default state cleanly
default_data = json.loads((scenario_dir / scenarios["Test A — Cost optimization"]).read_text(encoding="utf-8"))
default_scenario_request = default_data.pop("request", "Optimize costs for reports-worker without reducing reliability.")
default_scenario_payload = json.dumps(default_data, indent=2)

request = st.text_area("Natural-language request", st.session_state.get("request", default_scenario_request), height=85)
payload_text = st.text_area("Cloud state JSON", st.session_state.get("payload", default_scenario_payload), height=380)

col1, col2 = st.columns([1, 4])
with col1:
    run = st.button("▶ Run CostGuard", type="primary", use_container_width=True)
with col2:
    st.info("Tip: Run Scenarios A → B → C → D in order for the complete judge demonstration.")

if run:
    if not api_online:
        st.error("Cannot run CostGuard: Mock Cloud API is not reachable at http://127.0.0.1:8000. Please start the backend service first.")
        st.stop()

    try:
        raw = json.loads(payload_text)
    except json.JSONDecodeError as e:
        st.error(f"Invalid JSON: {e}")
        st.stop()

    with st.spinner("CostGuard is investigating, applying guardrails, executing and verifying..."):
        try:
            result = run_costguard(request, raw)
        except Exception as e:
            st.error(f"Workflow error: {e}")
            st.exception(e)
            st.stop()

    st.success("Workflow completed successfully")

    verification = result.get("verification", {})
    execution = result.get("execution", {})
    action_kind = result.get("decision", {}).get("action", "no_action").replace("_", " ").title()
    verif_status = verification.get("status", "unknown").replace("_", " ").title()
    cost_after = float(verification.get("cost_after", 0))
    saving = float(verification.get("estimated_hourly_saving", 0))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Action", action_kind)
    c2.metric("Verification", verif_status)
    c3.metric("Hourly Cost", f"${cost_after:.2f}")
    c4.metric("Hourly Saving", f"${abs(saving):.2f}", delta=f"{saving:+.2f}/hr" if saving != 0 else "No change")

    st.caption(f"🧠 Intelligence Mode: **{result.get('llm_mode', 'Unknown')}**")

    st.subheader("Response to User")
    st.info(result.get("response", ""))

    st.subheader("Before → After Evidence")
    before = execution.get("before", {})
    after = {
        "instances": verification.get("after_instances"),
        "latency_ms": verification.get("after_latency_ms"),
        "healthy": verification.get("healthy"),
        "estimated_hourly_cost": verification.get("cost_after")
    }
    evidence = {
        "Metric": ["Instances", "Latency (ms)", "Healthy", "Estimated hourly cost"],
        "Before": [
            str(before.get("instances")) if before.get("instances") is not None else "N/A",
            f"{before.get('latency_ms')} ms" if before.get("latency_ms") is not None else "N/A",
            "Yes" if before.get("healthy") else "No",
            f"${verification.get('cost_before', 0):.2f}"
        ],
        "After": [
            str(after.get("instances")) if after.get("instances") is not None else "N/A",
            f"{after.get('latency_ms')} ms" if after.get("latency_ms") is not None else "N/A",
            "Yes" if after.get("healthy") else "No",
            f"${after.get('estimated_hourly_cost', 0):.2f}"
        ]
    }
    st.table(evidence)

    st.subheader("Agent Audit Trace")
    for item in result.get("trace", []):
        with st.expander(item["stage"], expanded=True):
            detail = item["detail"]
            if isinstance(detail, (dict, list)):
                st.json(detail)
            else:
                st.write(detail)

    with st.expander("📜 SQLite Persistent Action Log"):
        recent_actions = get_all_actions(10)
        if recent_actions:
            st.dataframe(recent_actions, use_container_width=True)
        else:
            st.caption("No persistent actions recorded yet.")

    with st.expander("Full Final State JSON"):
        st.json(result)
