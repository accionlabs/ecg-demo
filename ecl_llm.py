#!/usr/bin/env python3
"""
ECL LLM Module - Ollama-Powered Mixture of Experts Extraction
Uses local LLMs via Ollama for high-quality entity extraction.

Features: Agent Tracing, Confidence Guardrails, Hallucination Controls,
          Processing Time Metrics, Model Versioning, Prompt Versioning
"""

import json
import re
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from datetime import datetime

# Import tracing, validation, guardrails
from ecl_tracing import (
    ExtractionTrace, PipelineTrace,
    hash_text, save_trace, print_trace_summary,
    validate_entity, apply_confidence_filter,
    get_prompt_version, MIN_CONFIDENCE,
)

# Import base types from ecl_poc
from ecl_poc import (
    Entity, Relationship, ExtractionResult,
    EntityType, RelationshipType, Severity,
    BaseExpert, MoEOrchestrator, ContextGraphBuilder,
    ContractExpert, EquipmentExpert, FinancialRiskExpert, OpportunityExpert, HealthcareExpert
)


# ============================================================
# SECTION 1: OLLAMA CLIENT
# ============================================================

class OllamaClient:
    """HTTP client for Ollama API with health checking and retry."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3:8b"):
        self.base_url = base_url
        self.model = model
        self._available = None

    def is_available(self) -> bool:
        """Check if Ollama server is running."""
        if self._available is not None:
            return self._available
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=2) as response:
                self._available = response.status == 200
        except (urllib.error.URLError, TimeoutError):
            self._available = False
        return self._available

    def generate(self, prompt: str, system: str = "", format_json: bool = True) -> Optional[Dict]:
        """Generate completion from Ollama model."""
        if not self.is_available():
            return None

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # Low temp for consistent extraction
                "num_predict": 2048,
                "num_ctx": 8192,  # Use full model context capacity
            }
        }

        if system:
            payload["system"] = system

        if format_json:
            payload["format"] = "json"

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url}/api/generate",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode("utf-8"))
                response_text = result.get("response", "")

                if format_json:
                    try:
                        return json.loads(response_text)
                    except json.JSONDecodeError:
                        # Try to extract JSON from response
                        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                        if json_match:
                            return json.loads(json_match.group())
                        return None
                return {"text": response_text}

        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            print(f"    [Ollama Error] {e}")
            return None


# ============================================================
# SECTION 2: LLM BASE EXPERT
# ============================================================

class LLMBaseExpert(BaseExpert):
    """Base class for LLM-powered extraction experts."""

    def __init__(self, name: str, client: OllamaClient, fallback_expert: BaseExpert = None):
        super().__init__(name)
        self.client = client
        self.fallback = fallback_expert

    def get_system_prompt(self) -> str:
        """Override in subclass for domain-specific system prompt."""
        return "You are an entity extraction expert. Extract structured data and return valid JSON."

    def get_extraction_prompt(self, text: str) -> str:
        """Override in subclass for domain-specific extraction prompt."""
        raise NotImplementedError

    def parse_llm_response(self, response: Dict) -> ExtractionResult:
        """Override in subclass to parse LLM JSON into entities/relationships."""
        raise NotImplementedError

    def extract(self, text: str, context: Dict = None) -> ExtractionResult:
        """
        Extract entities using LLM, with fallback to regex expert.
        Includes: timing, model versioning, entity validation, confidence guardrails.
        """
        start_time = time.time()
        fallback_used = False
        model_version = self.client.model if self.client else "unknown"
        prompt_ver = get_prompt_version(self.name)

        # --- Trace record for this extraction ---
        trace = ExtractionTrace(
            expert_name=self.name,
            model_used=model_version,
            model_version=model_version,
            prompt_version=prompt_ver,
            input_text_hash=hash_text(text),
            input_text_length=len(text),
        )

        if not self.client.is_available():
            if self.fallback:
                print(f"    [LLM] Ollama unavailable, using regex fallback for {self.name}")
                fallback_used = True
                result = self.fallback.extract(text, context)
                trace.fallback_used = True
                trace.processing_time_ms = (time.time() - start_time) * 1000
                self._last_trace = trace
                return result
            return ExtractionResult(expert_name=self.name, reasoning="Ollama unavailable")

        prompt = self.get_extraction_prompt(text)
        system = self.get_system_prompt()

        response = self.client.generate(prompt, system=system, format_json=True)

        if response is None:
            if self.fallback:
                print(f"    [LLM] Extraction failed, using regex fallback for {self.name}")
                fallback_used = True
                result = self.fallback.extract(text, context)
                trace.fallback_used = True
                trace.processing_time_ms = (time.time() - start_time) * 1000
                self._last_trace = trace
                return result
            return ExtractionResult(expert_name=self.name, reasoning="LLM extraction failed")

        try:
            result = self.parse_llm_response(response)
            result.reasoning = f"[LLM] {result.reasoning}"

            # --- MODEL VERSIONING: stamp each entity ---
            for entity in result.entities:
                entity.properties["_model_version"] = model_version
                entity.properties["_prompt_version"] = prompt_ver
                entity.properties["_extracted_by"] = self.name

            # --- ENTITY VALIDATION (Hallucination Guard) ---
            validated_entities = []
            hallucinated_count = 0
            for entity in result.entities:
                validation = validate_entity(entity, text)
                if validation["valid"]:
                    validated_entities.append(entity)
                else:
                    hallucinated_count += 1
                    entity.confidence = 0.0  # Mark as hallucinated
                    print(f"    🚫 [HALLUCINATION] Rejected '{entity.name}': "
                          f"{'; '.join(validation['reasons'])}")
            result.entities = validated_entities

            # --- CONFIDENCE GUARDRAILS ---
            accepted, rejected = apply_confidence_filter(result.entities, MIN_CONFIDENCE)
            result.entities = accepted

            # --- TIMING ---
            elapsed_ms = (time.time() - start_time) * 1000
            print(f"    ⏱️  {self.name}: {elapsed_ms:.0f}ms")

            # --- UPDATE TRACE ---
            trace.entities_extracted = len(accepted)
            trace.entities_rejected = len(rejected)
            trace.entities_hallucinated = hallucinated_count
            trace.relationships_extracted = len(result.relationships)
            trace.confidence_scores = [e.confidence for e in accepted]
            trace.avg_confidence = sum(trace.confidence_scores) / len(trace.confidence_scores) if trace.confidence_scores else 0.0
            trace.min_confidence = min(trace.confidence_scores) if trace.confidence_scores else 0.0
            trace.processing_time_ms = elapsed_ms
            trace.entity_names = [e.name for e in accepted]
            self._last_trace = trace

            return result
        except Exception as e:
            print(f"    [LLM Parse Error] {e}")
            trace.error = str(e)
            trace.processing_time_ms = (time.time() - start_time) * 1000
            self._last_trace = trace
            if self.fallback:
                return self.fallback.extract(text, context)
            return ExtractionResult(expert_name=self.name, reasoning=f"Parse error: {e}")


# ============================================================
# SECTION 3: LLM CONTRACT EXPERT
# ============================================================

class LLMContractExpert(LLMBaseExpert):
    """LLM-powered contract extraction expert."""

    def __init__(self, client: OllamaClient):
        super().__init__("LLMContractExpert", client, ContractExpert())

    def get_system_prompt(self) -> str:
        return """You are a contract analysis expert. Extract contract entities from telecom tower documents.
