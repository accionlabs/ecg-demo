
#!/usr/bin/env python3
"""
ECL (Entity-Context-Linking) POC
Telecom Tower Use Case - MoE Expert Extraction + Neo4j Context Graph
Author: Field CTO, Accion Labs
Summit: Accion Labs 12th Annual Global Innovation Summit (Feb 26-28, 2026)
"""

import json
import re
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime

# ============================================================
# SECTION 1: DATA MODELS
# ============================================================

class EntityType(Enum):
    TOWER = "Tower"
    COMPANY = "Company"
    CONTRACT = "Contract"
    EQUIPMENT = "Equipment"
    OPPORTUNITY = "Opportunity"
    RISK = "Risk"
    FINANCIAL = "Financial"
    PERSON = "Person"
    DIAGNOSIS = "Diagnosis"
    MEDICATION = "Medication"

class RelationshipType(Enum):
    OCCUPIES = "OCCUPIES"
    HAS_CONTRACT = "HAS_CONTRACT"
    HAS_EQUIPMENT = "HAS_EQUIPMENT"
    WITH_CLIENT = "WITH_CLIENT"
    OWNED_BY = "OWNED_BY"
    INSTALLED_ON = "INSTALLED_ON"
    HAS_OPPORTUNITY = "HAS_OPPORTUNITY"
    TARGETS = "TARGETS"
    INVOLVES = "INVOLVES"
    HAS_RISK = "HAS_RISK"
    AFFECTS = "AFFECTS"
    PRESCRIBED_BY = "PRESCRIBED_BY"
    HAS_DIAGNOSIS = "HAS_DIAGNOSIS"
    TAKES = "TAKES"

