package es.um.sisdist.backend.Service;

import java.net.URI;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.ws.rs.client.Client;
import jakarta.ws.rs.client.ClientBuilder;
import jakarta.ws.rs.client.Entity;
import jakarta.ws.rs.client.WebTarget;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import jakarta.ws.rs.core.UriBuilder;

public class TestClient
{
    private static final ObjectMapper mapper = new ObjectMapper();

    public static void main(String[] args) throws Exception
    {
        Client client = ClientBuilder.newClient();
        WebTarget base = client.target(getBaseURI());

        String email = "testclient-" + System.currentTimeMillis() + "@test.com";
        String password = "testpass123";
        String dialogueName = "test-dialogue-" + System.currentTimeMillis();

        System.out.println("=== Iniciando Cliente de Prueba REST Java ===");

        // 1. Registrar usuario
        System.out.println("\n[1] Registrando usuario: " + email);
        Response regRes = base.path("u")
                .request(MediaType.APPLICATION_JSON)
                .post(Entity.json("{\"email\":\"" + email + "\",\"password\":\"" + password + "\",\"name\":\"TestUser\"}"));
        String regBody = regRes.readEntity(String.class);
        System.out.println("  -> " + regRes.getStatus() + " " + regBody);
        if (regRes.getStatus() != 201) { System.out.println("ERROR: registro fallido"); return; }

        String userId = mapper.readTree(regBody).get("id").asText();
        System.out.println("  userId: " + userId);

        // 2. Autenticarse y obtener JWT
        System.out.println("\n[2] Autenticando...");
        Response loginRes = base.path("checkLogin")
                .request(MediaType.APPLICATION_JSON)
                .post(Entity.json("{\"email\":\"" + email + "\",\"password\":\"" + password + "\"}"));
        String loginBody = loginRes.readEntity(String.class);
        System.out.println("  -> " + loginRes.getStatus());
        if (loginRes.getStatus() != 200) { System.out.println("ERROR: login fallido\n" + loginBody); return; }

        String jwtToken = mapper.readTree(loginBody).get("jwtToken").asText();
        System.out.println("  JWT obtenido: " + jwtToken.substring(0, Math.min(40, jwtToken.length())) + "...");

        // 3. Crear diálogo
        System.out.println("\n[3] Creando diálogo: " + dialogueName);
        Response createRes = base.path("u").path(userId).path("dialogue")
                .request(MediaType.APPLICATION_JSON)
                .header("Authorization", "Bearer " + jwtToken)
                .post(Entity.json("{\"name\":\"" + dialogueName + "\"}"));
        System.out.println("  -> " + createRes.getStatus() + " " + createRes.readEntity(String.class));

        // 4. Enviar prompt
        System.out.println("\n[4] Enviando prompt...");
        Response promptRes = base.path("u").path(userId).path("dialogue").path(dialogueName).path("next")
                .request(MediaType.APPLICATION_JSON)
                .header("Authorization", "Bearer " + jwtToken)
                .post(Entity.json("{\"prompt\":\"Hola, esto es una prueba desde TestClient.\"}"));
        System.out.println("  -> " + promptRes.getStatus() + " " + promptRes.readEntity(String.class));

        // 5. Mostrar diálogo
        System.out.println("\n[5] Consultando diálogo...");
        Response getRes = base.path("u").path(userId).path("dialogue").path(dialogueName)
                .request(MediaType.APPLICATION_JSON)
                .header("Authorization", "Bearer " + jwtToken)
                .get();
        System.out.println("  -> " + getRes.getStatus() + "\n" + getRes.readEntity(String.class));

        // 6. Eliminar diálogo
        System.out.println("\n[6] Eliminando diálogo...");
        Response deleteRes = base.path("u").path(userId).path("dialogue").path(dialogueName)
                .request(MediaType.APPLICATION_JSON)
                .header("Authorization", "Bearer " + jwtToken)
                .delete();
        System.out.println("  -> " + deleteRes.getStatus() + " " + deleteRes.readEntity(String.class));

        System.out.println("\n=== Cliente de Prueba Terminado ===");
    }

    private static URI getBaseURI()
    {
        return UriBuilder.fromUri("http://localhost:8080/Service/").build();
    }
}
