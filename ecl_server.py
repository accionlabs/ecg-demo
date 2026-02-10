#!/usr/bin/env python3
"""
ECL Studio Server - Backend API for the Low-Code Builder
Lightweight HTTP server using Python's built-in http.server (zero external deps).

Endpoints:
  GET  /                  → Serves ecl_studio.html
  POST /api/extract       → Run MoE extraction on submitted text
  GET  /api/experts       → List available experts
  GET  /api/connectors    → List available connectors
  GET  /api/governance    → Get governance/retention policy
  GET  /api/traces        → List recent traces
  GET  /api/health        → Health check
"""

import json
import os
import sys
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime

# Add ECL directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ecl_poc import Entity, Relationship, ExtractionResult, EntityType, MoEOrchestrator, ContextGraphBuilder
from ecl_tracing import (
    ExtractionTrace, PipelineTrace, hash_text, save_trace,
    validate_entity, apply_confidence_filter, MIN_CONFIDENCE,
    get_prompt_version, PROMPT_VERSIONS,
)
from ecl_connectors import ConnectorRegistry
from ecl_governance import GovernanceEngine

# Try to import LLM module (requires ecl_poc first)
try:
    from ecl_llm import LLMMoEOrchestrator, OllamaClient
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False


class ECLStudioHandler(SimpleHTTPRequestHandler):
    """HTTP handler for ECL Studio API."""

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self._serve_file("ecl_studio.html", "text/html")
        elif path == "/api/health":
            self._json_response(self._health_check())
        elif path == "/api/experts":
            self._json_response(self._list_experts())
        elif path == "/api/connectors":
            self._json_response(self._list_connectors())
        elif path == "/api/governance":
            self._json_response(self._get_governance())
        elif path == "/api/traces":
            self._json_response(self._list_traces())
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/extract":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(body)
                result = self._run_extraction(data)
                self._json_response(result)
            except Exception as e:
                self._json_response({"error": str(e)}, status=500)
        else:
            self.send_error(404, "Not Found")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def _serve_file(self, filename, content_type):
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', f'{content_type}; charset=utf-8')
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
        else:
            self.send_error(404, f"File not found: {filename}")

    def _json_response(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode('utf-8'))

    def _health_check(self):
        ollama_ok = False
        if LLM_AVAILABLE:
            try:
                import os
                ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
                client = OllamaClient(base_url=ollama_host)
                ollama_ok = client.is_available()
            except:
                pass
        return {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "llm_module": LLM_AVAILABLE,
            "ollama_available": ollama_ok,
            "model": "llama3:8b",
            "min_confidence": MIN_CONFIDENCE,
        }

    def _list_experts(self):
        experts = [
            {"name": "ContractExpert", "domain": "Contracts & Agreements", "type": "regex", "icon": "📄"},
            {"name": "EquipmentExpert", "domain": "Equipment & Assets", "type": "regex", "icon": "⚙️"},
            {"name": "FinancialRiskExpert", "domain": "Financial Risks", "type": "regex", "icon": "💰"},
            {"name": "OpportunityExpert", "domain": "Business Opportunities", "type": "regex", "icon": "🎯"},
            {"name": "HealthcareExpert", "domain": "Healthcare Records", "type": "regex", "icon": "🏥"},
        ]
        if LLM_AVAILABLE:
            for e in experts[:4]:
                e["llm_variant"] = f"LLM{e['name']}"
                e["type"] = "llm+regex"
        return {"experts": experts, "total": len(experts)}

    def _list_connectors(self):
        registry = ConnectorRegistry()
        return {"connectors": registry.list_connectors()}

    def _get_governance(self):
        engine = GovernanceEngine()
        return engine.compliance_report()

    def _list_traces(self):
        traces_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "traces")
        if not os.path.isdir(traces_dir):
            return {"traces": [], "total": 0}
        files = sorted([f for f in os.listdir(traces_dir) if f.endswith('.json')], reverse=True)
        traces = []
        for f in files[:20]:
            fpath = os.path.join(traces_dir, f)
            with open(fpath) as fp:
                traces.append(json.load(fp))
        return {"traces": traces, "total": len(files)}

    def _run_extraction(self, data):
        text = data.get("text", "")
        use_llm = data.get("use_llm", False)
        confidence_threshold = data.get("confidence_threshold", MIN_CONFIDENCE)
        selected_experts = data.get("experts", [])

        if not text.strip():
            return {"error": "No text provided"}

        start_time = time.time()

        # Choose orchestrator
        if use_llm and LLM_AVAILABLE:
            orchestrator = LLMMoEOrchestrator(model=data.get("model", "llama3:8b"))
            results = orchestrator.extract_all(text)
            trace = orchestrator.last_pipeline_trace
        else:
            orchestrator = MoEOrchestrator()
            results = orchestrator.extract_all(text)
            trace = None

        # Build graph
        graph_builder = ContextGraphBuilder()
        graph_builder.add_extraction_results(results)

        # Serialize results
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

        relationships = []
        for rel in graph_builder.edges:
            relationships.append({
                "source": rel.source_id,
                "target": rel.target_id,
                "type": rel.type.value,
                "confidence": rel.confidence,
            })

        elapsed_ms = (time.time() - start_time) * 1000

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
            "model": "llama3:8b" if use_llm else "regex",
            "confidence_threshold": confidence_threshold,
            "trace_id": trace.pipeline_id if trace else None,
        }

    def log_message(self, format, *args):
        """Suppress default logging for clean output."""
        if '/api/' in str(args[0]) or args[0] == '"GET / HTTP/1.1"':
            sys.stderr.write(f"  [{datetime.now().strftime('%H:%M:%S')}] {args[0]}\n")


def main():
    port = 8765
    print("=" * 60)
    print("  🧪 ECL Studio — Low-Code Builder")
    print("=" * 60)
    print(f"  Server:    http://localhost:{port}")
    print(f"  LLM:       {'✓ Available' if LLM_AVAILABLE else '○ Regex-only mode'}")
    print(f"  Confidence: {MIN_CONFIDENCE}")
    print(f"  Prompts:   {len(PROMPT_VERSIONS)} versioned")
    print("=" * 60)
    print("  Press Ctrl+C to stop\n")

    server = HTTPServer(('localhost', port), ECLStudioHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
