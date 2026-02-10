"""
ECL Studio — Streamlit Edition
================================
Low-code builder for Entity-Context-Linking extraction pipeline.
Run: /Users/yakarteek/.pyenv/versions/ecl-demo/bin/streamlit run ecl_app.py
"""

import streamlit as st
import time
import json
import os
import sys
from datetime import datetime
from dataclasses import asdict

# Ensure ECL modules are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ecl_poc import (
    Entity, Relationship, ExtractionResult, EntityType,
    MoEOrchestrator, ContextGraphBuilder, HealthcareExpert,
)
from ecl_tracing import (
    ExtractionTrace, PipelineTrace, hash_text, save_trace,
    validate_entity, apply_confidence_filter, MIN_CONFIDENCE,
    get_prompt_version, PROMPT_VERSIONS,
)
from ecl_connectors import ConnectorRegistry
from ecl_governance import GovernanceEngine

# Try LLM module
try:
    from ecl_llm import LLMMoEOrchestrator, OllamaClient
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False


# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ECL Studio",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, rgba(30,41,59,0.8), rgba(15,23,42,0.9));
        border: 1px solid rgba(99,102,241,0.3);
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    [data-testid="stMetricValue"] {
        font-size: 32px !important;
        font-weight: 900 !important;
    }
    .stDataFrame { border-radius: 12px; overflow: hidden; }
    hr { border-color: rgba(99,102,241,0.2) !important; }
</style>
""", unsafe_allow_html=True)


# ── Ollama check ───────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def check_ollama():
    try:
        import urllib.request
        req = urllib.request.Request("http://localhost:11434/api/tags")
        resp = urllib.request.urlopen(req, timeout=2)
        data = json.loads(resp.read())
        models = [m["name"] for m in data.get("models", [])]
        return True, models
    except Exception:
        return False, []


# ── Expert definitions ─────────────────────────────────────────────────────
EXPERT_DEFS = [
    {"name": "ContractExpert", "domain": "Contracts & Agreements", "icon": "📄"},
    {"name": "EquipmentExpert", "domain": "Equipment & Assets", "icon": "⚙️"},
    {"name": "FinancialRiskExpert", "domain": "Financial Risks", "icon": "💰"},
    {"name": "OpportunityExpert", "domain": "Business Opportunities", "icon": "🎯"},
    {"name": "HealthcareExpert", "domain": "Healthcare Records", "icon": "🏥"},
]


# ── Sample document ────────────────────────────────────────────────────────
SAMPLE_DOC = """TOWER SITE INSPECTION REPORT
Tower ID: T-789 | Location: 40.6892° N, 74.0445° W | Type: Monopole | Height: 150ft

=== SECTION A: TENANT CONTRACTS ===

Contract #1001 - Company: Verizon Wireless
  Status: Active | Occupancy: 45% | Monthly Revenue: $5,000
  Lease Term: 2020-2030 | Auto-Renew: Yes
  Payment Status: Current | Outstanding: $0

Contract #1002 - Company: T-Mobile
  Status: Active | Occupancy: 30% | Monthly Revenue: $4,200
  Lease Term: 2021-2031 | Auto-Renew: Yes
  Payment Status: Current | Outstanding: $0

=== SECTION B: EQUIPMENT INVENTORY ===

Antenna Array: 3x Ericsson AIR 6449 (Band 77, 5G NR)
  Condition: Good | Last Maintenance: 2025-06-15
  Wind Load: Within specs | Ice Load: Acceptable

RRU: 6x Nokia AEQE (Remote Radio Units)
  Power Consumption: 1,200W per unit | Backup: 4hr battery

=== SECTION C: FINANCIAL RISK ASSESSMENT ===

Annual Revenue: $110,400 | Operating Costs: $45,000
Maintenance Reserve: $12,000 | Insurance: $8,500
Net Operating Income: $44,900

Payment Default Risk: LOW (all tenants current)
Market Risk: MODERATE (5G buildout may increase competition)

=== SECTION D: GROWTH OPPORTUNITIES ===