class Severity(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

@dataclass
class Entity:
    id: str
    type: EntityType
    name: str
    properties: Dict[str, Any] = field(default_factory=dict)
    source_expert: str = ""
    confidence: float = 0.0
    extracted_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class Relationship:
    source_id: str
    target_id: str
    type: RelationshipType
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0

@dataclass
class ExtractionResult:
    expert_name: str
    entities: List[Entity] = field(default_factory=list)
    relationships: List[Relationship] = field(default_factory=list)
    reasoning: str = ""


# ============================================================
# SECTION 2: MoE (Mixture of Experts) EXTRACTION ENGINE
# ============================================================

class BaseExpert:
    """Base class for domain-specific extraction experts."""

    def __init__(self, name: str):
        self.name = name

    def extract(self, text: str, context: Dict = None) -> ExtractionResult:
        raise NotImplementedError


class ContractExpert(BaseExpert):
    """Expert 1: Extracts contract entities, terms, and status."""

    def __init__(self):
        super().__init__("ContractExpert")

    def extract(self, text: str, context: Dict = None) -> ExtractionResult:
        result = ExtractionResult(expert_name=self.name)

        # Extract contract IDs
        contract_patterns = re.findall(
            r'Contract\s*#?\s*(\w+).*?(?:Company|Tenant|Carrier)[:\s]*(\w+[\w\s]*?)(?:\n|,|;)',
            text, re.IGNORECASE | re.DOTALL
        )

        # Extract status patterns
        status_map = {}
        for match in re.finditer(
            r'(?:Status|State)[:\s]*(Active|Defaulted|Expired|Pending|Suspended)',
            text, re.IGNORECASE
        ):
            status_map[len(status_map)] = match.group(1).upper()

        # Extract occupancy
        occupancy_matches = re.findall(
            r'(\w+).*?(?:occupancy|capacity)[:\s]*(\d+)%',
            text, re.IGNORECASE
        )

        # Extract financial terms
        revenue_matches = re.findall(
            r'(?:revenue|rent|payment|fee)[:\s]*\$?([\d,]+(?:\.\d{2})?)\s*(?:/mo|per\s*month|monthly)?',
            text, re.IGNORECASE
        )

        outstanding_matches = re.findall(
            r'(?:outstanding|arrears|overdue|owed)[:\s]*\$?([\d,]+(?:\.\d{2})?)',
            text, re.IGNORECASE
        )

        # Build entities from patterns
        idx = 0
        for contract_id, company in contract_patterns:
            company = company.strip()
            status = status_map.get(idx, "UNKNOWN")

            contract_entity = Entity(
                id=f"contract_{contract_id.strip()}",
                type=EntityType.CONTRACT,
                name=f"Contract #{contract_id.strip()}",
                properties={
                    "contract_id": contract_id.strip(),
                    "company": company,
                    "status": status,
                },
                source_expert=self.name,
                confidence=0.92
            )

            # Add financial data if available
            if idx < len(revenue_matches):
                contract_entity.properties["monthly_revenue"] = revenue_matches[idx]
            if idx < len(outstanding_matches):
                contract_entity.properties["outstanding_amount"] = outstanding_matches[idx]

            result.entities.append(contract_entity)

            # Create company entity
            company_entity = Entity(
                id=f"company_{company.lower().replace(' ', '_')}",
                type=EntityType.COMPANY,
                name=company,
                properties={"name": company},
                source_expert=self.name,
                confidence=0.95
            )
            result.entities.append(company_entity)

            # Relationship: Company HAS_CONTRACT
            result.relationships.append(Relationship(
                source_id=company_entity.id,
                target_id=contract_entity.id,
                type=RelationshipType.HAS_CONTRACT,
                properties={"status": status},
                confidence=0.92
            ))

            idx += 1

        # Add occupancy to company properties
        for company_name, pct in occupancy_matches:
            for e in result.entities:
                if e.type == EntityType.COMPANY and company_name.lower() in e.name.lower():
                    e.properties["occupancy_pct"] = int(pct)

        result.reasoning = (
            f"Extracted {len(contract_patterns)} contracts with status, "
            f"financial terms, and occupancy data."
        )
        return result


class EquipmentExpert(BaseExpert):
    """Expert 2: Extracts equipment entities from contracts + drone data."""

    def __init__(self):
        super().__init__("EquipmentExpert")

    def extract(self, text: str, context: Dict = None) -> ExtractionResult:
        result = ExtractionResult(expert_name=self.name)

        # Equipment patterns
        equipment_patterns = re.findall(
            r'(?:Equipment|Hardware|Device)[:\s]*([\w\s]+?)(?:\n|,|;|\.)',
            text, re.IGNORECASE
        )

        # Antenna/radio patterns
        antenna_matches = re.findall(
            r'(\d+)\s*(?:x\s*)?(?:antennas?|radios?|panels?|dishes?)',
            text, re.IGNORECASE
        )

        # Equipment status
        equip_status = re.findall(
            r'(?:equipment|hardware).*?(?:status|condition)[:\s]*(operational|inactive|damaged|rusted|degraded)',
            text, re.IGNORECASE
        )

        # Drone observation patterns
        drone_obs = re.findall(
            r'(?:drone|inspection|visual|image).*?(?:detected|found|shows?|observed)[:\s]*(.*?)(?:\n|\.)',
            text, re.IGNORECASE
        )

        # Build equipment entities
        for i, (equip_name,) in enumerate([(e,) for e in equipment_patterns]):
            equip_name = equip_name.strip()
            if len(equip_name) < 2:
                continue

            status = equip_status[i] if i < len(equip_status) else "unknown"

            entity = Entity(
                id=f"equipment_{equip_name.lower().replace(' ', '_')}_{i}",
                type=EntityType.EQUIPMENT,
                name=equip_name,
                properties={
                    "type": equip_name,
                    "status": status,
                    "quantity": antenna_matches[i] if i < len(antenna_matches) else "1",
                },
                source_expert=self.name,
                confidence=0.88
            )

            if i < len(drone_obs):
                entity.properties["drone_observation"] = drone_obs[i].strip()

            result.entities.append(entity)

        result.reasoning = (
            f"Extracted {len(result.entities)} equipment items with status "
            f"and {len(drone_obs)} drone observations."
        )
        return result


class FinancialRiskExpert(BaseExpert):
    """Expert 3: Detects financial risks, payment defaults, revenue exposure."""

    def __init__(self):
        super().__init__("FinancialRiskExpert")

    def extract(self, text: str, context: Dict = None) -> ExtractionResult:
        result = ExtractionResult(expert_name=self.name)

        # Default/arrears detection
        default_patterns = re.findall(
            r'(?:default(?:ed)?|arrears|overdue|delinquent).*?'
            r'(?:(\d+)\s*days?)?.*?'
            r'(?:\$?([\d,]+(?:\.\d{2})?))?',
            text, re.IGNORECASE
        )

        # Revenue at risk
        revenue_risk = re.findall(
            r'(?:annual|yearly|monthly)\s*(?:revenue|value|rent)[:\s]*\$?([\d,]+(?:\.\d{2})?)',
            text, re.IGNORECASE
        )

        # Payment history signals
        payment_issues = re.findall(
            r'(?:missed|late|partial)\s*(?:payment|installment)',
            text, re.IGNORECASE
        )

        for i, (days, amount) in enumerate(default_patterns):
            severity = Severity.HIGH if int(days or 0) > 60 else Severity.MEDIUM

            risk_entity = Entity(
                id=f"risk_payment_default_{i}",
                type=EntityType.RISK,
                name=f"Payment Default Risk #{i+1}",
                properties={
                    "risk_type": "PAYMENT_DEFAULT",
                    "days_overdue": int(days) if days else 0,
                    "amount_outstanding": amount if amount else "unknown",
                    "severity": severity.value,
                    "payment_issues_count": len(payment_issues),
                },
                source_expert=self.name,
                confidence=0.90
            )
            result.entities.append(risk_entity)

        # Calculate total revenue exposure
        total_exposure = sum(
            float(r.replace(',', '')) for r in revenue_risk if r
        )

        if total_exposure > 0:
            fin_entity = Entity(
                id="financial_exposure_summary",
                type=EntityType.FINANCIAL,
                name="Revenue Exposure Summary",
                properties={
                    "total_annual_exposure": total_exposure,
                    "risk_factors": len(default_patterns),
                },
                source_expert=self.name,
                confidence=0.85
            )
            result.entities.append(fin_entity)

        result.reasoning = (
            f"Detected {len(default_patterns)} default signals, "
            f"${total_exposure:,.0f} total revenue exposure."
        )
        return result


class OpportunityExpert(BaseExpert):
    """Expert 4: Reasoning layer - identifies upsell, cross-sell, maintenance opportunities."""

    def __init__(self):
        super().__init__("OpportunityExpert")

    def extract(self, text: str, context: Dict = None) -> ExtractionResult:
        result = ExtractionResult(expert_name=self.name)
        context = context or {}

        # Upsell: Look for capacity/occupancy gaps
        occupancy_matches = re.findall(
            r'(\w+).*?(?:occupancy|capacity)[:\s]*(\d+)%',
            text, re.IGNORECASE
        )

        for company, pct in occupancy_matches:
            pct_int = int(pct)
            if pct_int < 100:
                gap = 100 - pct_int
                # Estimate revenue uplift
                monthly_rev_match = re.search(
                    rf'{company}.*?\$?([\d,]+)(?:/mo|per\s*month)',
                    text, re.IGNORECASE
                )
                current_rev = float(monthly_rev_match.group(1).replace(',', '')) if monthly_rev_match else 0
                potential_uplift = (current_rev / pct_int * gap) if pct_int > 0 and current_rev > 0 else 0

                opp = Entity(
                    id=f"opportunity_upsell_{company.lower()}",
                    type=EntityType.OPPORTUNITY,
                    name=f"Upsell: {company} Capacity Expansion",
                    properties={
                        "opportunity_type": "UPSELL",
                        "company": company,
                        "current_occupancy": pct_int,
                        "available_capacity": gap,
                        "potential_monthly_uplift": round(potential_uplift, 2),
                        "reasoning": f"{company} at {pct_int}% occupancy; {gap}% available for expansion",
                    },
                    source_expert=self.name,
                    confidence=0.87
                )
                result.entities.append(opp)

        # Equipment removal: Defaulted equipment
        defaulted = re.findall(
            r'(?:defaulted|inactive|abandoned).*?(?:equipment|hardware|dish|antenna)(.*?)(?:\n|\.)',
            text, re.IGNORECASE
        )

        for i, details in enumerate(defaulted):
            opp = Entity(
                id=f"opportunity_removal_{i}",
                type=EntityType.OPPORTUNITY,
                name=f"Equipment Removal #{i+1}",
                properties={
                    "opportunity_type": "EQUIPMENT_REMOVAL",
                    "details": details.strip(),
                    "reasoning": "Defaulted equipment must be removed per contract terms",
                    "action_required": True,
                },
                source_expert=self.name,
                confidence=0.91
            )
            result.entities.append(opp)

        # Maintenance: Structural/safety issues
        maintenance_signals = re.findall(
            r'(?:rust(?:ed)?|corrosion|damaged|cracked|loose|degraded)(.*?)(?:\n|\.)',
            text, re.IGNORECASE
        )

        for i, details in enumerate(maintenance_signals):
            opp = Entity(
                id=f"opportunity_maintenance_{i}",
                type=EntityType.OPPORTUNITY,
                name=f"Maintenance Required #{i+1}",
                properties={
                    "opportunity_type": "MAINTENANCE",
                    "details": details.strip(),
                    "severity": "HIGH",
                    "reasoning": "Safety/compliance issue detected - requires immediate attention",
                },
                source_expert=self.name,
                confidence=0.93
            )
            result.entities.append(opp)

        result.reasoning = (
            f"Identified {len(result.entities)} opportunities: "
            f"{len(occupancy_matches)} upsell, {len(defaulted)} removal, "
            f"{len(maintenance_signals)} maintenance."
        )
        return result


class MoEOrchestrator:
    """
    Mixture-of-Experts Orchestrator.
    Routes text through specialized experts and merges results.
    """

    def __init__(self):
        self.experts: List[BaseExpert] = [
            ContractExpert(),
            EquipmentExpert(),
            FinancialRiskExpert(),
            OpportunityExpert(),
        ]

    def extract_all(self, text: str, context: Dict = None) -> Dict[str, ExtractionResult]:
        """Run all experts and return merged extraction results."""
        results = {}
        all_entities = []

        for expert in self.experts:
            try:
                extraction = expert.extract(text, context)
                results[expert.name] = extraction
                all_entities.extend(extraction.entities)
                print(f"  [✓] {expert.name}: {len(extraction.entities)} entities, "
                      f"{len(extraction.relationships)} relationships")
                print(f"      Reasoning: {extraction.reasoning}")
            except Exception as e:
                print(f"  [✗] {expert.name}: Error - {e}")
                results[expert.name] = ExtractionResult(expert_name=expert.name)

        # Pass all entities as context to opportunity expert for cross-referencing
        if all_entities:
            context = context or {}
            context["all_entities"] = [asdict(e) for e in all_entities]

        return results


# ============================================================
# SECTION 3: CONTEXT GRAPH BUILDER (Neo4j Cypher Generation)
# ============================================================

class ContextGraphBuilder:
    """Builds Neo4j Cypher statements from extracted entities and relationships."""

    def __init__(self):
        self.cypher_statements: List[str] = []
        self.nodes: Dict[str, Entity] = {}
        self.edges: List[Relationship] = []

    def add_extraction_results(self, results: Dict[str, ExtractionResult]):
        """Merge all expert results into a unified graph."""
        for expert_name, extraction in results.items():
            for entity in extraction.entities:
                # Deduplicate by ID
                if entity.id not in self.nodes:
                    self.nodes[entity.id] = entity
                else:
                    # Merge properties
                    self.nodes[entity.id].properties.update(entity.properties)

            for rel in extraction.relationships:
                self.edges.append(rel)

    def generate_cypher(self) -> str:
        """Generate complete Neo4j Cypher CREATE statements."""
        lines = []
        lines.append("// ============================================")
        lines.append("// ECL Context Graph - Auto-Generated Cypher")
        lines.append(f"// Generated: {datetime.now().isoformat()}")
        lines.append("// ============================================")
        lines.append("")

        # Clear existing data (optional)
        lines.append("// Clear previous data (CAUTION: removes all nodes)")
        lines.append("// MATCH (n) DETACH DELETE n;")
        lines.append("")

        # Create constraint indexes
        lines.append("// Indexes for performance")
        unique_types = set(e.type.value for e in self.nodes.values())
        for t in sorted(unique_types):
            lines.append(f"CREATE INDEX IF NOT EXISTS FOR (n:{t}) ON (n.id);")
        lines.append("")

        # Create nodes
        lines.append("// === CREATE NODES ===")
        for entity_id, entity in self.nodes.items():
            props = {
                "id": entity.id,
                "name": entity.name,
                "confidence": entity.confidence,
                "source_expert": entity.source_expert,
                **entity.properties
            }
            props_str = self._format_properties(props)
            var_name = self._safe_var_name(entity.id)
            lines.append(f"CREATE ({var_name}:{entity.type.value} {props_str})")

        lines.append("")
        lines.append("// === CREATE RELATIONSHIPS ===")
        for rel in self.edges:
            src_var = self._safe_var_name(rel.source_id)
            tgt_var = self._safe_var_name(rel.target_id)
            props_str = self._format_properties(rel.properties) if rel.properties else ""
            if props_str:
                lines.append(f"CREATE ({src_var})-[:{rel.type.value} {props_str}]->({tgt_var})")
            else:
                lines.append(f"CREATE ({src_var})-[:{rel.type.value}]->({tgt_var})")

        lines.append("")
        lines.append(";")

        return "\n".join(lines)

    def generate_query_library(self) -> str:
        """Generate useful Cypher queries for AI agents."""
        queries = []
        queries.append("// ============================================")
        queries.append("// ECL Agent Query Library")
        queries.append("// ============================================")
        queries.append("")

        queries.append("// Q1: Find all opportunities for a tower")
        queries.append("MATCH (t:Tower)-[:HAS_OPPORTUNITY]->(o:Opportunity)")
        queries.append("RETURN t.name AS tower, o.name AS opportunity,")
        queries.append("       o.opportunity_type AS type, o.potential_monthly_uplift AS uplift")
        queries.append("ORDER BY o.potential_monthly_uplift DESC;")
        queries.append("")

        queries.append("// Q2: Identify equipment needing removal")
        queries.append("MATCH (e:Equipment {status: 'inactive'})-[:INSTALLED_ON]->(t:Tower)")
        queries.append("MATCH (c:Company)-[:HAS_EQUIPMENT]->(e)")
        queries.append("RETURN t.name AS tower, c.name AS company, e.name AS equipment;")
        queries.append("")

        queries.append("// Q3: Get complete tower context (for AI agent)")
        queries.append("MATCH (t:Tower {id: $tower_id})")
        queries.append("OPTIONAL MATCH (t)<-[:OCCUPIES]-(c:Contract)")
        queries.append("OPTIONAL MATCH (t)<-[:HAS_EQUIPMENT]-(co:Company)")
        queries.append("OPTIONAL MATCH (t)-[:HAS_OPPORTUNITY]->(o:Opportunity)")
        queries.append("OPTIONAL MATCH (t)-[:HAS_RISK]->(r:Risk)")
        queries.append("RETURN t, collect(DISTINCT c) AS contracts,")
        queries.append("       collect(DISTINCT co) AS companies,")
        queries.append("       collect(DISTINCT o) AS opportunities,")
        queries.append("       collect(DISTINCT r) AS risks;")
        queries.append("")

        queries.append("// Q4: Calculate total revenue at risk")
        queries.append("MATCH (r:Risk)-[:AFFECTS]->(c:Contract)")
        queries.append("RETURN sum(toFloat(c.outstanding_amount)) AS total_arrears,")
        queries.append("       sum(toFloat(c.monthly_revenue) * 12) AS annual_at_risk;")
        queries.append("")

        queries.append("// Q5: Cross-company relationship discovery")
        queries.append("MATCH path = (c1:Company)-[*1..3]-(c2:Company)")
        queries.append("WHERE c1 <> c2")
        queries.append("RETURN c1.name, c2.name, [r IN relationships(path) | type(r)] AS via;")

        return "\n".join(queries)

    @staticmethod
    def _format_properties(props: Dict) -> str:
        formatted = []
        for k, v in props.items():
            if isinstance(v, str):
                escaped = v.replace("'", "\\'")
                formatted.append(f"{k}: '{escaped}'")
            elif isinstance(v, bool):
                formatted.append(f"{k}: {'true' if v else 'false'}")
            elif isinstance(v, (int, float)):
                formatted.append(f"{k}: {v}")
            else:
                formatted.append(f"{k}: '{v}'")
        return "{" + ", ".join(formatted) + "}"

    @staticmethod
    def _safe_var_name(entity_id: str) -> str:
        return re.sub(r'[^a-zA-Z0-9]', '_', entity_id)


# ============================================================
# SECTION 4: MCP (Model Context Protocol) AGENT INTERFACE
# ============================================================

class MCPToolServer:
    """
    Simulated MCP Server exposing ECL graph tools for AI agents.
    In production, this would be a FastAPI/SSE server implementing MCP spec.
    """

    def __init__(self, graph_builder: ContextGraphBuilder):
        self.graph = graph_builder
        self.tools = {
            "get_tower_context": self.get_tower_context,
            "find_opportunities": self.find_opportunities,
            "assess_risk": self.assess_risk,
            "get_company_relationships": self.get_company_relationships,
            "search_entities": self.search_entities,
        }

    def list_tools(self) -> List[Dict]:
        """MCP tools/list - Returns available tools for AI agents."""
        return [
            {
                "name": "get_tower_context",
                "description": "Get complete context for a tower including contracts, equipment, opportunities, and risks",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "tower_id": {"type": "string", "description": "Tower identifier"}
                    },
                    "required": ["tower_id"]
                }
            },
            {
                "name": "find_opportunities",
                "description": "Find upsell, cross-sell, and maintenance opportunities across towers",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "opportunity_type": {
                            "type": "string",
                            "enum": ["UPSELL", "EQUIPMENT_REMOVAL", "MAINTENANCE", "ALL"]
                        }
                    }
                }
            },
            {
                "name": "assess_risk",
                "description": "Assess financial and operational risks for towers or companies",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "entity_id": {"type": "string"}
                    }
                }
            },
            {
                "name": "get_company_relationships",
                "description": "Get all relationships for a company across towers",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "company_name": {"type": "string"}
                    }
                }
            },
            {
                "name": "search_entities",
                "description": "Search extracted entities by type or keyword",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "entity_type": {"type": "string"},
                        "keyword": {"type": "string"}
                    }
                }
            },
        ]

    def call_tool(self, tool_name: str, arguments: Dict) -> Dict:
        """MCP tools/call - Execute a tool and return results."""
        if tool_name not in self.tools:
            return {"error": f"Unknown tool: {tool_name}"}
        return self.tools[tool_name](**arguments)

    def get_tower_context(self, tower_id: str) -> Dict:
        """Returns full context graph for a specific tower."""
        tower_entities = []
        tower_relationships = []

        # Find tower node
        tower_node = None
        for eid, entity in self.graph.nodes.items():
            if entity.type == EntityType.TOWER and tower_id.lower() in eid.lower():
                tower_node = entity
                break

        if not tower_node:
            return {"error": f"Tower {tower_id} not found", "available_towers": [
                e.name for e in self.graph.nodes.values() if e.type == EntityType.TOWER
            ]}

        # Gather all connected entities
        connected_ids = set()
        for rel in self.graph.edges:
            if tower_node.id in (rel.source_id, rel.target_id):
                connected_ids.add(rel.source_id)
                connected_ids.add(rel.target_id)
                tower_relationships.append(asdict(rel))

        for eid in connected_ids:
            if eid in self.graph.nodes:
                tower_entities.append(asdict(self.graph.nodes[eid]))

        return {
            "tower": asdict(tower_node),
            "connected_entities": tower_entities,
            "relationships": tower_relationships,
            "entity_count": len(tower_entities),
            "relationship_count": len(tower_relationships),
        }

    def find_opportunities(self, opportunity_type: str = "ALL") -> Dict:
        """Returns opportunities filtered by type."""
        opportunities = []
        for entity in self.graph.nodes.values():
            if entity.type == EntityType.OPPORTUNITY:
                if opportunity_type == "ALL" or entity.properties.get("opportunity_type") == opportunity_type:
                    opportunities.append(asdict(entity))

        return {
            "opportunities": opportunities,
            "count": len(opportunities),
            "filter": opportunity_type,
        }

    def assess_risk(self, entity_id: str = "") -> Dict:
        """Returns risk assessment for an entity."""
        risks = []
        for entity in self.graph.nodes.values():
            if entity.type == EntityType.RISK:
                risks.append(asdict(entity))

        financials = []
        for entity in self.graph.nodes.values():
            if entity.type == EntityType.FINANCIAL:
                financials.append(asdict(entity))

        return {
            "risks": risks,
            "financial_summary": financials,
            "total_risks": len(risks),
        }

    def get_company_relationships(self, company_name: str) -> Dict:
        """Returns all relationships for a company."""
        company_node = None
        for entity in self.graph.nodes.values():
            if entity.type == EntityType.COMPANY and company_name.lower() in entity.name.lower():
                company_node = entity
                break

        if not company_node:
            return {"error": f"Company {company_name} not found"}

        rels = []
        for rel in self.graph.edges:
            if company_node.id in (rel.source_id, rel.target_id):
                rels.append(asdict(rel))

        return {
            "company": asdict(company_node),
            "relationships": rels,
            "relationship_count": len(rels),
        }

    def search_entities(self, entity_type: str = "", keyword: str = "") -> Dict:
        """Search entities by type or keyword."""
        results = []
        for entity in self.graph.nodes.values():
            type_match = not entity_type or entity.type.value.lower() == entity_type.lower()
            keyword_match = not keyword or keyword.lower() in json.dumps(asdict(entity)).lower()
            if type_match and keyword_match:
                results.append(asdict(entity))

        return {"results": results, "count": len(results)}


