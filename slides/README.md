# ECL Slide Assets (Updated Feb 2026)

## Generated Images (in `/slides/`)

| Slide | File | Description | Status |
|-------|------|-------------|--------|
| 1: Title | `slide1_hero.png` | Tower with graph overlay | ✅ |
| 3: ETL Limitation | `slide3_pie_chart.png` | 80/20 data composition | ✅ |
| 4: Hallucination | `slide4_hallucination_chart.png` | RAG vs Knowledge Graphs | ✅ |
| 5: ECL Workflow | `slide5_ecl_workflow.png` | Extract → Build → Link | ✅ |
| 6: ETL vs ECL | `slide6_etl_vs_ecl.png` | Side-by-side comparison | ✅ |
| 7: Engineer Evolution | `slide7_engineer_evolution.png` | Pipeline → Context Architect | ✅ |
| 8: Market | `slide8_market_matrix.png` | Vendor landscape matrix | ✅ |
| 9: Architecture | `slide9_6layer_architecture.png` | 6-layer stack | 🔄 Regen (new layers) |
| 10: Tech Stack | `slide10_tech_stack.png` | Full pipeline + modules | 🔄 Regen (new modules) |
| 11: ECL Studio | — | Screenshot from localhost:8765 | 🆕 NEW |
| 12: Demo Input | `slide11_demo_input.png` | Tower report screenshot | ✅ |
| 13: Graph Output | `diagrams.md` | Live demo + trace output | 📝 |
| 15: ECL vs Lyzr | — | Screenshot ECL_ARCHITECTURE.html | 🆕 NEW |

## New Slides in this Update

| # | Title | What Changed |
|---|-------|-------------|
| 11 | ECL Studio | **NEW** — Low-code builder screenshot |
| 15 | ECL vs Lyzr | **NEW** — Competitive comparison |
| 9 | Architecture | **UPDATED** — Connectors, tracing, governance layers |
| 10 | Tech Stack | **UPDATED** — New modules: tracing, connectors, governance, studio |

## Quick Demo Commands

```bash
# Pre-flight
python3 test_ecl.py              # 29/29 tests

# Demo options
python3 ecl_poc.py               # Regex extraction
python3 ecl_llm.py --test        # LLM extraction + tracing
python3 ecl_falkordb.py --test   # Live graph + MCP
python3 ecl_server.py            # ECL Studio at :8765

# Connector check
python3 ecl_connectors.py        # List connectors & status

# Governance check
python3 ecl_governance.py        # Retention policy report
```

## File Quick Links

- [Demo Playbook](../DEMO_PLAYBOOK.md)
- [ECL Architecture vs Lyzr](../ECL_ARCHITECTURE.html)
- [ECL Studio](../ecl_studio.html)
- [Sample Tower Report](../sample_documents/tower_site_report_T789.md)
- [Test Suite](../test_ecl.py)
