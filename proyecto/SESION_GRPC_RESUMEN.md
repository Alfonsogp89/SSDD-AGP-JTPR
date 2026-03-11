# Resumen de Sesión – Implementación gRPC (Sesión 03)
**Fecha:** 11 de marzo de 2026  
**Asignatura:** Sistemas Distribuidos (SSDD 25-26)  
**Proyecto:** LlamaChat

---

## Objetivo

Implementar la comunicación gRPC entre el backend REST y el servidor gRPC, conectando con el contenedor `ssdd-llamachat-dummy` para el procesamiento de prompts.

---

## 1. Estado del proyecto al inicio

Los ficheros `.proto` ya estaban definidos:

| Fichero | Servicio | RPC |
|---|---|---|
| `grpcservice.proto` | `GrpcService` | `Ping(PingRequest) → PingResponse` |
| `chat.proto` | `LlamaChatService` | `SendPrompt(PromptRequest) → PromptResponse` |

La implementación del servidor gRPC (`LlamaChatServiceImpl.java`) ya existía pero no estaba conectada con el backend REST.

---

## 2. Cambios realizados

### 2.1 `AppLogicImpl.java` (backend-rest)
**Fichero:** `proyecto/backend-rest/es.um.sisdist.backend.Service/src/es/um/sisdist/backend/Service/impl/AppLogicImpl.java`

- Añadido import de `LlamaChatServiceGrpc`, `PromptRequest`, `PromptResponse`
- Añadido campo `chatStub` (stub bloqueante de `LlamaChatService`) usando el mismo `ManagedChannel`
- Añadido método `sendPrompt(int userId, String dialogueId, String prompt)` que construye el `PromptRequest` y llama al servidor gRPC

```java
private final LlamaChatServiceGrpc.LlamaChatServiceBlockingStub chatStub;
// En el constructor:
chatStub = LlamaChatServiceGrpc.newBlockingStub(channel);

// Nuevo método:
public PromptResponse sendPrompt(int userId, String dialogueId, String prompt) { ... }
```

### 2.2 `ChatEndpoint.java` (backend-rest) — NUEVO
**Fichero:** `proyecto/backend-rest/es.um.sisdist.backend.Service/src/es/um/sisdist/backend/Service/ChatEndpoint.java`

Endpoint REST `POST /Service/chat` que:
- Recibe `{"userId": 1, "dialogueId": "...", "prompt": "..."}`
- Llama a `AppLogicImpl.sendPrompt()` → gRPC → LlamaChat
- Devuelve `{"success": true/false, "message": "..."}`
- JWT **no validado** en esta entrega (según indicaciones)

### 2.3 `pom.xml` (backend-rest)
**Fichero:** `proyecto/backend-rest/es.um.sisdist.backend.Service/pom.xml`

Añadidas dependencias de runtime gRPC necesarias para ejecutar el cliente dentro de Tomcat:
- `io.grpc:grpc-netty:1.79.0`
- `io.grpc:grpc-stub:1.79.0`
- `io.grpc:grpc-protobuf:1.79.0`
- `jakarta.annotation:jakarta.annotation-api:3.0.0`

### 2.4 `pom.xml` (GrpcServiceImpl)
**Fichero:** `proyecto/backend-grpc/es.um.sisdist.backend.grpc.GrpcServiceImpl/pom.xml`

Eliminada la dependencia `dao` que estaba declarada pero ninguna clase gRPC la utilizaba. Esto permite compilar el módulo gRPC de forma independiente al módulo `backend`.

### 2.5 `docker-compose-devel.yml`
**Fichero:** `proyecto/docker-compose-devel.yml`

Añadida variable de entorno al servicio `backend-grpc`:
```yaml
environment:
  - LLAMACHAT_SERVICE_URL=http://ssdd-llamachat:5020/prompt
```
Sin esto, el servidor gRPC buscaba `localhost:5000` en lugar del contenedor llamachat.

---

## 3. Problemas encontrados y soluciones

| Problema | Causa | Solución |
|---|---|---|
| `docker-credential-desktop.exe: exec format error` | WSL usaba el credential helper de Windows | `echo '{}' > ~/.docker/config.json` |
| `Could not find artifact dao:0.0.1-SNAPSHOT` | `GrpcServiceImpl` dependía de `dao` innecesariamente | Eliminar la dependencia del `pom.xml` |
| `getcwd: No such file or directory` | WSL perdió referencia al directorio actual | Usar `cd /mnt/c/...` con ruta absoluta |
| `pull access denied for dsevilla/ssdd-backend-rest` | Docker Compose buscaba imagen en Docker Hub | Usar `docker-compose-devel.yml` (usa `build:` local) |
| `404 en /ping/1` | URL incorrecta: WAR se despliega en `/Service/` | Ruta correcta: `http://localhost:8080/Service/ping` |
| `Error contacting LlamaChat: null` | Dummy no levantado + URL de red Docker incorrecta | Construir dummy + añadir `LLAMACHAT_SERVICE_URL` |

---

## 4. Orden de compilación correcto

```bash
# 1. DAO (necesario para backend-rest)
cd proyecto && make backend

# 2. GrpcService (genera stubs proto) + GrpcServiceImpl (servidor)
make backend-grpc

# 3. Backend REST
make backend-rest
```

---

## 5. Arranque del sistema

```bash
cd /mnt/c/Users/alfon/Desktop/ssdd-25-26/proyecto

# Construir imagen dummy LlamaChat (solo la primera vez)
cd llamachat && docker build -f Dockerfile-dummy -t dsevilla/ssdd-llamachat:1.0 . && cd ..

# Levantar los servicios necesarios
docker-compose -f docker-compose-devel.yml up db-mysql backend-grpc backend-rest ssdd-llamachat
```

---

## 6. Verificación — Pruebas realizadas

### Ping (verifica comunicación REST → gRPC)
```bash
curl http://localhost:8080/Service/ping
# Resultado: true ✅
```

### Chat (verifica flujo completo REST → gRPC → LlamaChat)
```bash
curl -X POST http://localhost:8080/Service/chat \
  -H "Content-Type: application/json" \
  -d '{"userId": 1, "dialogueId": "test-001", "prompt": "Hola mundo"}'
# Resultado: {"message":"Processing in background: /response/...","success":true} ✅
```

### Consultar respuesta del prompt (async)
```bash
curl http://localhost:5020/response/<TOKEN>
# Resultado: {"prompt": "Hola mundo", "answer": "DUMMY Generated response..."} ✅
```

---

## 7. Arquitectura del flujo implementado

```
Cliente HTTP
    │
    ▼ POST /Service/chat
backend-rest (Tomcat :8080)
  ChatEndpoint.java
    │
    ▼ gRPC SendPrompt (LlamaChatServiceGrpc)
backend-grpc (:50051)
  LlamaChatServiceImpl.java
    │
    ▼ HTTP POST /prompt
sssd-llamachat-dummy (:5020)
    │
    ▼ 202 Accepted + Location: /response/{token}
  (procesamiento asíncrono)
```

---

## 8. Notas para siguientes entregas

- **JWT**: En esta entrega el `userId` se pasa en el body sin validación. En futuras entregas habrá que extraerlo del token JWT de la cabecera `Authorization`.
- **Kafka**: La siguiente sesión introducirá Kafka para el log de sesiones de prompt.
- **Tests E2E**: Pendiente implementar con Selenium.
