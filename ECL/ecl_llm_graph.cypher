// ============================================
// ECL Context Graph - Auto-Generated Cypher
// Generated: 2026-02-07T21:07:46.907563
// ============================================

// Clear previous data (CAUTION: removes all nodes)
// MATCH (n) DETACH DELETE n;

// Indexes for performance
CREATE INDEX IF NOT EXISTS FOR (n:Company) ON (n.id);
CREATE INDEX IF NOT EXISTS FOR (n:Contract) ON (n.id);
CREATE INDEX IF NOT EXISTS FOR (n:Equipment) ON (n.id);
CREATE INDEX IF NOT EXISTS FOR (n:Financial) ON (n.id);
CREATE INDEX IF NOT EXISTS FOR (n:Risk) ON (n.id);
CREATE INDEX IF NOT EXISTS FOR (n:Tower) ON (n.id);

// === CREATE NODES ===
CREATE (tower_t789:Tower {id: 'tower_t789', name: 'Tower T-789', confidence: 1.0, source_expert: 'manual', location: '40.6892° N, 74.0445° W', type: 'Monopole', height: '150ft'})
CREATE (contract_12345:Contract {id: 'contract_12345', name: 'Contract #12345', confidence: 0.95, source_expert: 'LLMContractExpert', contract_id: '12345', company: 'Verizon', status: 'ACTIVE', occupancy_pct: 80, monthly_revenue: 5000, outstanding_amount: 0})
CREATE (contract_67890:Contract {id: 'contract_67890', name: 'Contract #67890', confidence: 0.95, source_expert: 'LLMContractExpert', contract_id: '67890', company: 'DISH', status: 'DEFAULTED', occupancy_pct: 15, monthly_revenue: 3000, outstanding_amount: 9000})
CREATE (company_verizon:Company {id: 'company_verizon', name: 'Verizon', confidence: 0.96, source_expert: 'LLMContractExpert', is_active: true})
CREATE (company_dish:Company {id: 'company_dish', name: 'DISH', confidence: 0.96, source_expert: 'LLMContractExpert', is_active: false})
CREATE (equipment_verizon_antennas_0:Equipment {id: 'equipment_verizon_antennas_0', name: 'Verizon Antennas', confidence: 0.93, source_expert: 'LLMEquipmentExpert', equipment_type: 'antenna', quantity: 6, status: 'operational', company: 'Verizon', drone_observation: 'no issues detected'})
CREATE (equipment_dish_satellite_dish_1:Equipment {id: 'equipment_dish_satellite_dish_1', name: 'DISH Satellite Dish', confidence: 0.93, source_expert: 'LLMEquipmentExpert', equipment_type: 'dish', quantity: 1, status: 'inactive', company: 'DISH', drone_observation: 'corrosion'})
CREATE (risk_payment_default_0:Risk {id: 'risk_payment_default_0', name: 'PAYMENT_DEFAULT #1', confidence: 0.92, source_expert: 'LLMFinancialRiskExpert', risk_type: 'PAYMENT_DEFAULT', description: 'DISH equipment must be removed per defaulted contract terms', days_overdue: 90, amount_outstanding: 9000, severity: 'HIGH', affected_entity: 'Contract #67890'})
CREATE (risk_revenue_loss_1:Risk {id: 'risk_revenue_loss_1', name: 'REVENUE_LOSS #2', confidence: 0.92, source_expert: 'LLMFinancialRiskExpert', risk_type: 'REVENUE_LOSS', description: 'Potential revenue loss from DISH\'s defaulted contract', days_overdue: 0, amount_outstanding: 36000, severity: 'CRITICAL', affected_entity: 'DISH'})
CREATE (financial_exposure_summary:Financial {id: 'financial_exposure_summary', name: 'Revenue Exposure Summary', confidence: 0.9, source_expert: 'LLMFinancialRiskExpert', total_annual_revenue: 48000, total_at_risk: 45000, risk_count: 2})

// === CREATE RELATIONSHIPS ===
CREATE (company_verizon)-[:HAS_CONTRACT {status: 'Active'}]->(contract_12345)
CREATE (company_dish)-[:HAS_CONTRACT {status: 'Defaulted'}]->(contract_67890)
CREATE (contract_12345)-[:OCCUPIES]->(tower_t789)
CREATE (contract_67890)-[:OCCUPIES]->(tower_t789)
CREATE (equipment_verizon_antennas_0)-[:INSTALLED_ON]->(tower_t789)
CREATE (equipment_dish_satellite_dish_1)-[:INSTALLED_ON]->(tower_t789)
CREATE (tower_t789)-[:HAS_RISK]->(risk_payment_default_0)
CREATE (tower_t789)-[:HAS_RISK]->(risk_revenue_loss_1)

;

// ============================================
// ECL Agent Query Library
// ============================================

// Q1: Find all opportunities for a tower
MATCH (t:Tower)-[:HAS_OPPORTUNITY]->(o:Opportunity)
RETURN t.name AS tower, o.name AS opportunity,
       o.opportunity_type AS type, o.potential_monthly_uplift AS uplift
ORDER BY o.potential_monthly_uplift DESC;

// Q2: Identify equipment needing removal
MATCH (e:Equipment {status: 'inactive'})-[:INSTALLED_ON]->(t:Tower)
MATCH (c:Company)-[:HAS_EQUIPMENT]->(e)
RETURN t.name AS tower, c.name AS company, e.name AS equipment;

// Q3: Get complete tower context (for AI agent)
MATCH (t:Tower {id: $tower_id})
OPTIONAL MATCH (t)<-[:OCCUPIES]-(c:Contract)
OPTIONAL MATCH (t)<-[:HAS_EQUIPMENT]-(co:Company)
OPTIONAL MATCH (t)-[:HAS_OPPORTUNITY]->(o:Opportunity)
OPTIONAL MATCH (t)-[:HAS_RISK]->(r:Risk)
RETURN t, collect(DISTINCT c) AS contracts,
       collect(DISTINCT co) AS companies,
       collect(DISTINCT o) AS opportunities,
       collect(DISTINCT r) AS risks;

// Q4: Calculate total revenue at risk
MATCH (r:Risk)-[:AFFECTS]->(c:Contract)
RETURN sum(toFloat(c.outstanding_amount)) AS total_arrears,
       sum(toFloat(c.monthly_revenue) * 12) AS annual_at_risk;

// Q5: Cross-company relationship discovery
MATCH path = (c1:Company)-[*1..3]-(c2:Company)
WHERE c1 <> c2
RETURN c1.name, c2.name, [r IN relationships(path) | type(r)] AS via;