#!/bin/bash
set -e

cd /app/backend-rest/es.um.sisdist.backend.Service
mvn -B exec:java -Dexec.mainClass="es.um.sisdist.backend.Service.TestClient" -Dmaven.repo.local=/app/.m2/repository
