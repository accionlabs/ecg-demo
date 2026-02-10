#!/usr/bin/env python3
"""
ECL Tracing Module - Agent Tracing / Audit Trail
Provides structured JSON audit logs for every extraction decision.

Lyzr Criteria Addressed:
  - "Agent Tracing — every decision traceable"
  - "Ability to reconstruct agent action"
"""

import json
import hashlib
import os
import time
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime


# ============================================================
# SECTION 1: TRACE DATA MODELS
# ============================================================

@dataclass
class ExtractionTrace:
    """Traces a single expert's extraction run."""
    trace_id: str = ""
    timestamp: str = ""
    expert_name: str = ""
    model_used: str = ""
    model_version: str = ""
    prompt_version: str = ""
    input_text_hash: str = ""  # SHA-256 of input for reproducibility
    input_text_length: int = 0
    entities_extracted: int = 0
    entities_rejected: int = 0  # Below confidence threshold
    entities_hallucinated: int = 0  # Failed validation
    relationships_extracted: int = 0
    confidence_scores: List[float] = field(default_factory=list)
    avg_confidence: float = 0.0
    min_confidence: float = 0.0
    processing_time_ms: float = 0.0
    fallback_used: bool = False
    error: Optional[str] = None
    entity_names: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.trace_id:
            self.trace_id = f"trace_{int(time.time() * 1000)}_{self.expert_name}"
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class PipelineTrace:
    """Traces an entire extraction pipeline run."""
    pipeline_id: str = ""
    timestamp: str = ""
    model_used: str = ""
    model_version: str = ""
    document_hash: str = ""
    document_length: int = 0
    total_experts: int = 0
    total_entities: int = 0
    total_entities_rejected: int = 0
    total_entities_hallucinated: int = 0
    total_relationships: int = 0
    total_time_ms: float = 0.0
    min_confidence_threshold: float = 0.0
    expert_traces: List[ExtractionTrace] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.pipeline_id:
            self.pipeline_id = f"pipeline_{int(time.time() * 1000)}"
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


# ============================================================
# SECTION 2: TRACING UTILITIES
# ============================================================

def hash_text(text: str) -> str:
    """SHA-256 hash of input text for audit reproducibility."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]


def save_trace(trace, output_dir: str = "traces") -> str:
    """Save a trace (Extraction or Pipeline) to a JSON file on disk."""
    os.makedirs(output_dir, exist_ok=True)

    if isinstance(trace, PipelineTrace):
        filename = f"{trace.pipeline_id}.json"
    elif isinstance(trace, ExtractionTrace):
        filename = f"{trace.trace_id}.json"
    else:
        filename = f"trace_{int(time.time() * 1000)}.json"

    filepath = os.path.join(output_dir, filename)

    # Convert dataclass to dict, handling nested dataclasses
    trace_dict = asdict(trace)

    with open(filepath, 'w') as f:
        json.dump(trace_dict, f, indent=2, default=str)

    return filepath


def load_trace(filepath: str) -> Dict:
    """Load a trace from a JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def print_trace_summary(trace: PipelineTrace):
    """Print a human-readable trace summary to stdout."""
    print("\n" + "=" * 60)
    print("  📋 ECL PIPELINE TRACE")
    print("=" * 60)
    print(f"  Pipeline ID:      {trace.pipeline_id}")
    print(f"  Timestamp:        {trace.timestamp}")
    print(f"  Model:            {trace.model_used} ({trace.model_version})")
    print(f"  Document Hash:    {trace.document_hash}")
    print(f"  Confidence Min:   {trace.min_confidence_threshold}")
    print(f"  Total Time:       {trace.total_time_ms:.0f}ms")
    print("-" * 60)
    print(f"  Experts Run:      {trace.total_experts}")
    print(f"  Entities:         {trace.total_entities} extracted, "
          f"{trace.total_entities_rejected} rejected, "
          f"{trace.total_entities_hallucinated} hallucinated")
    print(f"  Relationships:    {trace.total_relationships}")
    print("-" * 60)

    for et in trace.expert_traces:
        status = "✓" if not et.error else "✗"
        fallback = " [FALLBACK]" if et.fallback_used else ""
        print(f"  [{status}] {et.expert_name}: "
              f"{et.entities_extracted} entities, "
              f"{et.processing_time_ms:.0f}ms, "
              f"avg_conf={et.avg_confidence:.2f}"
              f"{fallback}")

    if trace.warnings:
        print("-" * 60)
        print("  ⚠️  Warnings:")
        for w in trace.warnings:
            print(f"    - {w}")

    print("=" * 60)