# ============================================================
# SECTION 5: NETWORKX VISUALIZATION (Neo4j-Free Demo)
# ============================================================

def build_networkx_graph(graph_builder: ContextGraphBuilder):
    """Build a NetworkX graph for local visualization (no Neo4j required)."""
    try:
        import networkx as nx

        G = nx.DiGraph()

        # Color map by entity type
        color_map = {
            EntityType.TOWER: "#FF6B6B",
            EntityType.COMPANY: "#4ECDC4",
            EntityType.CONTRACT: "#45B7D1",
            EntityType.EQUIPMENT: "#96CEB4",
            EntityType.OPPORTUNITY: "#FFEAA7",
            EntityType.RISK: "#FF7675",
            EntityType.FINANCIAL: "#DDA0DD",
            EntityType.PERSON: "#74B9FF",
        }

        # Reserved keys that shouldn't be unpacked from properties
        reserved_keys = {'type', 'label', 'color', 'id'}
        
        for entity_id, entity in graph_builder.nodes.items():
            # Filter out reserved keys to avoid duplicate keyword arguments
            safe_props = {k: str(v) for k, v in entity.properties.items() if k not in reserved_keys}
            G.add_node(
                entity_id,
                label=entity.name,
                type=entity.type.value,
                color=color_map.get(entity.type, "#CCCCCC"),
                **safe_props
            )

        for rel in graph_builder.edges:
            if rel.source_id in G.nodes and rel.target_id in G.nodes:
                G.add_edge(
                    rel.source_id,
                    rel.target_id,
                    relationship=rel.type.value,
                    **{k: str(v) for k, v in rel.properties.items()}
                )

        return G
    except ImportError:
        print("NetworkX not installed. Run: pip install networkx")
        return None


