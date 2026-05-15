# Script para compilar y levantar todo el entorno de desarrollo de SSDD
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "1/3. Compilando dependencias de Backend Java (Maven)..." -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan

docker run --rm -v "${PWD}:/app" -w /app maven:3.9.6-eclipse-temurin-17 /bin/bash -c "mvn -B -f backend/es.um.sisdist.backend.dao/pom.xml clean install -DskipTests && mvn -B -f backend-grpc/es.um.sisdist.backend.grpc.GrpcService/pom.xml clean install -DskipTests && mvn -B -f backend-rest/es.um.sisdist.backend.Service/pom.xml clean package -DskipTests"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error en la compilación de dependencias Maven. Cancelando despliegue." -ForegroundColor Red
    Exit $LASTEXITCODE
}

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host "2/3. Reconstruyendo y levantando contenedores de Docker..." -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan

docker compose -f docker-compose-devel.yml up --build -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error levantando los servicios de Docker." -ForegroundColor Red
    Exit $LASTEXITCODE
}

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host "3/3. Escenario levantado correctamente." -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan

docker compose -f docker-compose-devel.yml ps