Return valid JSON with the structure: {"contracts": [...], "companies": [...]}"""

    def get_extraction_prompt(self, text: str) -> str:
        return f"""Analyze this telecom tower document and extract ALL contracts and companies.

For each CONTRACT extract:
- contract_id: The contract number/ID
- company: Company name (tenant)
- status: Active, Defaulted, Expired, Pending, or Suspended
- occupancy_pct: Occupancy percentage (0-100)
- monthly_revenue: Monthly revenue amount
- outstanding_amount: Any outstanding/overdue amount

For each COMPANY extract:
- name: Company name
- is_active: true/false

DOCUMENT:
{text}

Return JSON format:
{{
  "contracts": [
    {{"contract_id": "...", "company": "...", "status": "...", "occupancy_pct": 0, "monthly_revenue": 0, "outstanding_amount": 0}}
  ],
  "companies": [
    {{"name": "...", "is_active": true}}
  ]
}}"""

    def parse_llm_response(self, response: Dict) -> ExtractionResult:
        result = ExtractionResult(expert_name=self.name)

        contracts = response.get("contracts", [])
        companies = response.get("companies", [])

        for c in contracts:
            contract_id = str(c.get("contract_id", "unknown"))
            entity = Entity(
                id=f"contract_{contract_id}",
                type=EntityType.CONTRACT,
                name=f"Contract #{contract_id}",
                properties={
                    "contract_id": contract_id,
                    "company": c.get("company", ""),
                    "status": c.get("status", "UNKNOWN").upper(),
                    "occupancy_pct": c.get("occupancy_pct", 0),
                    "monthly_revenue": c.get("monthly_revenue", 0),
                    "outstanding_amount": c.get("outstanding_amount", 0),
                },
                source_expert=self.name,
                confidence=0.95  # LLM extractions get higher confidence
            )
            result.entities.append(entity)

        for comp in companies:
            name = comp.get("name", "Unknown")
            entity = Entity(
                id=f"company_{name.lower().replace(' ', '_')}",
                type=EntityType.COMPANY,
                name=name,
                properties={
                    "name": name,
                    "is_active": comp.get("is_active", True),
                },
                source_expert=self.name,
                confidence=0.96
            )
            result.entities.append(entity)

            # Create HAS_CONTRACT relationships
            for c in contracts:
                if c.get("company", "").lower() == name.lower():
                    result.relationships.append(Relationship(
                        source_id=entity.id,
                        target_id=f"contract_{c.get('contract_id', '')}",
                        type=RelationshipType.HAS_CONTRACT,
                        properties={"status": c.get("status", "")},
                        confidence=0.95
                    ))

        result.reasoning = f"Extracted {len(contracts)} contracts and {len(companies)} companies via LLM"
        return result


# ============================================================
# SECTION 4: LLM EQUIPMENT EXPERT
# ============================================================

class LLMEquipmentExpert(LLMBaseExpert):
    """LLM-powered equipment extraction expert."""

    def __init__(self, client: OllamaClient):
        super().__init__("LLMEquipmentExpert", client, EquipmentExpert())

    def get_system_prompt(self) -> str:
        return """You are a telecom equipment analysis expert. Extract equipment entities from tower reports and drone inspection data.
