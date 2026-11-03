# Kubernetes - SGSDev

Cada microservicio tiene su propio archivo YAML.

| Archivo | Servicio |
|---|---|
| login.yaml | ms-login |
| salones.yaml | ms-salones |
| docentes.yaml | ms-docentes |
| roles.yaml | ms-roles |
| usuarios.yaml | ms-usuarios |
| reservas.yaml | ms-reservas |
| monolito.yaml | pantallas |
| gateway.yaml | Nginx (localhost:8080) |

```powershell
.\k8s\desplegar.ps1
```
