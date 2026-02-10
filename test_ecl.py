#!/usr/bin/env python3
"""
ECL Test Suite - Automated Tests for All Gap Fixes
Tests: tracing, confidence guardrails, hallucination guard, timing,
       model versioning, connectors, governance.

Run: python3 test_ecl.py
"""

import sys
import os
import json
import time
from datetime import datetime

# Ensure ECL directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ============================================================
# TEST HELPERS
# ============================================================

class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def ok(self, name):
        self.passed += 1
        print(f"  ✓ {name}")

    def fail(self, name, reason=""):
        self.failed += 1
        self.errors.append((name, reason))
        print(f"  ✗ {name}: {reason}")

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"  Results: {self.passed}/{total} passed, {self.failed} failed")
        if self.errors:
            print(f"\n  Failures:")
            for name, reason in self.errors:
                print(f"    - {name}: {reason}")
        print(f"{'='*60}")
        return self.failed == 0


results = TestResult()


# ============================================================
# TEST 1: ecl_tracing.py
# ============================================================

def test_tracing():
    print("\n[TEST 1] ecl_tracing.py — Agent Tracing & Audit Trail")
    print("-" * 40)

    try:
        from ecl_tracing import (
            ExtractionTrace, PipelineTrace,
            hash_text, save_trace, load_trace,
            validate_entity, apply_confidence_filter,
            get_prompt_version, MIN_CONFIDENCE, PROMPT_VERSIONS,
        )
        results.ok("Import ecl_tracing")
    except ImportError as e:
        results.fail("Import ecl_tracing", str(e))
        return

    # Test hash_text
    h = hash_text("Hello World")
    assert len(h) == 16, f"Hash length should be 16, got {len(h)}"
    assert h == hash_text("Hello World"), "Hash should be deterministic"
    assert h != hash_text("Hello World!"), "Different input should hash differently"
    results.ok("hash_text deterministic")

    # Test ExtractionTrace creation
    trace = ExtractionTrace(expert_name="TestExpert", model_used="llama3:8b")
    assert trace.expert_name == "TestExpert"
    assert trace.trace_id.startswith("trace_")
    assert trace.timestamp != ""
    results.ok("ExtractionTrace creation")

    # Test PipelineTrace creation
    pipeline = PipelineTrace(model_used="llama3:8b")
    assert pipeline.pipeline_id.startswith("pipeline_")
    assert pipeline.expert_traces == []
    results.ok("PipelineTrace creation")

    # Test save/load trace
    os.makedirs("test_traces", exist_ok=True)
    path = save_trace(trace, "test_traces")
    assert os.path.exists(path), f"Trace file not created at {path}"
    loaded = load_trace(path)
    assert loaded["expert_name"] == "TestExpert"
    results.ok("save_trace / load_trace")

    # Cleanup
    os.remove(path)
    os.rmdir("test_traces")

    # Test MIN_CONFIDENCE
    assert MIN_CONFIDENCE == 0.70, f"MIN_CONFIDENCE should be 0.70, got {MIN_CONFIDENCE}"
    results.ok("MIN_CONFIDENCE = 0.70")

    # Test prompt versioning
    assert "LLMContractExpert.system" in PROMPT_VERSIONS
    v = get_prompt_version("LLMContractExpert", "system")
    assert v == "v1.0.0"
    v_unknown = get_prompt_version("UnknownExpert")
    assert v_unknown == "v0.0.0-unversioned"
    results.ok("Prompt versioning")


# ============================================================
# TEST 2: Entity Validation (Hallucination Guard)
# ============================================================