Return valid JSON with the structure: {"equipment": [...]}"""

    def get_extraction_prompt(self, text: str) -> str:
        return f"""Analyze this telecom tower document and extract ALL equipment mentioned.

For each piece of EQUIPMENT extract:
- name: Equipment name/type (e.g., "Verizon Antennas", "DISH Satellite Dish")
- equipment_type: antenna, radio, dish, panel, mounting, cable, etc.
- quantity: Number of items
- status: operational, inactive, damaged, rusted, degraded
- company: Which company owns it
- drone_observation: Any observation from drone inspection

DOCUMENT:
{text}

Return JSON format:
{{
  "equipment": [
    {{"name": "...", "equipment_type": "...", "quantity": 1, "status": "...", "company": "...", "drone_observation": "..."}}
  ]
}}"""

    def parse_llm_response(self, response: Dict) -> ExtractionResult:
        result = ExtractionResult(expert_name=self.name)

        equipment_list = response.get("equipment", [])

        for i, eq in enumerate(equipment_list):
            entity = Entity(
                id=f"equipment_{eq.get('name', 'unknown').lower().replace(' ', '_')}_{i}",
                type=EntityType.EQUIPMENT,
                name=eq.get("name", "Unknown Equipment"),
                properties={
                    "equipment_type": eq.get("equipment_type", ""),
                    "quantity": eq.get("quantity", 1),
                    "status": eq.get("status", "unknown"),
                    "company": eq.get("company", ""),
                    "drone_observation": eq.get("drone_observation", ""),
                },
                source_expert=self.name,
                confidence=0.93
            )
            result.entities.append(entity)

        result.reasoning = f"Extracted {len(equipment_list)} equipment items via LLM"
        return result


# ============================================================
# SECTION 5: LLM FINANCIAL RISK EXPERT
# ============================================================

class LLMFinancialRiskExpert(LLMBaseExpert):
    """LLM-powered financial risk detection expert."""

    def __init__(self, client: OllamaClient):
        super().__init__("LLMFinancialRiskExpert", client, FinancialRiskExpert())

    def get_system_prompt(self) -> str:
        return """You are a financial risk analyst. Identify payment defaults, arrears, and revenue exposure from business documents.