def export_graph_html(graph_builder: ContextGraphBuilder, output_file: str = "ecl_graph.html"):
    """Export interactive HTML visualization using pyvis (if available) or D3.js."""
    try:
        from pyvis.network import Network

        net = Network(height="800px", width="100%", bgcolor="#1a1a2e", font_color="white")
        net.barnes_hut(gravity=-3000, central_gravity=0.3, spring_length=200)

        color_map = {
            EntityType.TOWER: "#FF6B6B",
            EntityType.COMPANY: "#4ECDC4",
            EntityType.CONTRACT: "#45B7D1",
            EntityType.EQUIPMENT: "#96CEB4",
            EntityType.OPPORTUNITY: "#FFEAA7",
            EntityType.RISK: "#FF7675",
            EntityType.FINANCIAL: "#DDA0DD",
        }

        for entity_id, entity in graph_builder.nodes.items():
            title = f"<b>{entity.name}</b><br>Type: {entity.type.value}<br>"
            for k, v in entity.properties.items():
                title += f"{k}: {v}<br>"

            net.add_node(
                entity_id,
                label=entity.name,
                color=color_map.get(entity.type, "#CCCCCC"),
                title=title,
                size=30 if entity.type == EntityType.TOWER else 20,
                shape="diamond" if entity.type == EntityType.TOWER else "dot",
            )

        for rel in graph_builder.edges:
            net.add_edge(
                rel.source_id,
                rel.target_id,
                title=rel.type.value,
                label=rel.type.value,
                color="#888888",
            )

        net.save_graph(output_file)
        print(f"  Graph exported to {output_file}")
        return output_file

    except ImportError:
        # Fallback: Generate raw D3.js HTML
        nodes_json = []
        for eid, entity in graph_builder.nodes.items():
            nodes_json.append({
                "id": eid, "label": entity.name,
                "group": entity.type.value
            })

        edges_json = []
        for rel in graph_builder.edges:
            edges_json.append({
                "source": rel.source_id, "target": rel.target_id,
                "label": rel.type.value
            })

        html = f"""<!DOCTYPE html>
<html><head><title>ECL Context Graph</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>body{{background:#1a1a2e;margin:0}} svg{{width:100%;height:100vh}}</style>
</head><body>
<script>
const nodes = {json.dumps(nodes_json)};
const links = {json.dumps(edges_json)};
// D3 force-directed graph implementation
const svg = d3.select("body").append("svg");
const sim = d3.forceSimulation(nodes)
  .force("link", d3.forceLink(links).id(d=>d.id).distance(150))
  .force("charge", d3.forceManyBody().strength(-300))
  .force("center", d3.forceCenter(window.innerWidth/2, window.innerHeight/2));
const link = svg.selectAll("line").data(links).join("line").attr("stroke","#666");
const node = svg.selectAll("circle").data(nodes).join("circle").attr("r",12).attr("fill","#4ECDC4");
const label = svg.selectAll("text").data(nodes).join("text").text(d=>d.label)
  .attr("fill","white").attr("font-size","10px");
sim.on("tick",()=>{{
  link.attr("x1",d=>d.source.x).attr("y1",d=>d.source.y).attr("x2",d=>d.target.x).attr("y2",d=>d.target.y);
  node.attr("cx",d=>d.x).attr("cy",d=>d.y);
  label.attr("x",d=>d.x+15).attr("y",d=>d.y+4);
}});
</script></body></html>"""

        with open(output_file, "w") as f:
            f.write(html)
        print(f"  Graph exported to {output_file} (D3.js fallback)")
        return output_file


