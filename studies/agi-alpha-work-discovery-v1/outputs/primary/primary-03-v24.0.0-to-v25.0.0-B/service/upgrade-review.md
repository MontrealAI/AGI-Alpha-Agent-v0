# API response assurance / Vérification des réponses API

Source: /workspace/scratch/c4e9aee15454/agi-alpha/studies/agi-alpha-work-discovery-v1/inputs/acquired/v24.0.0.json -> /workspace/scratch/c4e9aee15454/agi-alpha/studies/agi-alpha-work-discovery-v1/inputs/acquired/v25.0.0.json
Structural changes / Changements structurels: 70
Responses assessed / Réponses évaluées: 43 -> 43
Unassessed scope records / Éléments hors portée: 355

Decision: review the exact changed fields before upgrading consumers. No whole-API compatibility approval is issued.
Décision : examiner les champs modifiés avant la mise à niveau des clients. Aucune approbation globale de compatibilité.

- ADDED: GET /containers/json 200 i:/p:NetworkSettings/p:Networks/a:/p:DNSNames/i:
- ADDED: GET /containers/json 200 i:/p:NetworkSettings/p:Networks/a:/p:DNSNames
- ADDED: GET /containers/{id}/json 200 p:Config/p:Healthcheck/p:StartInterval
- ADDED: GET /containers/{id}/json 200 p:HostConfig/allOf:1/p:Mounts/i:/p:BindOptions/p:ReadOnlyForceRecursive
- ADDED: GET /containers/{id}/json 200 p:HostConfig/allOf:1/p:Mounts/i:/p:BindOptions/p:ReadOnlyNonRecursive
- ADDED: GET /containers/{id}/json 200 p:NetworkSettings/p:Networks/a:/p:DNSNames/i:
- ADDED: GET /containers/{id}/json 200 p:NetworkSettings/p:Networks/a:/p:DNSNames
- ADDED: GET /images/{name}/json 200 p:Config/p:Healthcheck/p:StartInterval
- CHANGED: GET /images/{name}/json 200 p:Container
- ADDED: GET /images/{name}/json 200 p:ContainerConfig/p:Healthcheck/p:StartInterval
- ADDED: GET /info 200 p:CDISpecDirs/i:
- ADDED: GET /info 200 p:CDISpecDirs
- REMOVED: GET /info 200 p:ClusterAdvertise
- REMOVED: GET /info 200 p:ClusterStore
- ADDED: GET /info 200 p:Runtimes/a:/p:status/a:
- ADDED: GET /info 200 p:Runtimes/a:/p:status
- ADDED: GET /services 200 i:/p:Spec/p:TaskTemplate/p:ContainerSpec/p:HealthCheck/p:StartInterval
- ADDED: GET /services 200 i:/p:Spec/p:TaskTemplate/p:ContainerSpec/p:Mounts/i:/p:BindOptions/p:ReadOnlyForceRecursive
- ADDED: GET /services 200 i:/p:Spec/p:TaskTemplate/p:ContainerSpec/p:Mounts/i:/p:BindOptions/p:ReadOnlyNonRecursive
- ADDED: GET /services 200 i:/p:Spec/p:TaskTemplate/p:ContainerSpec/p:Privileges/p:AppArmor/p:Mode
- ADDED: GET /services 200 i:/p:Spec/p:TaskTemplate/p:ContainerSpec/p:Privileges/p:AppArmor
- ADDED: GET /services 200 i:/p:Spec/p:TaskTemplate/p:ContainerSpec/p:Privileges/p:NoNewPrivileges
- ADDED: GET /services 200 i:/p:Spec/p:TaskTemplate/p:ContainerSpec/p:Privileges/p:Seccomp/p:Mode
- ADDED: GET /services 200 i:/p:Spec/p:TaskTemplate/p:ContainerSpec/p:Privileges/p:Seccomp/p:Profile
- ADDED: GET /services 200 i:/p:Spec/p:TaskTemplate/p:ContainerSpec/p:Privileges/p:Seccomp
- ADDED: GET /services/{id} 200 p:Spec/p:TaskTemplate/p:ContainerSpec/p:HealthCheck/p:StartInterval
- ADDED: GET /services/{id} 200 p:Spec/p:TaskTemplate/p:ContainerSpec/p:Mounts/i:/p:BindOptions/p:ReadOnlyForceRecursive
- ADDED: GET /services/{id} 200 p:Spec/p:TaskTemplate/p:ContainerSpec/p:Mounts/i:/p:BindOptions/p:ReadOnlyNonRecursive
- ADDED: GET /services/{id} 200 p:Spec/p:TaskTemplate/p:ContainerSpec/p:Privileges/p:AppArmor/p:Mode
- ADDED: GET /services/{id} 200 p:Spec/p:TaskTemplate/p:ContainerSpec/p:Privileges/p:AppArmor
- ADDED: GET /services/{id} 200 p:Spec/p:TaskTemplate/p:ContainerSpec/p:Privileges/p:NoNewPrivileges
- ADDED: GET /services/{id} 200 p:Spec/p:TaskTemplate/p:ContainerSpec/p:Privileges/p:Seccomp/p:Mode
- ADDED: GET /services/{id} 200 p:Spec/p:TaskTemplate/p:ContainerSpec/p:Privileges/p:Seccomp/p:Profile
- ADDED: GET /services/{id} 200 p:Spec/p:TaskTemplate/p:ContainerSpec/p:Privileges/p:Seccomp
- ADDED: GET /system/df 200 p:Containers/i:/p:NetworkSettings/p:Networks/a:/p:DNSNames/i:
- ADDED: GET /system/df 200 p:Containers/i:/p:NetworkSettings/p:Networks/a:/p:DNSNames
- ADDED: GET /tasks 200 i:/p:Spec/p:ContainerSpec/p:HealthCheck/p:StartInterval
- ADDED: GET /tasks 200 i:/p:Spec/p:ContainerSpec/p:Mounts/i:/p:BindOptions/p:ReadOnlyForceRecursive
- ADDED: GET /tasks 200 i:/p:Spec/p:ContainerSpec/p:Mounts/i:/p:BindOptions/p:ReadOnlyNonRecursive
- ADDED: GET /tasks 200 i:/p:Spec/p:ContainerSpec/p:Privileges/p:AppArmor/p:Mode
- ADDED: GET /tasks 200 i:/p:Spec/p:ContainerSpec/p:Privileges/p:AppArmor
- ADDED: GET /tasks 200 i:/p:Spec/p:ContainerSpec/p:Privileges/p:NoNewPrivileges
- ADDED: GET /tasks 200 i:/p:Spec/p:ContainerSpec/p:Privileges/p:Seccomp/p:Mode
- ADDED: GET /tasks 200 i:/p:Spec/p:ContainerSpec/p:Privileges/p:Seccomp/p:Profile
- ADDED: GET /tasks 200 i:/p:Spec/p:ContainerSpec/p:Privileges/p:Seccomp
- ADDED: GET /tasks 200 i:/p:Status/p:PortStatus/p:Ports/i:/p:Name
- ADDED: GET /tasks 200 i:/p:Status/p:PortStatus/p:Ports/i:/p:Protocol
- ADDED: GET /tasks 200 i:/p:Status/p:PortStatus/p:Ports/i:/p:PublishMode
- ADDED: GET /tasks 200 i:/p:Status/p:PortStatus/p:Ports/i:/p:PublishedPort
- ADDED: GET /tasks 200 i:/p:Status/p:PortStatus/p:Ports/i:/p:TargetPort
- ADDED: GET /tasks 200 i:/p:Status/p:PortStatus/p:Ports/i:
- ADDED: GET /tasks 200 i:/p:Status/p:PortStatus/p:Ports
- ADDED: GET /tasks 200 i:/p:Status/p:PortStatus
- ADDED: GET /tasks/{id} 200 p:Spec/p:ContainerSpec/p:HealthCheck/p:StartInterval
- ADDED: GET /tasks/{id} 200 p:Spec/p:ContainerSpec/p:Mounts/i:/p:BindOptions/p:ReadOnlyForceRecursive
- ADDED: GET /tasks/{id} 200 p:Spec/p:ContainerSpec/p:Mounts/i:/p:BindOptions/p:ReadOnlyNonRecursive
- ADDED: GET /tasks/{id} 200 p:Spec/p:ContainerSpec/p:Privileges/p:AppArmor/p:Mode
- ADDED: GET /tasks/{id} 200 p:Spec/p:ContainerSpec/p:Privileges/p:AppArmor
- ADDED: GET /tasks/{id} 200 p:Spec/p:ContainerSpec/p:Privileges/p:NoNewPrivileges
- ADDED: GET /tasks/{id} 200 p:Spec/p:ContainerSpec/p:Privileges/p:Seccomp/p:Mode
- ADDED: GET /tasks/{id} 200 p:Spec/p:ContainerSpec/p:Privileges/p:Seccomp/p:Profile
- ADDED: GET /tasks/{id} 200 p:Spec/p:ContainerSpec/p:Privileges/p:Seccomp
- ADDED: GET /tasks/{id} 200 p:Status/p:PortStatus/p:Ports/i:/p:Name
- ADDED: GET /tasks/{id} 200 p:Status/p:PortStatus/p:Ports/i:/p:Protocol
- ADDED: GET /tasks/{id} 200 p:Status/p:PortStatus/p:Ports/i:/p:PublishMode
- ADDED: GET /tasks/{id} 200 p:Status/p:PortStatus/p:Ports/i:/p:PublishedPort
- ADDED: GET /tasks/{id} 200 p:Status/p:PortStatus/p:Ports/i:/p:TargetPort
- ADDED: GET /tasks/{id} 200 p:Status/p:PortStatus/p:Ports/i:
- ADDED: GET /tasks/{id} 200 p:Status/p:PortStatus/p:Ports
- ADDED: GET /tasks/{id} 200 p:Status/p:PortStatus

- Structural GET 2xx JSON schema surface assessment, not blanket compatibility certification.
- Optional property removal is a review signal, not necessarily a contract violation.
- Conjunction branch order may produce structural differences without semantic difference.
- Server behavior, authentication, requests, default/error responses and client runtime are outside scope.