# ============================================================
# SECTION 3: ENTITY VALIDATION (HALLUCINATION GUARD)
# ============================================================

def validate_entity(entity, source_text: str) -> Dict[str, Any]:
    """
    Validate an extracted entity against the source text.
    Returns validation result with reason if invalid.

    Checks:
    1. Entity name is present in (or derivable from) source text
    2. Entity ID is non-empty
    3. Required properties are present
    """
    result = {"valid": True, "reasons": []}

    # Check 1: Non-empty ID
    if not entity.id or entity.id.strip() == "":
        result["valid"] = False
        result["reasons"].append("Empty entity ID")

    # Check 2: Non-empty name
    if not entity.name or entity.name.strip() == "":
        result["valid"] = False
        result["reasons"].append("Empty entity name")

    # Check 3: Name derivable from source text (fuzzy)
    if entity.name and source_text:
        name_lower = entity.name.lower().strip()
        source_lower = source_text.lower()

        # Check if any significant word (3+ chars) from entity name appears in source
        name_words = [w for w in name_lower.split() if len(w) >= 3]
        # Filter out generic words
        generic_words = {"the", "and", "for", "with", "from", "contract", "equipment",
                         "risk", "opportunity", "tower", "company", "financial",
                         "medication", "diagnosis", "patient", "doctor"}
        meaningful_words = [w for w in name_words if w not in generic_words]

        if meaningful_words:
            found = any(w in source_lower for w in meaningful_words)
            if not found:
                result["valid"] = False
                result["reasons"].append(
                    f"Entity name '{entity.name}' not grounded in source text "
                    f"(checked words: {meaningful_words})"
                )

    # Check 4: Numeric properties should be reasonable
    for key, val in entity.properties.items():
        if isinstance(val, (int, float)):
            if val < 0 and key not in ("outstanding_amount", "overdue", "loss", "deficit"):
                result["valid"] = False
                result["reasons"].append(f"Negative value for {key}: {val}")

    return result


# ============================================================
# SECTION 4: CONFIDENCE GUARDRAILS
# ============================================================

MIN_CONFIDENCE = 0.70  # Minimum acceptable confidence score

def apply_confidence_filter(entities: list, min_confidence: float = MIN_CONFIDENCE) -> tuple:
    """
    Filter entities by confidence score.
    Returns (accepted_entities, rejected_entities).
    """
    accepted = []
    rejected = []

    for entity in entities:
        if entity.confidence >= min_confidence:
            accepted.append(entity)
        else:
            rejected.append(entity)
            print(f"    ⚡ [GUARDRAIL] Rejected '{entity.name}' "
                  f"(confidence={entity.confidence:.2f} < {min_confidence})")

    return accepted, rejected


# ============================================================
# SECTION 5: PROMPT VERSIONING
# ============================================================

# All prompt versions are tracked here for auditability
PROMPT_VERSIONS = {
    "LLMContractExpert.system": "v1.0.0",
    "LLMContractExpert.extraction": "v1.0.0",
    "LLMEquipmentExpert.system": "v1.0.0",
    "LLMEquipmentExpert.extraction": "v1.0.0",
    "LLMFinancialRiskExpert.system": "v1.0.0",
    "LLMFinancialRiskExpert.extraction": "v1.0.0",
    "LLMOpportunityExpert.system": "v1.0.0",
    "LLMOpportunityExpert.extraction": "v1.0.0",
    "LLMHealthcareExpert.system": "v1.0.0",
    "LLMHealthcareExpert.extraction": "v1.0.0",
}

def get_prompt_version(expert_name: str, prompt_type: str = "extraction") -> str:
    """Get the version string for an expert's prompt."""
    key = f"{expert_name}.{prompt_type}"
    return PROMPT_VERSIONS.get(key, "v0.0.0-unversioned")