# ============================================================
# SECTION 6: HEALTHCARE DOMAIN EXPERT (Bonus - from POC doc)
# ============================================================

class HealthcareExpert(BaseExpert):
    """Extracts patient-diagnosis-medication-doctor entities from clinical notes."""

    def __init__(self):
        super().__init__("HealthcareExpert")

    def extract(self, text: str, context: Dict = None) -> ExtractionResult:
        result = ExtractionResult(expert_name=self.name)

        # Patient extraction
        patients = re.findall(r'Patient[:\s]*([\w\s]+?)(?:\n|,|;)', text, re.IGNORECASE)
        for p in patients:
            result.entities.append(Entity(
                id=f"patient_{p.strip().lower().replace(' ', '_')}",
                type=EntityType.PERSON,
                name=p.strip(),
                properties={"role": "patient"},
                source_expert=self.name,
                confidence=0.95
            ))

        # Medication
        meds = re.findall(
            r'(?:Medication|Rx|Drug|Prescribed)[:\s]*([\w]+)\s*(?:dosage|dose)?[:\s]*(\d+\s*mg)?',
            text, re.IGNORECASE
        )
        for med_name, dosage in meds:
            result.entities.append(Entity(
                id=f"medication_{med_name.lower()}",
                type=EntityType.MEDICATION,
                name=med_name,
                properties={"dosage": dosage.strip() if dosage else "unknown"},
                source_expert=self.name,
                confidence=0.90
            ))

        # ICD-10 Diagnosis codes
        diagnoses = re.findall(r'ICD-10[:\s]*([\w.]+)\s*\(([^)]+)\)', text, re.IGNORECASE)
        for code, desc in diagnoses:
            result.entities.append(Entity(
                id=f"diagnosis_{code.lower().replace('.', '_')}",
                type=EntityType.DIAGNOSIS,
                name=f"{desc} ({code})",
                properties={"icd10_code": code, "description": desc},
                source_expert=self.name,
                confidence=0.95
            ))

        # Doctor
        doctors = re.findall(r'(?:Dr\.?|Doctor|Prescribed by)[:\s]*([\w\s.]+?)(?:\n|,|;|$)', text, re.IGNORECASE)
        for doc in doctors:
            result.entities.append(Entity(
                id=f"doctor_{doc.strip().lower().replace(' ', '_').replace('.', '')}",
                type=EntityType.PERSON,
                name=f"Dr. {doc.strip()}",
                properties={"role": "doctor"},
                source_expert=self.name,
                confidence=0.90
            ))

        # Build relationships
        patient_ids = [e.id for e in result.entities if e.properties.get("role") == "patient"]
        med_ids = [e.id for e in result.entities if e.type == EntityType.MEDICATION]
        diag_ids = [e.id for e in result.entities if e.type == EntityType.DIAGNOSIS]
        doc_ids = [e.id for e in result.entities if e.properties.get("role") == "doctor"]

        for pid in patient_ids:
            for mid in med_ids:
                result.relationships.append(Relationship(pid, mid, RelationshipType.TAKES, confidence=0.90))
            for did in diag_ids:
                result.relationships.append(Relationship(pid, did, RelationshipType.HAS_DIAGNOSIS, confidence=0.95))
            for drid in doc_ids:
                result.relationships.append(Relationship(pid, drid, RelationshipType.PRESCRIBED_BY, confidence=0.88))

        result.reasoning = (
            f"Extracted {len(patients)} patients, {len(meds)} medications, "
            f"{len(diagnoses)} diagnoses, {len(doctors)} doctors."
        )
        return result


