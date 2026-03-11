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

    public LlamaChatServiceImpl() {
        super();
        this.httpClient = HttpClient.newBuilder().version(HttpClient.Version.HTTP_2).build();
        // Obtener la URL del servicio de chat desde variables de entorno, o usar localhost por defecto
        this.llamaChatUrl = System.getenv().getOrDefault("LLAMACHAT_SERVICE_URL", "http://localhost:5000/prompt");
    }

    @Override
    public void sendPrompt(PromptRequest request, StreamObserver<PromptResponse> responseObserver) {
        logger.info("Received prompt request from user: " + request.getUserId() + " for dialogue: " + request.getDialogueId());

        try {
            // Construir JSON payload simple
            String jsonPayload = String.format("{\"prompt\": \"%s\"}", request.getPrompt().replace("\"", "\\\""));

            HttpRequest httpRequest = HttpRequest.newBuilder()
                    .uri(URI.create(this.llamaChatUrl))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(jsonPayload))
                    .build();

            HttpResponse<String> httpResponse = httpClient.send(httpRequest, HttpResponse.BodyHandlers.ofString());

            String responseMsg = httpResponse.body();
            boolean success = httpResponse.statusCode() == 200 || httpResponse.statusCode() == 201 || httpResponse.statusCode() == 202;

            // Si es 202 Accepted, el location suele venir en cabeceras o en el body (según la implementación de LlamaChat)
            if (httpResponse.statusCode() == 202) {
                responseMsg = "Processing in background: " + httpResponse.headers().firstValue("Location").orElse(responseMsg);
            } else if (httpResponse.statusCode() == 102) {
                responseMsg = "Model is initializing...";
            }

            PromptResponse response = PromptResponse.newBuilder()
                    .setSuccess(success)
                    .setMessage(responseMsg)
                    .build();

            responseObserver.onNext(response);
            responseObserver.onCompleted();

        } catch (IOException | InterruptedException e) {
            logger.severe("Error contacting LlamaChat service: " + e.getMessage());
            PromptResponse response = PromptResponse.newBuilder()
                    .setSuccess(false)
                    .setMessage("Error contacting LlamaChat service: " + e.getMessage())
                    .build();
            responseObserver.onNext(response);
            responseObserver.onCompleted();
        }
    }
}
