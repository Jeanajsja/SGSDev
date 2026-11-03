$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$kind = "$env:TEMP\kind.exe"
if (-not (Test-Path $kind)) {
    Invoke-WebRequest -Uri "https://kind.sigs.k8s.io/dl/v0.30.0/kind-windows-amd64" -OutFile $kind -UseBasicParsing
}

Write-Host "Apagando docker compose para liberar el puerto 8080..."
Set-Location $root
cmd /c "docker compose down >nul 2>&1"

$clusters = @(& $kind get clusters 2>$null)
if ($clusters -contains "sgsdev") {
    Write-Host "Recreando cluster Kind sgsdev..."
    & $kind delete cluster --name sgsdev
}
& $kind create cluster --name sgsdev --config "$PSScriptRoot\kind-config.yaml"
if ($LASTEXITCODE -ne 0) { throw "No se pudo crear el cluster Kind" }

Write-Host "Construyendo imagenes..."
docker build -t sgsdev-monolito:latest .
docker build -t sgsdev-login:latest ./services/login
docker build -t sgsdev-salones:latest ./services/salones
docker build -t sgsdev-docentes:latest ./services/docentes
docker build -t sgsdev-roles:latest ./services/roles
docker build -t sgsdev-usuarios:latest ./services/usuarios
docker build -t sgsdev-reservas:latest ./services/reservas

Write-Host "Cargando imagenes en Kind..."
foreach ($img in @(
    "sgsdev-monolito:latest","sgsdev-login:latest","sgsdev-salones:latest",
    "sgsdev-docentes:latest","sgsdev-roles:latest","sgsdev-usuarios:latest","sgsdev-reservas:latest"
)) { & $kind load docker-image $img --name sgsdev }

Write-Host "Aplicando manifiestos..."
kubectl apply -f "$PSScriptRoot\namespace.yaml"
kubectl apply -f "$PSScriptRoot\db-secret.yaml"
kubectl apply -f "$PSScriptRoot\login.yaml"
kubectl apply -f "$PSScriptRoot\salones.yaml"
kubectl apply -f "$PSScriptRoot\docentes.yaml"
kubectl apply -f "$PSScriptRoot\roles.yaml"
kubectl apply -f "$PSScriptRoot\usuarios.yaml"
kubectl apply -f "$PSScriptRoot\reservas.yaml"
kubectl apply -f "$PSScriptRoot\monolito.yaml"
kubectl apply -f "$PSScriptRoot\gateway.yaml"

foreach ($app in @("login","salones","docentes","roles","usuarios","reservas","monolito","gateway")) {
    kubectl -n sgsdev rollout status deployment/$app --timeout=180s
}

kubectl -n sgsdev get pods,svc
Write-Host ""
Write-Host "Sistema completo en Kubernetes: http://localhost:8080"
