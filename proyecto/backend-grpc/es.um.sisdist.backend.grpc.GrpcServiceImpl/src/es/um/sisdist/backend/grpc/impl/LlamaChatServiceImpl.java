package es.um.sisdist.backend.grpc.impl;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.logging.Logger;

import es.um.sisdist.backend.grpc.chat.LlamaChatServiceGrpc;
import es.um.sisdist.backend.grpc.chat.PromptRequest;
import es.um.sisdist.backend.grpc.chat.PromptResponse;
import io.grpc.stub.StreamObserver;

public class LlamaChatServiceImpl extends LlamaChatServiceGrpc.LlamaChatServiceImplBase {

    private static final Logger logger = Logger.getLogger(LlamaChatServiceImpl.class.getName());
    private final HttpClient httpClient;
    private final String llamaChatUrl;
    // Base URL para construir URLs absolutas a partir de Location relativas
    private final String llamaChatBase;

    public LlamaChatServiceImpl() {
        super();
        this.httpClient = HttpClient.newBuilder().version(HttpClient.Version.HTTP_1_1).build();
        // Obtener la URL del servicio de chat desde variables de entorno
        this.llamaChatUrl = System.getenv().getOrDefault("LLAMACHAT_SERVICE_URL", "http://localhost:5020/prompt");
        // Extraer la base (scheme + host + port) para construir URLs absolutas
        URI uri = URI.create(this.llamaChatUrl);
        this.llamaChatBase = uri.getScheme() + "://" + uri.getHost()
                + (uri.getPort() != -1 ? ":" + uri.getPort() : "");
    }

    @Override
    public void sendPrompt(PromptRequest request, StreamObserver<PromptResponse> responseObserver) {
        logger.info("Received prompt request from user: " + request.getUserId()
                + " for dialogue: " + request.getDialogueId());

        try {
            // Construir JSON payload
            String jsonPayload = String.format("{\"prompt\": \"%s\"}",
                    request.getPrompt().replace("\\", "\\\\").replace("\"", "\\\""));

            HttpRequest httpRequest = HttpRequest.newBuilder()
                    .uri(URI.create(this.llamaChatUrl))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(jsonPayload))
                    .build();

            HttpResponse<String> httpResponse = httpClient.send(httpRequest,
                    HttpResponse.BodyHandlers.ofString());

            String responseMsg = httpResponse.body();
            boolean success = false;

            if (httpResponse.statusCode() == 200 || httpResponse.statusCode() == 201) {
                // Respuesta directa
                success = true;

            } else if (httpResponse.statusCode() == 202) {
                // El modelo procesa en background: hacer polling de la URL Location
                String location = httpResponse.headers().firstValue("Location").orElse(null);
                if (location != null) {
                    String pollUrl = location.startsWith("http") ? location : llamaChatBase + location;
                    logger.info("Polling response URL: " + pollUrl);
                    responseMsg = pollForResponse(pollUrl);
                    success = true;
                } else {
                    responseMsg = "202 Accepted (no Location header)";
                    success = true;
                }

            } else if (httpResponse.statusCode() == 102) {
                responseMsg = "El modelo LlamaChat se esta inicializando. Intentalo en unos segundos.";

            } else {
                responseMsg = "Error del servicio LlamaChat: HTTP " + httpResponse.statusCode();
            }

            responseObserver.onNext(PromptResponse.newBuilder()
                    .setSuccess(success).setMessage(responseMsg).build());
            responseObserver.onCompleted();

        } catch (IOException | InterruptedException e) {
            logger.severe("Error contacting LlamaChat service: " + e.getMessage());
            responseObserver.onNext(PromptResponse.newBuilder()
                    .setSuccess(false)
                    .setMessage("Error contacting LlamaChat service: " + e.getMessage())
                    .build());
            responseObserver.onCompleted();
        }
    }

    /**
     * Hace polling de la URL de respuesta hasta obtener 200 o agotar el timeout.
     * El dummy devuelve la respuesta tras ~5 segundos.
     */
    private String pollForResponse(String pollUrl) throws IOException, InterruptedException {
        int maxAttempts = 30; // 30 intentos x 1s = 30s maximo
        for (int i = 0; i < maxAttempts; i++) {
            Thread.sleep(1000);
            HttpRequest pollRequest = HttpRequest.newBuilder()
                    .uri(URI.create(pollUrl))
                    .GET()
                    .build();
            try {
                HttpResponse<String> pollResponse = httpClient.send(pollRequest,
                        HttpResponse.BodyHandlers.ofString());
                if (pollResponse.statusCode() == 200) {
                    logger.info("Got response after " + (i + 1) + " poll attempt(s)");
                    return pollResponse.body();
                }
                // 102 o cualquier otro codigo -> seguir esperando
                logger.info("Poll attempt " + (i + 1) + ": status=" + pollResponse.statusCode() + ", retrying...");
            } catch (IOException ex) {
                logger.warning("Poll attempt " + (i + 1) + " failed: " + ex.getMessage());
            }
        }
        return "Timeout: no se recibio respuesta del modelo en 30 segundos.";
    }
}
