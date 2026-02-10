#!/usr/bin/env python3
"""
ECL FalkorDB Module - Live Graph Database Integration
Replaces Neo4j Cypher file generation with live FalkorDB graph operations.
"""

import json
from dataclasses import asdict
from typing import List, Dict, Optional, Any
from datetime import datetime

# Import base types from ecl_poc
from ecl_poc import (
    Entity, Relationship, ExtractionResult,
    EntityType, RelationshipType,
    BaseExpert, MoEOrchestrator, ContextGraphBuilder,
    ContractExpert, EquipmentExpert, FinancialRiskExpert, OpportunityExpert
)


# ============================================================
# SECTION 1: FALKORDB CLIENT
# ============================================================

class FalkorDBClient:
    """Client wrapper for FalkorDB graph database."""

    def __init__(self, host: str = None, port: int = None, graph_name: str = "ecl_graph"):
        import os
        self.host = host or os.getenv("FALKORDB_HOST", "localhost")
        self.port = port or int(os.getenv("FALKORDB_PORT", "6379"))
        self.graph_name = graph_name
        self._db = None
        self._graph = None
        self._available = None

    def connect(self) -> bool:
        """Connect to FalkorDB server."""
        try:
            from falkordb import FalkorDB
            self._db = FalkorDB(host=self.host, port=self.port)
            self._graph = self._db.select_graph(self.graph_name)
            self._available = True
            return True
        except Exception as e:
            print(f"  [FalkorDB] Connection failed: {e}")
            self._available = False
            return False

    def is_available(self) -> bool:
        """Check if FalkorDB is connected."""
        if self._available is None:
            self.connect()
        return self._available

    @property
    def graph(self):
        """Get the graph instance."""
        if self._graph is None:
            self.connect()
        return self._graph

    def query(self, cypher: str, params: Dict = None) -> Optional[Any]:
        """Execute a Cypher query."""
        if not self.is_available():
            return None
        try:
            result = self.graph.query(cypher, params or {})
            return result
        except Exception as e:
            print(f"  [FalkorDB Query Error] {e}")
            return None

    def clear_graph(self) -> bool:
        """Clear all nodes and relationships from the graph."""
        if not self.is_available():
            return False
        try:
            self.graph.query("MATCH (n) DETACH DELETE n")
            return True
        except Exception as e:
            print(f"  [FalkorDB Clear Error] {e}")
            return False


# ============================================================
# SECTION 2: FALKORDB GRAPH BUILDER
# ============================================================

class FalkorDBGraphBuilder:
    """Builds and writes graph directly to FalkorDB."""

    def __init__(self, client: FalkorDBClient):
        self.client = client
        self.nodes: Dict[str, Entity] = {}
        self.edges: List[Relationship] = []
        self._nodes_written = 0
        self._edges_written = 0

    def add_entity(self, entity: Entity) -> bool:
        """Add an entity node to the graph."""
        if entity.id in self.nodes:
            # Merge properties
            self.nodes[entity.id].properties.update(entity.properties)
            return True

        self.nodes[entity.id] = entity

        if not self.client.is_available():
            return False

        # Build properties dict - convert all values to safe types
        props = {
            "id": entity.id,
            "name": entity.name,
            "confidence": entity.confidence,
            "source_expert": entity.source_expert,
        }
        # Add entity properties, converting to strings for safety
        for k, v in entity.properties.items():
            if isinstance(v, bool):
                props[k] = v
            elif isinstance(v, (int, float)):
                props[k] = v
            else:
                props[k] = str(v)

        # Build inline properties for Cypher (FalkorDB doesn't support $props parameter)
        prop_parts = []
        for k, v in props.items():
            if isinstance(v, str):
                escaped = v.replace("'", "\\'")
                prop_parts.append(f"{k}: '{escaped}'")
            elif isinstance(v, bool):
                prop_parts.append(f"{k}: {'true' if v else 'false'}")
            else:
                prop_parts.append(f"{k}: {v}")
        props_str = "{" + ", ".join(prop_parts) + "}"

        # Create node
        cypher = f"CREATE (n:{entity.type.value} {props_str})"
        result = self.client.query(cypher)

        if result is not None:
            self._nodes_written += 1
            return True
        return False

    def add_relationship(self, rel: Relationship) -> bool:
        """Add a relationship edge to the graph."""
        self.edges.append(rel)

        if not self.client.is_available():
            return False

        # Build properties inline (FalkorDB doesn't support $props parameter)
        prop_parts = []
        for k, v in rel.properties.items():
            if isinstance(v, str):
                escaped = v.replace("'", "\\'")
                prop_parts.append(f"{k}: '{escaped}'")
            elif isinstance(v, bool):
                prop_parts.append(f"{k}: {'true' if v else 'false'}")
            elif isinstance(v, (int, float)):
                prop_parts.append(f"{k}: {v}")
            else:
                prop_parts.append(f"{k}: '{str(v)}'")

        props_str = ""
        if prop_parts:
            props_str = " {" + ", ".join(prop_parts) + "}"

        # Escape IDs for query
        src_id = rel.source_id.replace("'", "\\'")
        tgt_id = rel.target_id.replace("'", "\\'")

        cypher = f"""
        MATCH (a {{id: '{src_id}'}}), (b {{id: '{tgt_id}'}})
        CREATE (a)-[r:{rel.type.value}{props_str}]->(b)
        """
        result = self.client.query(cypher)

        if result is not None:
            self._edges_written += 1
            return True
        return False

    def add_extraction_results(self, results: Dict[str, ExtractionResult]):
        """Add all entities and relationships from extraction results."""
        for expert_name, extraction in results.items():
            for entity in extraction.entities:
                self.add_entity(entity)
            for rel in extraction.relationships:
                self.add_relationship(rel)

    def get_stats(self) -> Dict:
        """Get graph statistics."""
        return {
            "nodes_in_memory": len(self.nodes),
            "edges_in_memory": len(self.edges),
            "nodes_written": self._nodes_written,
            "edges_written": self._edges_written,
            "connected": self.client.is_available(),
        }


