# API response assurance / Vérification des réponses API

Source: /workspace/scratch/c4e9aee15454/agi-alpha/studies/agi-alpha-work-discovery-v1/inputs/acquired/v23.0.0.json -> /workspace/scratch/c4e9aee15454/agi-alpha/studies/agi-alpha-work-discovery-v1/inputs/acquired/v24.0.0.json
Structural changes / Changements structurels: 8
Responses assessed / Réponses évaluées: 43 -> 43
Unassessed scope records / Éléments hors portée: 341

Decision: review the exact changed fields before upgrading consumers. No whole-API compatibility approval is issued.
Décision : examiner les champs modifiés avant la mise à niveau des clients. Aucune approbation globale de compatibilité.

- ADDED: GET /containers/{id}/json 200 p:HostConfig/allOf:1/p:Annotations/a:
- ADDED: GET /containers/{id}/json 200 p:HostConfig/allOf:1/p:Annotations
- CHANGED: GET /containers/{id}/json 200 p:HostConfig/allOf:1/p:ShmSize
- CHANGED: GET /images/json 200 i:/p:VirtualSize
- CHANGED: GET /images/json 200 i:
- CHANGED: GET /images/{name}/json 200 p:VirtualSize
- CHANGED: GET /system/df 200 p:Images/i:/p:VirtualSize
- CHANGED: GET /system/df 200 p:Images/i:

- Structural GET 2xx JSON schema surface assessment, not blanket compatibility certification.
- Optional property removal is a review signal, not necessarily a contract violation.
- Conjunction branch order may produce structural differences without semantic difference.
- Server behavior, authentication, requests, default/error responses and client runtime are outside scope.