Return valid JSON with the structure: {"risks": [...], "financial_summary": {...}}"""

    def get_extraction_prompt(self, text: str) -> str:
        return f"""Analyze this document for financial risks and payment issues.

For each RISK extract:
- risk_type: PAYMENT_DEFAULT, LATE_PAYMENT, CONTRACT_VIOLATION, REVENUE_LOSS
- description: What is the risk
- days_overdue: Number of days payment is late (0 if not applicable)
- amount_outstanding: Dollar amount at risk
- severity: LOW, MEDIUM, HIGH, CRITICAL
- affected_entity: Which company/contract is affected

Also provide a FINANCIAL SUMMARY:
- total_annual_revenue: Total revenue mentioned
- total_at_risk: Total amount at risk
- risk_count: Number of risk factors

DOCUMENT:
{text}

Return JSON format:
{{
  "risks": [
    {{"risk_type": "...", "description": "...", "days_overdue": 0, "amount_outstanding": 0, "severity": "...", "affected_entity": "..."}}
  ],
  "financial_summary": {{
    "total_annual_revenue": 0,
    "total_at_risk": 0,
    "risk_count": 0
  }}
}}"""

    def parse_llm_response(self, response: Dict) -> ExtractionResult:
        result = ExtractionResult(expert_name=self.name)

        risks = response.get("risks", [])
        summary = response.get("financial_summary", {})

        for i, risk in enumerate(risks):
            entity = Entity(
                id=f"risk_{risk.get('risk_type', 'unknown').lower()}_{i}",
                type=EntityType.RISK,
                name=f"{risk.get('risk_type', 'Risk')} #{i+1}",
                properties={
                    "risk_type": risk.get("risk_type", ""),
                    "description": risk.get("description", ""),
                    "days_overdue": risk.get("days_overdue", 0),
                    "amount_outstanding": risk.get("amount_outstanding", 0),
                    "severity": risk.get("severity", "MEDIUM"),
                    "affected_entity": risk.get("affected_entity", ""),
                },
                source_expert=self.name,
                confidence=0.92
            )
            result.entities.append(entity)

        # Add financial summary entity
        if summary:
            fin_entity = Entity(
                id="financial_exposure_summary",
                type=EntityType.FINANCIAL,
                name="Revenue Exposure Summary",
                properties={
                    "total_annual_revenue": summary.get("total_annual_revenue", 0),
                    "total_at_risk": summary.get("total_at_risk", 0),
                    "risk_count": summary.get("risk_count", len(risks)),
                },
                source_expert=self.name,
                confidence=0.90
            )
            result.entities.append(fin_entity)

        result.reasoning = f"Detected {len(risks)} financial risks, ${summary.get('total_at_risk', 0):,} at risk via LLM"
        return result


# ============================================================
# SECTION 6: LLM OPPORTUNITY EXPERT
# ============================================================

class LLMOpportunityExpert(LLMBaseExpert):
    """LLM-powered opportunity detection expert (reasoning layer)."""

    def __init__(self, client: OllamaClient):
        super().__init__("LLMOpportunityExpert", client, OpportunityExpert())

    def get_system_prompt(self) -> str:
        return """You are a business development analyst. Identify upsell, cross-sell, maintenance, and equipment removal opportunities from telecom tower data.
Think step-by-step about what actions could generate revenue or reduce risk.
Return valid JSON with the structure: {"opportunities": [...]}"""

    def get_extraction_prompt(self, text: str) -> str:
        return f"""Analyze this telecom tower document and identify ALL business opportunities.

Types of opportunities to look for:
1. UPSELL: Companies not using full capacity that could expand
2. CROSS_SELL: New services that could be offered
3. EQUIPMENT_REMOVAL: Defaulted/abandoned equipment that must be removed
4. MAINTENANCE: Safety issues, rust, damage requiring repair
5. CONTRACT_RENEWAL: Contracts expiring soon