# ============================================================
# SECTION 3: FALKORDB MCP TOOL SERVER
# ============================================================

class FalkorDBMCPServer:
    """
    MCP Server with live FalkorDB queries.
    Provides real-time graph access for AI agents.
    """

    def __init__(self, client: FalkorDBClient):
        self.client = client
        self.tools = {
            "get_tower_context": self.get_tower_context,
            "find_opportunities": self.find_opportunities,
            "assess_risk": self.assess_risk,
            "get_company_relationships": self.get_company_relationships,
            "search_entities": self.search_entities,
            "run_cypher": self.run_cypher,
        }

    def list_tools(self) -> List[Dict]:
        """MCP tools/list - Returns available tools."""
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
                "description": "Find upsell, cross-sell, and maintenance opportunities",
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
                "description": "Assess financial and operational risks",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "entity_id": {"type": "string"}
                    }
                }
            },
            {
                "name": "get_company_relationships",
                "description": "Get all relationships for a company",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "company_name": {"type": "string"}
                    }
                }
            },
            {
                "name": "search_entities",
                "description": "Search entities by type or keyword",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "entity_type": {"type": "string"},
                        "keyword": {"type": "string"}
                    }
                }
            },
            {
                "name": "run_cypher",
                "description": "Execute a raw Cypher query against the graph",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Cypher query to execute"}
                    },
                    "required": ["query"]
                }
            },
        ]

    def call_tool(self, tool_name: str, arguments: Dict) -> Dict:
        """MCP tools/call - Execute a tool."""
        if tool_name not in self.tools:
            return {"error": f"Unknown tool: {tool_name}"}
        return self.tools[tool_name](**arguments)

    def get_tower_context(self, tower_id: str) -> Dict:
        """Get complete tower context via live Cypher query."""
        result = self.client.query("""
            MATCH (t:Tower)
            WHERE t.id CONTAINS $tower_id OR t.name CONTAINS $tower_id
            OPTIONAL MATCH (c:Contract)-[:OCCUPIES]->(t)
            OPTIONAL MATCH (e:Equipment)-[:INSTALLED_ON]->(t)
            OPTIONAL MATCH (t)-[:HAS_OPPORTUNITY]->(o:Opportunity)
            OPTIONAL MATCH (t)-[:HAS_RISK]->(r:Risk)
            RETURN t, collect(DISTINCT c) AS contracts,
                   collect(DISTINCT e) AS equipment,
                   collect(DISTINCT o) AS opportunities,
                   collect(DISTINCT r) AS risks
        """, {"tower_id": tower_id})

        if result is None or len(result.result_set) == 0:
            return {"error": f"Tower {tower_id} not found"}

        row = result.result_set[0]
        return {
            "tower": self._node_to_dict(row[0]) if row[0] else None,
            "contracts": [self._node_to_dict(n) for n in row[1] if n],
            "equipment": [self._node_to_dict(n) for n in row[2] if n],
            "opportunities": [self._node_to_dict(n) for n in row[3] if n],
            "risks": [self._node_to_dict(n) for n in row[4] if n],
        }

    def find_opportunities(self, opportunity_type: str = "ALL") -> Dict:
        """Find opportunities via live query."""
        if opportunity_type == "ALL":
            result = self.client.query("""
                MATCH (o:Opportunity)
                RETURN o
            """)
        else:
            result = self.client.query("""
                MATCH (o:Opportunity)
                WHERE o.opportunity_type = $type
                RETURN o
            """, {"type": opportunity_type})

        if result is None:
            return {"opportunities": [], "count": 0}

        opportunities = [self._node_to_dict(row[0]) for row in result.result_set if row[0]]
        return {
            "opportunities": opportunities,
            "count": len(opportunities),
            "filter": opportunity_type,
        }

    def assess_risk(self, entity_id: str = "") -> Dict:
        """Assess risks via live query."""
        result = self.client.query("""
            MATCH (r:Risk)
            RETURN r
        """)

        fin_result = self.client.query("""
            MATCH (f:Financial)
            RETURN f
        """)

        risks = []
        if result:
            risks = [self._node_to_dict(row[0]) for row in result.result_set if row[0]]

        financials = []
        if fin_result:
            financials = [self._node_to_dict(row[0]) for row in fin_result.result_set if row[0]]

        return {
            "risks": risks,
            "financial_summary": financials,
            "total_risks": len(risks),
        }

    def get_company_relationships(self, company_name: str) -> Dict:
        """Get company relationships via live query."""
        result = self.client.query("""
            MATCH (c:Company)-[r]-(n)
            WHERE c.name CONTAINS $name
            RETURN c, type(r) AS rel_type, n
        """, {"name": company_name})

        if result is None or len(result.result_set) == 0:
            return {"error": f"Company {company_name} not found"}

        company = None
        relationships = []
        for row in result.result_set:
            if row[0] and not company:
                company = self._node_to_dict(row[0])
            if row[1] and row[2]:
                relationships.append({
                    "type": row[1],
                    "target": self._node_to_dict(row[2])
                })

        return {
            "company": company,
            "relationships": relationships,
            "relationship_count": len(relationships),
        }

    def search_entities(self, entity_type: str = "", keyword: str = "") -> Dict:
        """Search entities via live query."""
        if entity_type:
            result = self.client.query(f"""
                MATCH (n:{entity_type})
                WHERE n.name CONTAINS $keyword OR n.id CONTAINS $keyword
                RETURN n
            """, {"keyword": keyword or ""})
        else:
            result = self.client.query("""
                MATCH (n)
                WHERE n.name CONTAINS $keyword OR n.id CONTAINS $keyword
                RETURN n
            """, {"keyword": keyword or ""})

        if result is None:
            return {"results": [], "count": 0}

        entities = [self._node_to_dict(row[0]) for row in result.result_set if row[0]]
        return {"results": entities, "count": len(entities)}

    def run_cypher(self, query: str) -> Dict:
        """Execute arbitrary Cypher query."""
        result = self.client.query(query)
        if result is None:
            return {"error": "Query failed"}

        return {
            "result_set": [[str(col) for col in row] for row in result.result_set],
            "row_count": len(result.result_set),
        }

    @staticmethod
    def _node_to_dict(node) -> Dict:
        """Convert FalkorDB node to dictionary."""
        if node is None:
            return {}
        try:
            return dict(node.properties)
        except:
            return {"raw": str(node)}


