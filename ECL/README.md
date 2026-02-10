# ECL — Entity-Context-Linking

> **Transform 80% of enterprise data that ETL ignores into AI-ready knowledge graphs.**

ECL is a Mixture-of-Experts (MoE) extraction pipeline that converts unstructured documents into typed entity graphs stored in FalkorDB — enabling AI agents to reason over enterprise knowledge with full traceability and zero cloud LLM cost.

## Architecture

```
Document → 5 MoE Experts → Validation → Ollama LLM → FalkorDB → MCP Tools → AI Agents
```

| Layer | Components |
|-------|-----------|
| **Extraction** | ContractExpert, EquipmentExpert, FinancialRiskExpert, OpportunityExpert, HealthcareExpert |
| **Validation** | Hallucination guard, confidence guardrails (≥0.70), entity grounding, pipeline tracing |
| **Knowledge** | FalkorDB graph — typed entities, weighted relationships, Cypher queries |
| **Orchestration** | 6 MCP tools — `get_tower_context`, `find_opportunities`, `assess_risk`, `search_entities`, `get_trace` |
| **Consumption** | ECL Studio (low-code builder), AI agents, copilots |

## Quick Start

### Prerequisites
- Python 3.10+
- [Ollama](https://ollama.ai) running locally with `llama3:8b`
- [FalkorDB](https://www.falkordb.com) running on `localhost:6379`

### Run Extraction
```bash
python3 ecl_poc.py
```

### Launch ECL Studio
```bash
python3 ecl_server.py
# Open http://localhost:8765
```

### Run Tests
```bash
python3 -m pytest test_ecl.py -v
```

## Project Structure

```
ECL/
├── ecl_poc.py              # Core extraction pipeline (5 MoE experts)
├── ecl_llm.py              # Ollama LLM integration (model/prompt versioning)
├── ecl_falkordb.py          # FalkorDB graph operations
├── ecl_tracing.py           # Agent tracing + audit trail
├── ecl_connectors.py        # Enterprise connectors (SharePoint, Dynamics 365, ServiceNow)
├── ecl_governance.py        # Data governance + retention policies
├── ecl_server.py            # ECL Studio backend (zero-dependency HTTP)
├── ecl_studio.html          # ECL Studio low-code builder UI
├── ECL_ARCHITECTURE.html    # ECL vs Lyzr architecture comparison
├── test_ecl.py              # Test suite (29 tests)
├── DEMO_PLAYBOOK.md         # Demo script (6 acts)
├── HEART_BEAT.MD            # Activity log
├── sample_documents/        # Sample tower site reports
├── lib/                     # Frontend libraries (vis.js, tom-select)
└── slides/                  # Presentation assets
    ├── PLUSAI_PROMPTS.md     # 18 slide prompts
    ├── SPEAKER_NOTES.md     # Speaker script
    └── *.png / *.html       # Slide images + sources
```

## Key Differentiators

| Feature | ECL | Traditional RAG |
|---------|-----|-----------------|
| Extraction | 5 domain-specialized MoE experts | Generic embeddings |
| Knowledge | Typed graph with weighted relationships | Flat vector store |
| Traceability | Full pipeline trace per entity | None |
| Hallucination | Source-text validation + confidence guardrails | None |
| LLM Cost | $0 (local Ollama) | $$$  (cloud APIs) |
| Data Residency | 100% on-premise | Cloud |

## License

Proprietary — Accion Labs. All rights reserved.