For each OPPORTUNITY extract:
- opportunity_type: UPSELL, CROSS_SELL, EQUIPMENT_REMOVAL, MAINTENANCE, CONTRACT_RENEWAL
- name: Short descriptive name
- description: Detailed explanation
- company: Which company this involves
- potential_revenue: Estimated monthly revenue impact
- priority: LOW, MEDIUM, HIGH, CRITICAL
- reasoning: Why this is an opportunity

DOCUMENT:
{text}

Return JSON format:
{{
  "opportunities": [
    {{"opportunity_type": "...", "name": "...", "description": "...", "company": "...", "potential_revenue": 0, "priority": "...", "reasoning": "..."}}
  ]
}}"""

    def parse_llm_response(self, response: Dict) -> ExtractionResult:
        result = ExtractionResult(expert_name=self.name)

        opportunities = response.get("opportunities", [])

        for i, opp in enumerate(opportunities):
            entity = Entity(
                id=f"opportunity_{opp.get('opportunity_type', 'unknown').lower()}_{i}",
                type=EntityType.OPPORTUNITY,
                name=opp.get("name", f"Opportunity #{i+1}"),
                properties={
                    "opportunity_type": opp.get("opportunity_type", ""),
                    "description": opp.get("description", ""),
                    "company": opp.get("company", ""),
                    "potential_monthly_revenue": opp.get("potential_revenue", 0),
                    "priority": opp.get("priority", "MEDIUM"),
                    "reasoning": opp.get("reasoning", ""),
                },
                source_expert=self.name,
                confidence=0.94
            )
            result.entities.append(entity)

        result.reasoning = f"Identified {len(opportunities)} business opportunities via LLM reasoning"
        return result


# ============================================================
# SECTION 7: LLM HEALTHCARE EXPERT
# ============================================================

class LLMHealthcareExpert(LLMBaseExpert):
    """LLM-powered healthcare entity extraction expert."""

    def __init__(self, client: OllamaClient):
        super().__init__("LLMHealthcareExpert", client, HealthcareExpert())

    def get_system_prompt(self) -> str:
        return """You are a clinical NLP expert. Extract patient, diagnosis, medication, and doctor entities from clinical notes.
Return valid JSON with the structure: {"patients": [...], "diagnoses": [...], "medications": [...], "doctors": [...]}"""

    def get_extraction_prompt(self, text: str) -> str:
        return f"""Analyze this clinical note and extract all medical entities.

For PATIENTS extract:
- name: Patient full name
- dob: Date of birth if mentioned

For DIAGNOSES extract:
- icd10_code: ICD-10 code (e.g., E11.9)
- description: Diagnosis description

For MEDICATIONS extract:
- name: Medication name
- dosage: Dosage (e.g., "500mg")

For DOCTORS extract:
- name: Doctor name (include Dr. prefix)

CLINICAL NOTE:
{text}