# ============================================================
# SECTION 4: DEMO RUNNER
# ============================================================

def run_falkordb_demo():
    """Run the ECL pipeline with live FalkorDB integration."""

    print("=" * 60)
    print("  ECL FalkorDB Demo")
    print("  Live Graph Database Integration")
    print("=" * 60)

    # --- Connect to FalkorDB ---
    print("\n[STEP 1] Connecting to FalkorDB")
    print("-" * 40)

    client = FalkorDBClient(graph_name="ecl_telecom")

    if not client.connect():
        print("  ✗ FalkorDB not available. Make sure it's running:")
        print("    docker run -p 6379:6379 falkordb/falkordb")
        print("\n  Falling back to file-based Cypher generation...")
        # Fall back to original ContextGraphBuilder
        from ecl_poc import run_telecom_demo
        return run_telecom_demo()

    print(f"  ✓ Connected to FalkorDB at {client.host}:{client.port}")
    print(f"  ✓ Graph: {client.graph_name}")

    # Clear existing data
    print("  Clearing existing graph data...")
    client.clear_graph()

    # --- Load Sample Document ---
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sample_doc = os.path.join(script_dir, "sample_documents", "tower_site_report_T789.md")

    print(f"  Loading: {os.path.basename(sample_doc)}")
    with open(sample_doc, 'r') as f:
        telecom_text = f.read()
    print(f"  Document size: {len(telecom_text):,} characters")

    # --- MoE Extraction ---
    print("\n[STEP 2] MoE Expert Extraction")
    print("-" * 40)

    orchestrator = MoEOrchestrator()
    results = orchestrator.extract_all(telecom_text)

    # --- Build Live Graph ---
    print("\n[STEP 3] Writing to FalkorDB")
    print("-" * 40)

    graph_builder = FalkorDBGraphBuilder(client)

    # Add tower as root node
    tower = Entity(
        id="tower_t789",
        type=EntityType.TOWER,
        name="Tower T-789",
        properties={
            "location": "40.6892N_74.0445W",
            "tower_type": "Monopole",
            "height": "150ft",
        },
        source_expert="manual",
        confidence=1.0
    )
    graph_builder.add_entity(tower)

    # Add extraction results
    graph_builder.add_extraction_results(results)

    # Add tower relationships
    for entity in graph_builder.nodes.values():
        if entity.type == EntityType.CONTRACT:
            graph_builder.add_relationship(Relationship(
                entity.id, tower.id, RelationshipType.OCCUPIES, confidence=0.95
            ))
        elif entity.type == EntityType.OPPORTUNITY:
            graph_builder.add_relationship(Relationship(
                tower.id, entity.id, RelationshipType.HAS_OPPORTUNITY, confidence=0.90
            ))
        elif entity.type == EntityType.RISK:
            graph_builder.add_relationship(Relationship(
                tower.id, entity.id, RelationshipType.HAS_RISK, confidence=0.90
            ))
        elif entity.type == EntityType.EQUIPMENT:
            graph_builder.add_relationship(Relationship(
                entity.id, tower.id, RelationshipType.INSTALLED_ON, confidence=0.88
            ))

    stats = graph_builder.get_stats()
    print(f"  Nodes written: {stats['nodes_written']}")
    print(f"  Edges written: {stats['edges_written']}")

    # --- MCP Server Demo ---
    print("\n[STEP 4] MCP Agent Interface (Live Queries)")
    print("-" * 40)

    mcp = FalkorDBMCPServer(client)

    print("\n  Available MCP Tools:")
    for tool in mcp.list_tools():
        print(f"    - {tool['name']}: {tool['description'][:50]}...")

    print("\n  Live Query: find_opportunities(type='ALL')")
    opps = mcp.find_opportunities(opportunity_type="ALL")
    print(f"  Result: {opps['count']} opportunities found")
    for opp in opps.get("opportunities", []):
        print(f"    → {opp.get('name', 'Unknown')} [{opp.get('opportunity_type', 'N/A')}]")

    print("\n  Live Query: assess_risk()")
    risks = mcp.assess_risk()
    print(f"  Result: {risks['total_risks']} risks identified")

    print("\n  Live Query: get_tower_context('t789')")
    context = mcp.get_tower_context("t789")
    if "error" not in context:
        print(f"  Tower: {context.get('tower', {}).get('name', 'Unknown')}")
        print(f"  Contracts: {len(context.get('contracts', []))}")
        print(f"  Equipment: {len(context.get('equipment', []))}")
        print(f"  Opportunities: {len(context.get('opportunities', []))}")
        print(f"  Risks: {len(context.get('risks', []))}")

    # --- Summary ---
    print("\n" + "=" * 60)
    print("  ECL FalkorDB Demo Complete!")
    print("=" * 60)
    print(f"  Graph: {client.graph_name}")
    print(f"  Nodes: {stats['nodes_written']}")
    print(f"  Edges: {stats['edges_written']}")
    print(f"  MCP Tools: {len(mcp.list_tools())}")
    print("=" * 60)

    return graph_builder, mcp


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    import sys

    if "--test" in sys.argv:
        run_falkordb_demo()
    else:
        print("ECL FalkorDB Module")
        print("Usage: python3 ecl_falkordb.py --test")
        print("\nThis module provides FalkorDB graph database integration for ECL.")
        print("Requires FalkorDB server: docker run -p 6379:6379 falkordb/falkordb")
