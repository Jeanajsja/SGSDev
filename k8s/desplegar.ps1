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
docker build -t sgsdev-login:latest -f services/login/Dockerfile .
docker build -t sgsdev-salones:latest -f services/salones/Dockerfile .
docker build -t sgsdev-docentes:latest -f services/docentes/Dockerfile .
docker build -t sgsdev-roles:latest -f services/roles/Dockerfile .
docker build -t sgsdev-usuarios:latest -f services/usuarios/Dockerfile .
docker build -t sgsdev-reservas:latest -f services/reservas/Dockerfile .

Write-Host "Cargando imagenes en Kind..."
foreach ($img in @(
    "sgsdev-monolito:latest","sgsdev-login:latest","sgsdev-salones:latest",
    "sgsdev-docentes:latest","sgsdev-roles:latest","sgsdev-usuarios:latest","sgsdev-reservas:latest"
)) { & $kind load docker-image $img --name sgsdev }

Write-Host "Aplicando manifiestos..."
kubectl apply -f "$PSScriptRoot\namespace.yaml"
$envFile = Join-Path $root ".env"
if (-not (Test-Path $envFile)) {
    throw "Falta .env. Créalo desde .env.example y configura DB_*, JWT_SECRET y el aprovisionamiento inicial."
}
kubectl -n sgsdev create secret generic sgsdev-db --from-env-file="$envFile" --dry-run=client -o yaml |
    kubectl apply -f -
if ($LASTEXITCODE -ne 0) { throw "No se pudo crear el secreto de Kubernetes desde .env" }
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