def test_entity_validation():
    print("\n[TEST 2] Entity Validation — Hallucination Guard")
    print("-" * 40)

    from ecl_tracing import validate_entity
    from ecl_poc import Entity, EntityType

    source = "Contract #1001 with TechCorp. Monthly revenue: $5000. Status: Active."

    # Valid entity
    e1 = Entity(id="contract_1001", type=EntityType.CONTRACT, name="Contract #1001",
                properties={"company": "TechCorp", "monthly_revenue": 5000})
    v1 = validate_entity(e1, source)
    assert v1["valid"] == True, f"Should be valid: {v1['reasons']}"
    results.ok("Valid entity passes validation")

    # Invalid: empty ID
    e2 = Entity(id="", type=EntityType.CONTRACT, name="Test")
    v2 = validate_entity(e2, source)
    assert v2["valid"] == False
    assert any("Empty entity ID" in r for r in v2["reasons"])
    results.ok("Empty ID flagged as invalid")

    # Invalid: empty name
    e3 = Entity(id="test_1", type=EntityType.CONTRACT, name="")
    v3 = validate_entity(e3, source)
    assert v3["valid"] == False
    results.ok("Empty name flagged as invalid")

    # Invalid: hallucinated name (not in source text)
    e4 = Entity(id="contract_9999", type=EntityType.CONTRACT, name="MegaCorp Platinum Deal")
    v4 = validate_entity(e4, source)
    assert v4["valid"] == False
    assert any("not grounded" in r for r in v4["reasons"])
    results.ok("Hallucinated entity detected")


# ============================================================
# TEST 3: Confidence Guardrails
# ============================================================

def test_confidence_guardrails():
    print("\n[TEST 3] Confidence Guardrails")
    print("-" * 40)

    from ecl_tracing import apply_confidence_filter
    from ecl_poc import Entity, EntityType

    entities = [
        Entity(id="e1", type=EntityType.CONTRACT, name="High", confidence=0.95),
        Entity(id="e2", type=EntityType.CONTRACT, name="Medium", confidence=0.75),
        Entity(id="e3", type=EntityType.CONTRACT, name="Low", confidence=0.50),
        Entity(id="e4", type=EntityType.CONTRACT, name="VeryLow", confidence=0.30),
    ]

    accepted, rejected = apply_confidence_filter(entities, 0.70)
    assert len(accepted) == 2, f"Should accept 2, got {len(accepted)}"
    assert len(rejected) == 2, f"Should reject 2, got {len(rejected)}"
    assert accepted[0].name == "High"
    assert accepted[1].name == "Medium"
    results.ok("Confidence filter accepts/rejects correctly")

    # Edge case: exactly at threshold
    edge = [Entity(id="e5", type=EntityType.CONTRACT, name="Edge", confidence=0.70)]
    acc, rej = apply_confidence_filter(edge, 0.70)
    assert len(acc) == 1, "Confidence == threshold should be accepted"
    results.ok("Edge case: exact threshold accepted")


# ============================================================
# TEST 4: Connectors
# ============================================================

def test_connectors():
    print("\n[TEST 4] ecl_connectors.py — Enterprise Connectors")
    print("-" * 40)

    try:
        from ecl_connectors import (
            ConnectorRegistry, FileSystemConnector,
            SharePointConnector, Dynamics365Connector,
            ServiceNowConnector, DocumentMetadata,
        )
        results.ok("Import ecl_connectors")
    except ImportError as e:
        results.fail("Import ecl_connectors", str(e))
        return

    # Test registry
    registry = ConnectorRegistry()
    available = registry.list_available()
    assert "filesystem" in available
    assert "sharepoint" in available
    assert "dynamics365" in available
    assert "servicenow" in available
    results.ok(f"Registry has {len(available)} connectors")

    # Test FileSystem connector (fully functional)
    fs = registry.get("filesystem")
    connected = fs.connect(base_path=".")
    assert connected == True
    assert fs.connected == True
    results.ok("FileSystem connector connects")

    docs = fs.list_documents()
    assert isinstance(docs, list)
    results.ok(f"FileSystem lists {len(docs)} documents")

    # Test health check
    statuses = registry.list_connectors()
    assert len(statuses) == 4
    results.ok("Health check returns all connectors")