Return JSON format:
{{
  "patients": [{{"name": "...", "dob": "..."}}],
  "diagnoses": [{{"icd10_code": "...", "description": "..."}}],
  "medications": [{{"name": "...", "dosage": "..."}}],
  "doctors": [{{"name": "..."}}]
}}"""

    def parse_llm_response(self, response: Dict) -> ExtractionResult:
        result = ExtractionResult(expert_name=self.name)

        patients = response.get("patients", [])
        diagnoses = response.get("diagnoses", [])
        medications = response.get("medications", [])
        doctors = response.get("doctors", [])

        patient_ids = []
        for p in patients:
            name = p.get("name", "Unknown")
            pid = f"patient_{name.lower().replace(' ', '_')}"
            patient_ids.append(pid)
            result.entities.append(Entity(
                id=pid,
                type=EntityType.PERSON,
                name=name,
                properties={"role": "patient", "dob": p.get("dob", "")},
                source_expert=self.name,
                confidence=0.97
            ))

        for d in diagnoses:
            code = d.get("icd10_code", "")
            did = f"diagnosis_{code.lower().replace('.', '_')}"
            result.entities.append(Entity(
                id=did,
                type=EntityType.DIAGNOSIS,
                name=f"{d.get('description', '')} ({code})",
                properties={"icd10_code": code, "description": d.get("description", "")},
                source_expert=self.name,
                confidence=0.96
            ))
            # Link to patients
            for pid in patient_ids:
                result.relationships.append(Relationship(pid, did, RelationshipType.HAS_DIAGNOSIS, confidence=0.95))

        for m in medications:
            name = m.get("name", "")
            mid = f"medication_{name.lower()}"
            result.entities.append(Entity(
                id=mid,
                type=EntityType.MEDICATION,
                name=name,
                properties={"dosage": m.get("dosage", "")},
                source_expert=self.name,
                confidence=0.95
            ))
            # Link to patients
            for pid in patient_ids:
                result.relationships.append(Relationship(pid, mid, RelationshipType.TAKES, confidence=0.94))

        for doc in doctors:
            name = doc.get("name", "")
            drid = f"doctor_{name.lower().replace(' ', '_').replace('.', '')}"
            result.entities.append(Entity(
                id=drid,
                type=EntityType.PERSON,
                name=name if name.startswith("Dr") else f"Dr. {name}",
                properties={"role": "doctor"},
                source_expert=self.name,
                confidence=0.94
            ))
            # Link to patients
            for pid in patient_ids:
                result.relationships.append(Relationship(pid, drid, RelationshipType.PRESCRIBED_BY, confidence=0.93))

        result.reasoning = (
            f"Extracted {len(patients)} patients, {len(diagnoses)} diagnoses, "
            f"{len(medications)} medications, {len(doctors)} doctors via LLM"
        )
        return result


# ============================================================
# SECTION 8: LLM MOE ORCHESTRATOR
# ============================================================

class LLMMoEOrchestrator:
    """
    LLM-powered Mixture-of-Experts Orchestrator.
    Uses Ollama for extraction with fallback to regex.
    Includes: Pipeline tracing, per-expert timing, confidence guardrails.
    """

    def __init__(self, model: str = "llama3:8b", ollama_host: str = None):
        # Use environment variable or parameter, fallback to localhost
        import os
        if ollama_host is None:
            ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.client = OllamaClient(base_url=ollama_host, model=model)
        self.experts: List[LLMBaseExpert] = [
            LLMContractExpert(self.client),
            LLMEquipmentExpert(self.client),
            LLMFinancialRiskExpert(self.client),
            LLMOpportunityExpert(self.client),
        ]
        self.last_pipeline_trace: Optional[PipelineTrace] = None

    def extract_all(self, text: str, context: Dict = None) -> Dict[str, ExtractionResult]:
        """
        Run all LLM experts and return merged extraction results.
        Produces a full PipelineTrace with per-expert timing and audit data.
        """
        pipeline_start = time.time()
        results = {}
        all_entities = []

        # Initialize pipeline trace
        pipeline_trace = PipelineTrace(
            model_used=self.client.model,
            model_version=self.client.model,
            document_hash=hash_text(text),
            document_length=len(text),
            total_experts=len(self.experts),
            min_confidence_threshold=MIN_CONFIDENCE,
        )

        print(f"  Using Ollama model: {self.client.model}")
        print(f"  Ollama available: {self.client.is_available()}")
        print(f"  Confidence threshold: {MIN_CONFIDENCE}")

        for expert in self.experts:
            try:
                print(f"  [{expert.name}] Extracting...")
                extraction = expert.extract(text, context)
                results[expert.name] = extraction
                all_entities.extend(extraction.entities)
                print(f"    → {len(extraction.entities)} entities, {len(extraction.relationships)} relationships")
                print(f"    → {extraction.reasoning}")

                # Collect expert trace
                if hasattr(expert, '_last_trace') and expert._last_trace:
                    pipeline_trace.expert_traces.append(expert._last_trace)

            except Exception as e:
                print(f"  [✗] {expert.name}: Error - {e}")
                results[expert.name] = ExtractionResult(expert_name=expert.name)
                pipeline_trace.warnings.append(f"{expert.name}: {str(e)}")

        # Compute pipeline totals
        pipeline_trace.total_time_ms = (time.time() - pipeline_start) * 1000
        pipeline_trace.total_entities = sum(et.entities_extracted for et in pipeline_trace.expert_traces)
        pipeline_trace.total_entities_rejected = sum(et.entities_rejected for et in pipeline_trace.expert_traces)
        pipeline_trace.total_entities_hallucinated = sum(et.entities_hallucinated for et in pipeline_trace.expert_traces)
        pipeline_trace.total_relationships = sum(et.relationships_extracted for et in pipeline_trace.expert_traces)

        # Save trace to disk
        trace_path = save_trace(pipeline_trace)
        print(f"\n  📋 Pipeline trace saved: {trace_path}")
        print(f"  ⏱️  Total pipeline time: {pipeline_trace.total_time_ms:.0f}ms")

        # Print summary
        print_trace_summary(pipeline_trace)

        self.last_pipeline_trace = pipeline_trace
        return results


# ============================================================
# SECTION 9: MAIN / TEST
# ============================================================

def run_llm_test():
    """Test LLM extraction on sample telecom document."""

    print("=" * 60)
    print("  ECL LLM Extraction Test")
    print("  Using Ollama for MoE Extraction")
    print("=" * 60)

    # --- Load Sample Document ---
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sample_doc = os.path.join(script_dir, "sample_documents", "tower_site_report_T789.md")

    print(f"  Loading: {os.path.basename(sample_doc)}")
    with open(sample_doc, 'r') as f:
        telecom_text = f.read()
    print(f"  Document size: {len(telecom_text):,} characters")

    print("\n[STEP 1] LLM MoE Extraction")
    print("-" * 40)

    orchestrator = LLMMoEOrchestrator(model="llama3:8b")
    results = orchestrator.extract_all(telecom_text)

    print("\n[STEP 2] Building Context Graph")
    print("-" * 40)

    graph_builder = ContextGraphBuilder()

    # Add tower as root node
    tower = Entity(
        id="tower_t789",
        type=EntityType.TOWER,
        name="Tower T-789",
        properties={
            "location": "40.6892° N, 74.0445° W",
            "type": "Monopole",
            "height": "150ft",
        },
        source_expert="manual",
        confidence=1.0
    )
    graph_builder.nodes[tower.id] = tower

    # Add extraction results
    graph_builder.add_extraction_results(results)

    # Add tower relationships
    for entity in graph_builder.nodes.values():
        if entity.type == EntityType.CONTRACT:
            graph_builder.edges.append(Relationship(
                entity.id, tower.id, RelationshipType.OCCUPIES, confidence=0.95
            ))
        elif entity.type == EntityType.OPPORTUNITY:
            graph_builder.edges.append(Relationship(
                tower.id, entity.id, RelationshipType.HAS_OPPORTUNITY, confidence=0.90
            ))
        elif entity.type == EntityType.RISK:
            graph_builder.edges.append(Relationship(
                tower.id, entity.id, RelationshipType.HAS_RISK, confidence=0.90
            ))
        elif entity.type == EntityType.EQUIPMENT:
            graph_builder.edges.append(Relationship(
                entity.id, tower.id, RelationshipType.INSTALLED_ON, confidence=0.88
            ))

    print(f"  Total nodes: {len(graph_builder.nodes)}")
    print(f"  Total edges: {len(graph_builder.edges)}")

    # Generate Cypher
    print("\n[STEP 3] Generating Neo4j Cypher")
    print("-" * 40)
    cypher = graph_builder.generate_cypher()

    with open("ecl_llm_graph.cypher", "w") as f:
        f.write(cypher)
        f.write("\n\n")
        f.write(graph_builder.generate_query_library())
    print("  Saved: ecl_llm_graph.cypher")

    # Summary
    print("\n" + "=" * 60)
    print("  ECL LLM Extraction Complete!")
    print("=" * 60)
    print(f"  Entities extracted: {len(graph_builder.nodes)}")
    print(f"  Relationships:      {len(graph_builder.edges)}")
    print("=" * 60)

    return graph_builder, results


if __name__ == "__main__":
    import sys
    if "--test" in sys.argv:
        run_llm_test()
    else:
        print("ECL LLM Module")
        print("Usage: python3 ecl_llm.py --test")
        print("\nThis module provides LLM-powered extraction experts for ECL.")
        print("Import and use LLMMoEOrchestrator in your code.")
