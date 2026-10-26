# API response assurance / Vérification des réponses API

Source: studies/agi-alpha-work-discovery-v1/inputs/discovery-docker-v25.0.0.json -> studies/agi-alpha-work-discovery-v1/inputs/discovery-docker-v26.0.0.json
Structural changes / Changements structurels: 6
Responses assessed / Réponses évaluées: 43 -> 43
Unassessed scope records / Éléments hors portée: 370

Decision: review the exact changed fields before upgrading consumers. No whole-API compatibility approval is issued.
Décision : examiner les champs modifiés avant la mise à niveau des clients. Aucune approbation globale de compatibilité.

- ADDED: GET /containers/{id}/json 200 p:HostConfig/allOf:1/p:Mounts/i:/p:VolumeOptions/p:Subpath
- CHANGED: GET /images/{name}/json 200 p:Created
- ADDED: GET /services 200 i:/p:Spec/p:TaskTemplate/p:ContainerSpec/p:Mounts/i:/p:VolumeOptions/p:Subpath
- ADDED: GET /services/{id} 200 p:Spec/p:TaskTemplate/p:ContainerSpec/p:Mounts/i:/p:VolumeOptions/p:Subpath
- ADDED: GET /tasks 200 i:/p:Spec/p:ContainerSpec/p:Mounts/i:/p:VolumeOptions/p:Subpath
- ADDED: GET /tasks/{id} 200 p:Spec/p:ContainerSpec/p:Mounts/i:/p:VolumeOptions/p:Subpath

- Structural GET 2xx JSON schema surface assessment, not blanket compatibility certification.
- Optional property removal is a review signal, not necessarily a contract violation.
- Conjunction branch order may produce structural differences without semantic difference.
- Server behavior, authentication, requests, default/error responses and client runtime are outside scope.