# ============================================================
# SECTION 7: MAIN ECL PIPELINE
# ============================================================

def run_telecom_demo():
    """Run the full ECL pipeline on a telecom tower document."""

    print("=" * 60)
    print("  ECL (Entity-Context-Linking) POC")
    print("  Telecom Tower Use Case")
    print("  Accion Labs Innovation Summit 2026")
    print("=" * 60)

    # --- Sample Telecom Tower Document ---
    telecom_text = """
    TOWER SITE REPORT: T-789
    Location: 40.6892° N, 74.0445° W
    Tower Type: Monopole, 150ft

    CONTRACT SUMMARY:
    Contract #12345
    Company: Verizon
    Status: Active
    Occupancy: 80%
    Monthly Revenue: $5,000/mo
    Equipment: 6 antennas, 4 radios
    Equipment Status: Operational
    Term: 2020-2030, auto-renew

    Contract #67890
    Company: DISH
    Status: Defaulted
    Occupancy: 15%
    Monthly Revenue: $3,000/mo (suspended)
    Outstanding: $9,000
    Equipment: 1 Satellite Dish
    Equipment Status: Inactive
    Term: 2019-2024, expired
    Default: 90 days overdue, $9,000 outstanding
    Annual value: $36,000

    DRONE INSPECTION (2026-01-20):
    Drone inspection detected rusted mounting brackets on south face.
    Defaulted equipment dish from DISH Network shows corrosion.
    Verizon antennas operational, no issues detected.

    NOTES:
    - Verizon interested in expanding to full tower capacity
    - DISH equipment must be removed per defaulted contract terms
    - Safety inspection due Q2 2026
    """

    # --- Step 1: MoE Extraction ---
    print("\n[STEP 1] MoE Expert Extraction")
    print("-" * 40)
    orchestrator = MoEOrchestrator()
    results = orchestrator.extract_all(telecom_text)

    # --- Step 2: Build Context Graph ---
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

    # Add tower relationships (tower-centric graph)
    for entity in graph_builder.nodes.values():
        if entity.type == EntityType.CONTRACT:
            # Tower → Contract (HAS_CONTRACT)
            graph_builder.edges.append(Relationship(
                tower.id, entity.id, RelationshipType.HAS_CONTRACT, confidence=0.95
            ))
            # Contract → Company (WITH_CLIENT) if company exists
            company_name = entity.properties.get('company', '')
            if company_name:
                company_id = f"company_{company_name.lower().replace(' ', '_')}"
                if company_id in graph_builder.nodes:
                    graph_builder.edges.append(Relationship(
                        entity.id, company_id, RelationshipType.WITH_CLIENT, confidence=0.92
                    ))
        elif entity.type == EntityType.OPPORTUNITY:
            # Tower → Opportunity
            graph_builder.edges.append(Relationship(
                tower.id, entity.id, RelationshipType.HAS_OPPORTUNITY, confidence=0.90
            ))
        elif entity.type == EntityType.RISK:
            # Tower → Risk
            graph_builder.edges.append(Relationship(
                tower.id, entity.id, RelationshipType.HAS_RISK, confidence=0.90
            ))
        elif entity.type == EntityType.EQUIPMENT:
            # Tower → Equipment (HAS_EQUIPMENT)
            graph_builder.edges.append(Relationship(
                tower.id, entity.id, RelationshipType.HAS_EQUIPMENT, confidence=0.88
            ))

    print(f"  Total nodes: {len(graph_builder.nodes)}")
    print(f"  Total edges: {len(graph_builder.edges)}")

    # --- Step 3: Generate Cypher ---
    print("\n[STEP 3] Generating Neo4j Cypher")
    print("-" * 40)
    cypher = graph_builder.generate_cypher()
    print(cypher[:500] + "...\n")

    # Save Cypher to file
    with open("ecl_telecom_graph.cypher", "w") as f:
        f.write(cypher)
        f.write("\n\n")
        f.write(graph_builder.generate_query_library())
    print("  Saved: ecl_telecom_graph.cypher")

    # --- Step 4: MCP Agent Interface ---
    print("\n[STEP 4] MCP Agent Interface")
    print("-" * 40)
    mcp = MCPToolServer(graph_builder)

    print("\n  Available MCP Tools:")
    for tool in mcp.list_tools():
        print(f"    - {tool['name']}: {tool['description'][:60]}...")

    print("\n  Agent Query: find_opportunities(type='ALL')")
    opps = mcp.find_opportunities(opportunity_type="ALL")
    print(f"  Result: {opps['count']} opportunities found")
    for opp in opps.get("opportunities", []):
        print(f"    → {opp['name']} [{opp['properties'].get('opportunity_type', 'N/A')}]")

    print("\n  Agent Query: assess_risk()")
    risks = mcp.assess_risk()
    print(f"  Result: {risks['total_risks']} risks identified")
    for risk in risks.get("risks", []):
        print(f"    → {risk['name']} [Severity: {risk['properties'].get('severity', 'N/A')}]")

    # --- Step 5: Visualization ---
    print("\n[STEP 5] Graph Visualization")
    print("-" * 40)
    G = build_networkx_graph(graph_builder)
    if G:
        print(f"  NetworkX graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    export_graph_html(graph_builder, "ecl_telecom_graph.html")

    # --- Summary ---
    print("\n" + "=" * 60)
    print("  ECL POC Complete!")
    print("=" * 60)
    print(f"  Entities extracted: {len(graph_builder.nodes)}")
    print(f"  Relationships:      {len(graph_builder.edges)}")
    print(f"  MCP tools:          {len(mcp.list_tools())}")
    print(f"  Files generated:")
    print(f"    - ecl_telecom_graph.cypher  (Neo4j import)")
    print(f"    - ecl_telecom_graph.html    (Interactive viz)")
    print("=" * 60)

    return graph_builder, mcp


def run_healthcare_demo():
    """Run ECL pipeline on a healthcare clinical note."""

    print("\n" + "=" * 60)
    print("  ECL Healthcare Demo - Patient Graph")
    print("=" * 60)

    clinical_note = """
    Patient: John Smith
    DOB: 1958-03-15
    Visit Date: 2026-01-15

    Medication: Metformin dosage 500mg
    Medication: Lisinopril dosage 10mg
    ICD-10: E11.9 (Type 2 Diabetes)
    ICD-10: I10 (Essential Hypertension)
    Prescribed by: Dr. Jane Doe

    Notes: Patient reports improved glucose control. A1C decreased
    from 8.2 to 7.1. Blood pressure stable at 128/82.
    Continue current medications. Follow-up in 3 months.
    """

    expert = HealthcareExpert()
    result = expert.extract(clinical_note)

    print(f"\n  Entities: {len(result.entities)}")
    for e in result.entities:
        print(f"    [{e.type.value}] {e.name} (confidence: {e.confidence})")

    print(f"\n  Relationships: {len(result.relationships)}")
    for r in result.relationships:
        print(f"    {r.source_id} --[{r.type.value}]--> {r.target_id}")

    # Build graph
    graph_builder = ContextGraphBuilder()
    graph_builder.add_extraction_results({"healthcare": result})
    cypher = graph_builder.generate_cypher()

    with open("ecl_healthcare_graph.cypher", "w") as f:
        f.write(cypher)
    print(f"\n  Saved: ecl_healthcare_graph.cypher")

    return graph_builder


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    # Run both demos
    telecom_graph, telecom_mcp = run_telecom_demo()
    healthcare_graph = run_healthcare_demo()

    print("\n\nDone! Open ecl_telecom_graph.html in a browser for interactive visualization.")
    print("Import .cypher files into Neo4j Browser for full graph database experience.")
