# CKG-lite
Nodes: Condition, Symptom, Intervention, ScreeningTool, CrisisSignal
Edges: has_symptom, helps_with, contraindicated_with, screened_by, escalate_on
Seeds: data/kg/{nodes.csv,edges.csv,synonyms.csv}
APIs: /kg/nodes, /kg/ground, /kg/pathway
