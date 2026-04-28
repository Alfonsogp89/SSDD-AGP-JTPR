package es.um.sisdist.backend.Service;

import java.net.URI;
import jakarta.ws.rs.client.Client;
import jakarta.ws.rs.client.ClientBuilder;
import jakarta.ws.rs.client.Entity;
import jakarta.ws.rs.client.WebTarget;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import jakarta.ws.rs.core.UriBuilder;

public class TestClient {
    public static void main(String[] args) {
        Client client = ClientBuilder.newClient();
        WebTarget baseTarget = client.target(getBaseURI());

        String userId = "2"; 
        String dialogueName = "test-java-client-" + System.currentTimeMillis();

        System.out.println("=== Iniciando Cliente de Prueba REST Java ===");

        // 1. Crear conversación
        System.out.println("\n[1] Creando diálogo: " + dialogueName);
        String createJson = "{\"name\":\"" + dialogueName + "\"}";
        Response createRes = baseTarget.path("u").path(userId).path("dialogue")
                .request(MediaType.APPLICATION_JSON)
                .post(Entity.json(createJson));
        System.out.println("Respuesta creación: " + createRes.getStatus() + " " + createRes.readEntity(String.class));

        // 2. Enviar Prompt
        System.out.println("\n[2] Enviando Prompt...");
        String promptJson = "{\"prompt\":\"Hola, esto es un mensaje de prueba desde TestClient en Java.\"}";
        Response promptRes = baseTarget.path("u").path(userId).path("dialogue").path(dialogueName).path("next")
                .request(MediaType.APPLICATION_JSON)
                .post(Entity.json(promptJson));
        System.out.println("Respuesta prompt: " + promptRes.getStatus() + " " + promptRes.readEntity(String.class));

        // 3. Consultar conversación
        System.out.println("\n[3] Obteniendo estado de la conversación...");
        Response getRes = baseTarget.path("u").path(userId).path("dialogue").path(dialogueName)
                .request(MediaType.APPLICATION_JSON)
                .get();
        System.out.println("Respuesta GET: " + getRes.getStatus() + "\n" + getRes.readEntity(String.class));
        
        System.out.println("\n=== Cliente de Prueba Terminado ===");
    }

    private static URI getBaseURI() {
        return UriBuilder.fromUri("http://localhost:8080/Service/").build();
    }
}