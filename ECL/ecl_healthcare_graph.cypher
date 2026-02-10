// ============================================
// ECL Context Graph - Auto-Generated Cypher
// Generated: 2026-02-09T12:41:18.654842
// ============================================

// Clear previous data (CAUTION: removes all nodes)
// MATCH (n) DETACH DELETE n;

// Indexes for performance
CREATE INDEX IF NOT EXISTS FOR (n:Diagnosis) ON (n.id);
CREATE INDEX IF NOT EXISTS FOR (n:Medication) ON (n.id);
CREATE INDEX IF NOT EXISTS FOR (n:Person) ON (n.id);

// === CREATE NODES ===
CREATE (patient_john_smith:Person {id: 'patient_john_smith', name: 'John Smith', confidence: 0.95, source_expert: 'HealthcareExpert', role: 'patient'})
CREATE (medication_metformin:Medication {id: 'medication_metformin', name: 'Metformin', confidence: 0.9, source_expert: 'HealthcareExpert', dosage: '500mg'})
CREATE (medication_lisinopril:Medication {id: 'medication_lisinopril', name: 'Lisinopril', confidence: 0.9, source_expert: 'HealthcareExpert', dosage: '10mg'})
CREATE (medication_by:Medication {id: 'medication_by', name: 'by', confidence: 0.9, source_expert: 'HealthcareExpert', dosage: 'unknown'})
CREATE (medication_s:Medication {id: 'medication_s', name: 's', confidence: 0.9, source_expert: 'HealthcareExpert', dosage: 'unknown'})
CREATE (diagnosis_e11_9:Diagnosis {id: 'diagnosis_e11_9', name: 'Type 2 Diabetes (E11.9)', confidence: 0.95, source_expert: 'HealthcareExpert', icd10_code: 'E11.9', description: 'Type 2 Diabetes'})
CREATE (diagnosis_i10:Diagnosis {id: 'diagnosis_i10', name: 'Essential Hypertension (I10)', confidence: 0.95, source_expert: 'HealthcareExpert', icd10_code: 'I10', description: 'Essential Hypertension'})
CREATE (doctor_dr_jane_doe:Person {id: 'doctor_dr_jane_doe', name: 'Dr. Dr. Jane Doe', confidence: 0.9, source_expert: 'HealthcareExpert', role: 'doctor'})

// === CREATE RELATIONSHIPS ===
CREATE (patient_john_smith)-[:TAKES]->(medication_metformin)
CREATE (patient_john_smith)-[:TAKES]->(medication_lisinopril)
CREATE (patient_john_smith)-[:TAKES]->(medication_by)
CREATE (patient_john_smith)-[:TAKES]->(medication_s)
CREATE (patient_john_smith)-[:HAS_DIAGNOSIS]->(diagnosis_e11_9)
CREATE (patient_john_smith)-[:HAS_DIAGNOSIS]->(diagnosis_i10)
CREATE (patient_john_smith)-[:PRESCRIBED_BY]->(doctor_dr_jane_doe)

;