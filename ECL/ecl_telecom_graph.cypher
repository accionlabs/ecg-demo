// ============================================
// ECL Context Graph - Auto-Generated Cypher
// Generated: 2026-02-09T12:41:18.652896
// ============================================

// Clear previous data (CAUTION: removes all nodes)
// MATCH (n) DETACH DELETE n;

// Indexes for performance
CREATE INDEX IF NOT EXISTS FOR (n:Company) ON (n.id);
CREATE INDEX IF NOT EXISTS FOR (n:Contract) ON (n.id);
CREATE INDEX IF NOT EXISTS FOR (n:Equipment) ON (n.id);
CREATE INDEX IF NOT EXISTS FOR (n:Financial) ON (n.id);
CREATE INDEX IF NOT EXISTS FOR (n:Opportunity) ON (n.id);
CREATE INDEX IF NOT EXISTS FOR (n:Risk) ON (n.id);
CREATE INDEX IF NOT EXISTS FOR (n:Tower) ON (n.id);

// === CREATE NODES ===
CREATE (tower_t789:Tower {id: 'tower_t789', name: 'Tower T-789', confidence: 1.0, source_expert: 'manual', location: '40.6892° N, 74.0445° W', type: 'Monopole', height: '150ft'})
CREATE (contract_SUMMARY:Contract {id: 'contract_SUMMARY', name: 'Contract #SUMMARY', confidence: 0.92, source_expert: 'ContractExpert', contract_id: 'SUMMARY', company: 'Verizon', status: 'ACTIVE', monthly_revenue: '5,000', outstanding_amount: '9,000'})
CREATE (company_verizon:Company {id: 'company_verizon', name: 'Verizon', confidence: 0.95, source_expert: 'ContractExpert'})
CREATE (contract_67890:Contract {id: 'contract_67890', name: 'Contract #67890', confidence: 0.92, source_expert: 'ContractExpert', contract_id: '67890', company: 'DISH', status: 'DEFAULTED', monthly_revenue: '3,000', outstanding_amount: ','})
CREATE (company_dish:Company {id: 'company_dish', name: 'DISH', confidence: 0.95, source_expert: 'ContractExpert'})
CREATE (equipment_6_antennas_0:Equipment {id: 'equipment_6_antennas_0', name: '6 antennas', confidence: 0.88, source_expert: 'EquipmentExpert', type: '6 antennas', status: 'Operational', quantity: '6', drone_observation: 'rusted mounting brackets on south face'})
CREATE (equipment_1_satellite_dish_1:Equipment {id: 'equipment_1_satellite_dish_1', name: '1 Satellite Dish', confidence: 0.88, source_expert: 'EquipmentExpert', type: '1 Satellite Dish', status: 'Inactive', quantity: '4'})
CREATE (equipment_dish_from_dish_network_shows_corrosion_2:Equipment {id: 'equipment_dish_from_dish_network_shows_corrosion_2', name: 'dish from DISH Network shows corrosion', confidence: 0.88, source_expert: 'EquipmentExpert', type: 'dish from DISH Network shows corrosion', status: 'unknown', quantity: '1'})
CREATE (equipment_must_be_removed_per_defaulted_contract_terms_3:Equipment {id: 'equipment_must_be_removed_per_defaulted_contract_terms_3', name: 'must be removed per defaulted contract terms', confidence: 0.88, source_expert: 'EquipmentExpert', type: 'must be removed per defaulted contract terms', status: 'unknown', quantity: '1'})
CREATE (risk_payment_default_0:Risk {id: 'risk_payment_default_0', name: 'Payment Default Risk #1', confidence: 0.9, source_expert: 'FinancialRiskExpert', risk_type: 'PAYMENT_DEFAULT', days_overdue: 0, amount_outstanding: 'unknown', severity: 'MEDIUM', payment_issues_count: 0})
CREATE (risk_payment_default_1:Risk {id: 'risk_payment_default_1', name: 'Payment Default Risk #2', confidence: 0.9, source_expert: 'FinancialRiskExpert', risk_type: 'PAYMENT_DEFAULT', days_overdue: 0, amount_outstanding: 'unknown', severity: 'MEDIUM', payment_issues_count: 0})
CREATE (risk_payment_default_2:Risk {id: 'risk_payment_default_2', name: 'Payment Default Risk #3', confidence: 0.9, source_expert: 'FinancialRiskExpert', risk_type: 'PAYMENT_DEFAULT', days_overdue: 0, amount_outstanding: ',', severity: 'MEDIUM', payment_issues_count: 0})
CREATE (risk_payment_default_3:Risk {id: 'risk_payment_default_3', name: 'Payment Default Risk #4', confidence: 0.9, source_expert: 'FinancialRiskExpert', risk_type: 'PAYMENT_DEFAULT', days_overdue: 0, amount_outstanding: 'unknown', severity: 'MEDIUM', payment_issues_count: 0})
CREATE (risk_payment_default_4:Risk {id: 'risk_payment_default_4', name: 'Payment Default Risk #5', confidence: 0.9, source_expert: 'FinancialRiskExpert', risk_type: 'PAYMENT_DEFAULT', days_overdue: 0, amount_outstanding: 'unknown', severity: 'MEDIUM', payment_issues_count: 0})
CREATE (financial_exposure_summary:Financial {id: 'financial_exposure_summary', name: 'Revenue Exposure Summary', confidence: 0.85, source_expert: 'FinancialRiskExpert', total_annual_exposure: 44000.0, risk_factors: 5})
CREATE (opportunity_removal_0:Opportunity {id: 'opportunity_removal_0', name: 'Equipment Removal #1', confidence: 0.91, source_expert: 'OpportunityExpert', opportunity_type: 'EQUIPMENT_REMOVAL', details: 'dish from DISH Network shows corrosion', reasoning: 'Defaulted equipment must be removed per contract terms', action_required: true})
CREATE (opportunity_maintenance_0:Opportunity {id: 'opportunity_maintenance_0', name: 'Maintenance Required #1', confidence: 0.93, source_expert: 'OpportunityExpert', opportunity_type: 'MAINTENANCE', details: 'mounting brackets on south face', severity: 'HIGH', reasoning: 'Safety/compliance issue detected - requires immediate attention'})
CREATE (opportunity_maintenance_1:Opportunity {id: 'opportunity_maintenance_1', name: 'Maintenance Required #2', confidence: 0.93, source_expert: 'OpportunityExpert', opportunity_type: 'MAINTENANCE', details: '', severity: 'HIGH', reasoning: 'Safety/compliance issue detected - requires immediate attention'})

