# 🎯 ECL Demo Playbook - Summit Presentation (Updated Feb 2026)

## Pre-Demo Setup
```bash
# Terminal 1: FalkorDB (Graph-Based Knowledge Store)
docker run -p 6379:6379 falkordb/falkordb

# Terminal 2: Ollama (Local LLM Inference)
ollama serve

# Terminal 3: ECL Studio (Low-Code Builder)
python3 ecl_server.py
# → Opens at http://localhost:8765
```

### Pre-Flight Checks
```bash
# Verify everything works
python3 test_ecl.py          # Should show: 29/29 passed
curl localhost:8765/api/health  # Should show: {"status": "ok", ...}
```

---

## Act 1: The Problem (30 sec)

> *"Traditional ETL moves data. ECL extracts meaning and makes it AI-queryable — with every decision traced."*

**Show:** `sample_documents/tower_site_report_T789.md`

**Key stats:**
- 6,233 characters of mixed structured/unstructured data
- Contracts, financials, drone observations, opportunities

**Pitch:**
> *"An analyst needs 20 minutes per document. At enterprise scale — 10,000 towers, 120,000 reports/year — that's 40,000 labor hours annually."*

---

## Act 2: ECL Studio — Low-Code Builder ⭐ NEW (1 min)

**[Open browser → http://localhost:8765]**

> *"Before I show you the engine, let me show you the experience. This is ECL Studio."*

**Demo flow:**
1. **Show sidebar** → "Toggle experts on/off. Adjust confidence threshold. Pick your model."
2. **Click 'Load Sample'** → Tower report loads
3. **Click 'Extract Entities'** → Results appear
4. **Point to results** → "23 entities, typed and confidence-scored"
5. **Point to trace panel** → "Full pipeline trace — which expert, how long, how many validated"

> *"A business analyst does this. No Python. No terminal. No data engineering degree."*

---

## Act 3: Under the Hood — MoE + Guardrails (1 min)

```bash
python3 ecl_llm.py --test
```

> *"Unlike pure RAG, ECL doesn't just retrieve — it extracts, validates, and persists."*

**New capabilities to point out:**
- ⏱️ Per-expert timing (e.g., `LLMContractExpert: 2340ms`)
- 🚫 Hallucination guard (`HALLUCINATION: Rejected 'entity'...`)
- ⚡ Confidence guardrails (`GUARDRAIL: Rejected below 0.70`)
- 📋 Pipeline trace saved to `traces/`

**Experts in action:**
- **ContractExpert** → structured contract entities + model version stamp
- **EquipmentExpert** → assets + drone cross-reference + validation
- **FinancialRiskExpert** → defaults, exposure + confidence scores
- **OpportunityExpert** → LLM reasoning for upsell signals

---

## Act 4: Live Graph Database ⭐ (2 min)

```bash
python3 ecl_falkordb.py --test
```

**Key moments:**
1. ✅ 23 nodes written to live graph
2. ✅ 22 real-time relationships
3. ✅ 6 MCP tools for AI agent integration
4. ✅ Full audit trail in `traces/` directory

**Demo queries:**
```python
mcp.get_tower_context("t789")   # Full entity context
mcp.find_opportunities()         # 8 opportunities detected
mcp.assess_risk()                # 10 risks identified
```

> *"An AI sales agent can now ask: 'What opportunities exist at Tower T-789?' and get grounded answers — 8 opportunities, 10 risks, all traceable to the source document."*

**Show audit trail:**
```bash
cat traces/*.json | python3 -m json.tool | head -30
```

> *"Every expert call logged: model, timing, entities accepted, entities rejected, confidence scores. This is enterprise-grade traceability."*

---

## Act 5: ECL vs Lyzr — Why We Win ⭐ NEW (1 min)

**[Open ECL_ARCHITECTURE.html in browser]**

> *"Lyzr AI just signed Crown Castle — $380K per year for contract data extraction. The exact same use case."*

**Hit these three points hard:**

1. **Quality:** "5 MoE domain experts vs generic RAG. Typed graph vs flat vectors."
2. **Price:** "$0 per year vs $380,000. Local Ollama vs cloud GPT-4."
3. **Security:** "Your data never leaves your servers. Theirs goes to cloud APIs."

> *"ECL wins 9 out of 10 criteria. Save $480K in Year 1."*

---

## Act 6: Enterprise ROI (30 sec)

| Manual Process | ECL Automation |
|----------------|----------------|
| 20 min/document | 15 seconds |
| 40,000 hours/year | 500 hours |
| $3M labor cost | $37K |
| 15% missed opportunities | 0% |
| + $380K Lyzr license | $0 |

**Total Annual Impact: $4.16M + $480K savings = $4.64M**

---

## The Vision

> *"ECL transforms documents into AI-queryable context graphs. It's not ETL — it's Entity-Context-Linking for the agentic era."*

**Differentiators:**
- ✅ **Hybrid AI** — Rules + LLM + Graph
- ✅ **Enterprise-Ready** — Tracing, Guardrails, Governance
- ✅ **Low-Code** — ECL Studio for non-technical users
- ✅ **$0 LLM Cost** — No cloud spend, no vendor lock-in
- ✅ **29 Tests Passing** — Production-grade

---

## Key Terminology (from AI Primer)

| Term | Definition | ECL Application |
|------|------------|-----------------| 
| **MoE** | Mixture of Experts — specialized models per domain | 5 domain experts (Contract, Equipment, Financial, Risk, Opportunity) |
| **RAG** | Retrieval-Augmented Generation | Graph queries provide grounded context |
| **MCP** | Model Context Protocol — structured tool interface | 6 tools: get_tower_context, find_opportunities, assess_risk, etc. |
| **Hallucination Guard** | Validating LLM outputs against source | Entity validation: name grounding + confidence threshold |
| **Agent Tracing** | Logging every decision for auditability | Pipeline traces saved to `traces/` as JSON |
| **Knowledge Graph** | Network of typed entities and relationships | FalkorDB with confidence-scored nodes/edges |

---

## Emergency Fallbacks

| If... | Then... |
|-------|---------| 
| Ollama down | Run `ecl_poc.py` (regex experts, still works) |
| FalkorDB down | Show `ecl_telecom_graph.cypher` |
| ECL Studio won't load | Open `ecl_studio.html` as static file |
| All fails | Open `ecl_telecom_graph.html` + `ECL_ARCHITECTURE.html` |

---

## Assets

| Asset | Purpose |
|-------|---------|
| `sample_documents/tower_site_report_T789.md` | Demo input document |
| `ecl_studio.html` | Low-code builder UI |
| `ecl_server.py` | Studio backend server |
| `ECL_ARCHITECTURE.html` | Competitive comparison page |
| `DEMO_PLAYBOOK.md` | This playbook |
| `traces/` | Audit trail directory (created on first run) |
| `test_ecl.py` | Test suite (29 tests) |