# ============================================================
# TEST 5: Governance
# ============================================================

def test_governance():
    print("\n[TEST 5] ecl_governance.py — Data Governance")
    print("-" * 40)

    try:
        from ecl_governance import GovernanceEngine, RetentionPolicy
        results.ok("Import ecl_governance")
    except ImportError as e:
        results.fail("Import ecl_governance", str(e))
        return

    # Test default policy
    engine = GovernanceEngine(governance_dir="test_governance")
    policy = engine.get_policy()
    assert policy["retention_days"] == 365
    assert policy["audit_retention_days"] == 2555
    results.ok("Default retention policy loaded")

    # Test retention check
    check = engine.check_retention(datetime.now().isoformat(), "data")
    assert check["expired"] == False
    assert check["action"] == "RETAIN"
    results.ok("Recent data retained correctly")

    # Test old data
    old_date = (datetime.now() - __import__("datetime").timedelta(days=400)).isoformat()
    check_old = engine.check_retention(old_date, "data")
    assert check_old["expired"] == True
    assert check_old["action"] == "PURGE"
    results.ok("Expired data flagged for purge")

    # Test compliance report
    report = engine.compliance_report()
    assert "policy" in report
    assert "generated_at" in report
    results.ok("Compliance report generated")

    # Cleanup
    import shutil
    if os.path.exists("test_governance"):
        shutil.rmtree("test_governance")


# ============================================================
# TEST 6: ecl_poc.py base types
# ============================================================

def test_base_types():
    print("\n[TEST 6] ecl_poc.py — Base Types & Orchestrator")
    print("-" * 40)

    try:
        from ecl_poc import (
            Entity, Relationship, ExtractionResult,
            EntityType, RelationshipType, Severity,
            MoEOrchestrator, ContextGraphBuilder,
        )
        results.ok("Import ecl_poc base types")
    except ImportError as e:
        results.fail("Import ecl_poc", str(e))
        return

    # Test Entity creation
    e = Entity(id="test_1", type=EntityType.CONTRACT, name="Test Contract",
               properties={"value": 100}, source_expert="test", confidence=0.9)
    assert e.id == "test_1"
    assert e.type == EntityType.CONTRACT
    results.ok("Entity dataclass creation")

    # Test ContextGraphBuilder
    gb = ContextGraphBuilder()
    result = ExtractionResult(
        expert_name="test",
        entities=[e],
        relationships=[],
    )
    gb.add_extraction_results({"test": result})
    assert len(gb.nodes) == 1
    assert "test_1" in gb.nodes
    results.ok("ContextGraphBuilder merges entities")


# ============================================================
# TEST 7: ecl_llm.py integration (import only, no Ollama needed)
# ============================================================

def test_llm_module():
    print("\n[TEST 7] ecl_llm.py — LLM Module Integration")
    print("-" * 40)

    try:
        from ecl_llm import (
            OllamaClient, LLMBaseExpert, LLMMoEOrchestrator,
            LLMContractExpert, LLMEquipmentExpert,
        )
        results.ok("Import ecl_llm (with tracing integration)")
    except ImportError as e:
        results.fail("Import ecl_llm", str(e))
        return

    # Test OllamaClient creation
    client = OllamaClient(model="llama3:8b")
    assert client.model == "llama3:8b"
    results.ok("OllamaClient creation")

    # Test Orchestrator creation
    orch = LLMMoEOrchestrator(model="llama3:8b")
    assert len(orch.experts) == 4
    assert orch.last_pipeline_trace is None
    results.ok("LLMMoEOrchestrator has 4 experts + trace attribute")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  ECL Test Suite")
    print(f"  {datetime.now().isoformat()}")
    print("=" * 60)

    test_tracing()
    test_entity_validation()
    test_confidence_guardrails()
    test_connectors()
    test_governance()
    test_base_types()
    test_llm_module()

    success = results.summary()
    sys.exit(0 if success else 1)
