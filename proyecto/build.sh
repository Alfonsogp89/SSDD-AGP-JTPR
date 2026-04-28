#!/bin/bash
set -e

echo "Building DAO"
cd /app/backend/es.um.sisdist.backend.dao
mvn -B clean install -DskipTests -Dmaven.repo.local=/app/.m2/repository

echo "Building gRPC"
cd /app/backend-grpc/es.um.sisdist.backend.grpc.GrpcService
mvn -B clean install -DskipTests -Dmaven.repo.local=/app/.m2/repository

echo "Building Backend REST"
cd /app/backend-rest/es.um.sisdist.backend.Service
mvn -B clean package -DskipTests -Dmaven.repo.local=/app/.m2/repository