Available Capacity: 25% remaining
Pending Interest: AT&T (formal inquiry received 2025-01-10)
Estimated Additional Revenue: $4,500/month if AT&T onboards
Tower Upgrade Potential: Can support additional 2 carriers with structural reinforcement ($35,000 estimated cost)
"""


# ── Extraction logic (mirrors ecl_server._run_extraction) ──────────────────
def run_extraction(text: str, use_llm: bool, model: str, confidence_threshold: float):
    """Run MoE extraction pipeline. Same logic as ecl_server.py."""
    start_time = time.time()

    # Choose orchestrator
    if use_llm and LLM_AVAILABLE:
        orchestrator = LLMMoEOrchestrator(model=model)
        results = orchestrator.extract_all(text)
    else:
        orchestrator = MoEOrchestrator()
        results = orchestrator.extract_all(text)

    # Build graph
    graph_builder = ContextGraphBuilder()
    graph_builder.add_extraction_results(results)

    # Serialize entities
    entities = []
    for eid, entity in graph_builder.nodes.items():
        entities.append({
            "id": entity.id,
            "type": entity.type.value,
            "name": entity.name,
            "confidence": entity.confidence,
            "source_expert": entity.source_expert,
            "properties": entity.properties,
        })

    # Serialize relationships
    relationships = []
    for rel in graph_builder.edges:
        relationships.append({
            "source": rel.source_id,
            "target": rel.target_id,
            "type": rel.type.value,
            "confidence": rel.confidence,
        })

    elapsed_ms = (time.time() - start_time) * 1000

    # Expert breakdown
    expert_results = {}
    for expert_name, extraction in results.items():
        expert_results[expert_name] = {
            "entities": len(extraction.entities),
            "relationships": len(extraction.relationships),
            "reasoning": extraction.reasoning,
        }

    return {
        "entities": entities,
        "relationships": relationships,
        "expert_results": expert_results,
        "total_entities": len(entities),
        "total_relationships": len(relationships),
        "processing_time_ms": round(elapsed_ms),
        "engine": model if use_llm else "regex",
        "confidence_threshold": confidence_threshold,
    }


# ── Session state init ─────────────────────────────────────────────────────
if "doc_text" not in st.session_state:
    st.session_state["doc_text"] = ""
if "last_result" not in st.session_state:
    st.session_state["last_result"] = None


# ═══════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## ⚡ ECL Studio")
    st.caption("Low-Code Entity Extraction Builder")
    st.divider()

    # ── Status ──
    ollama_ok, models = check_ollama()
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("🟢 **Ollama**" if ollama_ok else "🔴 **Ollama**")
    with col2:
        st.markdown(f"📡 `{len(models)}` models")
    st.caption(f"LLM Module: {'✅ Loaded' if LLM_AVAILABLE else '❌ Not found'}")

    st.divider()

    # ── Experts ──
    st.markdown("### 🧠 Extraction Experts")
    enabled_experts = []
    for exp in EXPERT_DEFS:
        enabled = st.checkbox(
            f"{exp['icon']} {exp['name']}",
            value=(exp["name"] != "HealthcareExpert"),
            key=f"expert_{exp['name']}",
        )
        if enabled:
            enabled_experts.append(exp["name"])

    st.divider()

    # ── Config ──
    st.markdown("### ⚙️ Configuration")
    confidence = st.slider(
        "Confidence Threshold",
        min_value=0.0, max_value=1.0, value=0.70, step=0.05, format="%.2f",
    )

    mode = st.selectbox(
        "Extraction Mode",
        ["Regex Experts (Fast)", "LLM Experts (Ollama)"],
    )
    use_llm = (mode == "LLM Experts (Ollama)")

    model_options = models if models else ["llama3:8b", "mistral:7b", "gemma2:9b"]
    model = st.selectbox("LLM Model", model_options, disabled=(not use_llm))

    st.divider()

    # ── Connectors ──
    st.markdown("### 🔌 Connectors")
    for name, online in [("FileSystem (Local)", True), ("SharePoint", False),
                          ("Dynamics 365", False), ("ServiceNow", False)]:
        st.markdown(f"{'🟢' if online else '🟡'} {name}")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN AREA
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("# 📄 Document Input")

# Buttons BEFORE the text_area (avoids session_state widget conflict)
col_btn1, col_btn2, col_spacer = st.columns([1, 1, 4])
with col_btn1:
    load_sample = st.button("📋 Load Sample", use_container_width=True)
with col_btn2:
    clear = st.button("�️ Clear", use_container_width=True)

if load_sample:
    st.session_state["doc_text"] = SAMPLE_DOC
if clear:
    st.session_state["doc_text"] = ""

# Text area bound to session state
doc_text = st.text_area(
    "Paste your document text here",
    value=st.session_state["doc_text"],
    height=250,
    placeholder="Paste a tower inspection report, contract, medical record, or financial document...",
)
# Sync back
st.session_state["doc_text"] = doc_text

st.metric("Characters", len(doc_text))

# Extract button
extract_clicked = st.button(
    "⚡ Extract Entities",
    type="primary",
    use_container_width=True,
    disabled=(len(doc_text.strip()) == 0),
)

# ── Run extraction ──
if extract_clicked and doc_text.strip():
    with st.spinner("🔄 Running MoE extraction pipeline..."):
        result = run_extraction(doc_text, use_llm, model, confidence)
    st.session_state["last_result"] = result

# ── Show results ──
if st.session_state["last_result"]:
    result = st.session_state["last_result"]
    entities = result["entities"]
    relationships = result["relationships"]

    st.divider()

    # Metric cards
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Entities", result["total_entities"])
    m2.metric("Relationships", result["total_relationships"])
    m3.metric("Processing", f"{result['processing_time_ms']}ms")
    m4.metric("Engine", result["engine"])

    st.divider()

    # Tabs
    tab_table, tab_graph, tab_trace = st.tabs([
        "📊 Entity Table", "🕸️ Graph Preview", "📋 Pipeline Trace"
    ])

    # ─── Entity Table ────────────────────────────────────────────────
    with tab_table:
        if entities:
            import pandas as pd
            df = pd.DataFrame([
                {
                    "Entity": e["name"],
                    "Type": e["type"],
                    "Confidence": e["confidence"],
                    "Expert": e["source_expert"],
                    "Properties": json.dumps(e.get("properties", {}), default=str)[:80],
                }
                for e in entities
            ])
            df = df.sort_values("Confidence", ascending=False).reset_index(drop=True)

            st.dataframe(
                df,
                column_config={
                    "Confidence": st.column_config.ProgressColumn(
                        "Confidence", min_value=0.0, max_value=1.0, format="%.2f",
                    ),
                    "Type": st.column_config.TextColumn("Type", width="small"),
                    "Expert": st.column_config.TextColumn("Expert", width="medium"),
                },
                use_container_width=True,
                hide_index=True,
            )

            # Download
            st.download_button(
                "📥 Download CSV",
                df.to_csv(index=False),
                "ecl_entities.csv",
                "text/csv",
            )
        else:
            st.info("No entities extracted above confidence threshold.")

    # ─── Graph Preview ───────────────────────────────────────────────
    with tab_graph:
        if entities:
            try:
                from streamlit_agraph import agraph, Node, Edge, Config

                colors = {
                    "ASSET": "#3b82f6", "ORGANIZATION": "#8b5cf6",
                    "CONTRACT": "#f59e0b", "MONETARY": "#10b981",
                    "EQUIPMENT": "#6366f1", "RISK": "#ef4444",
                    "OPPORTUNITY": "#f97316", "PERSON": "#ec4899",
                    "TOWER": "#3b82f6", "FINANCIAL_METRIC": "#10b981",
                }

                nodes = []
                seen = set()
                for ent in entities:
                    name = ent["name"]
                    etype = ent["type"]
                    if name not in seen:
                        nodes.append(Node(
                            id=name, label=name, size=25,
                            color=colors.get(etype, "#64748b"),
                            font={"color": "#e2e8f0", "size": 14},
                        ))
                        seen.add(name)

                edges = []
                for rel in relationships:
                    src_name = next((e["name"] for e in entities if e["id"] == rel["source"]), rel["source"])
                    tgt_name = next((e["name"] for e in entities if e["id"] == rel["target"]), rel["target"])
                    if src_name in seen and tgt_name in seen:
                        edges.append(Edge(
                            source=src_name, target=tgt_name,
                            label=rel.get("type", ""), color="#475569",
                        ))

                config = Config(
                    width=900, height=400, directed=True,
                    physics=True, hierarchical=False,
                    nodeHighlightBehavior=True, highlightColor="#f59e0b",
                )

                agraph(nodes=nodes, edges=edges, config=config)

            except ImportError:
                st.warning("Install `streamlit-agraph` for graph visualization.")
        else:
            st.info("Run an extraction to see the graph.")

    # ─── Pipeline Trace ──────────────────────────────────────────────
    with tab_trace:
        st.markdown(f"**Pipeline completed in `{result['processing_time_ms']}ms`**")

        expert_results = result.get("expert_results", {})
        for exp_name, stats in expert_results.items():
            with st.expander(
                f"{'🟢' if stats['entities'] > 0 else '⚪'} {exp_name} — "
                f"{stats['entities']} entities, {stats['relationships']} rels",
                expanded=(stats['entities'] > 0),
            ):
                st.markdown(f"- **Entities**: {stats['entities']}")
                st.markdown(f"- **Relationships**: {stats['relationships']}")
                st.markdown(f"- **Reasoning**: {stats['reasoning']}")

        # Expert breakdown chart
        if expert_results:
            st.divider()
            st.markdown("#### Expert Breakdown")
            import plotly.express as px
            exp_data = [
                {"Expert": k, "Entities": v["entities"], "Relationships": v["relationships"]}
                for k, v in expert_results.items()
            ]
            fig = px.bar(
                exp_data, x="Expert", y="Entities", color="Expert",
                color_discrete_sequence=["#6366f1", "#3b82f6", "#10b981", "#f59e0b", "#ef4444"],
            )
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#e2e8f0",
                showlegend=False, height=300,
            )
            st.plotly_chart(fig, use_container_width=True)

    # ── Raw JSON ──
    st.divider()
    with st.expander("📥 Raw JSON Output"):
        st.json(result)