// === CREATE RELATIONSHIPS ===
CREATE (company_verizon)-[:HAS_CONTRACT {status: 'ACTIVE'}]->(contract_SUMMARY)
CREATE (company_dish)-[:HAS_CONTRACT {status: 'DEFAULTED'}]->(contract_67890)
CREATE (tower_t789)-[:HAS_CONTRACT]->(contract_SUMMARY)
CREATE (contract_SUMMARY)-[:WITH_CLIENT]->(company_verizon)
CREATE (tower_t789)-[:HAS_CONTRACT]->(contract_67890)
CREATE (contract_67890)-[:WITH_CLIENT]->(company_dish)
CREATE (tower_t789)-[:HAS_EQUIPMENT]->(equipment_6_antennas_0)
CREATE (tower_t789)-[:HAS_EQUIPMENT]->(equipment_1_satellite_dish_1)
CREATE (tower_t789)-[:HAS_EQUIPMENT]->(equipment_dish_from_dish_network_shows_corrosion_2)
CREATE (tower_t789)-[:HAS_EQUIPMENT]->(equipment_must_be_removed_per_defaulted_contract_terms_3)
CREATE (tower_t789)-[:HAS_RISK]->(risk_payment_default_0)
CREATE (tower_t789)-[:HAS_RISK]->(risk_payment_default_1)
CREATE (tower_t789)-[:HAS_RISK]->(risk_payment_default_2)
CREATE (tower_t789)-[:HAS_RISK]->(risk_payment_default_3)
CREATE (tower_t789)-[:HAS_RISK]->(risk_payment_default_4)
CREATE (tower_t789)-[:HAS_OPPORTUNITY]->(opportunity_removal_0)
CREATE (tower_t789)-[:HAS_OPPORTUNITY]->(opportunity_maintenance_0)
CREATE (tower_t789)-[:HAS_OPPORTUNITY]->(opportunity_maintenance_1)

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