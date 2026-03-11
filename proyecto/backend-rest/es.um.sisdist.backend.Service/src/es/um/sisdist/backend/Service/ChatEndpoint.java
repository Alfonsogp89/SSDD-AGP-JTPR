package es.um.sisdist.backend.Service;

import es.um.sisdist.backend.Service.impl.AppLogicImpl;
import es.um.sisdist.backend.grpc.chat.PromptResponse;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;

/**
 * Endpoint REST para enviar prompts al modelo LlamaChat a través del servidor gRPC.
 *
 * POST /chat  →  llama a AppLogicImpl.sendPrompt  →  gRPC LlamaChatService  →  dummy/real
 *
 * NOTA: Para esta entrega NO se valida JWT. La cabecera Authorization se ignora.
 */
@Path("/chat")
public class ChatEndpoint
{
    private AppLogicImpl impl = AppLogicImpl.getInstance();

    // DTO interno para el body de la petición
    public static class PromptRequestDTO
    {
        public int userId;
        public String dialogueId;
        public String prompt;
    }

    // DTO interno para la respuesta
    public static class PromptResponseDTO
    {
        public boolean success;
        public String message;

        public PromptResponseDTO(boolean success, String message)
        {
            this.success = success;
            this.message = message;
        }
    }

    /**
     * Recibe un prompt y lo reenvía al servidor gRPC.
     *
     * Ejemplo de body:
     * {
     *   "userId": 1,
     *   "dialogueId": "dial-001",
     *   "prompt": "¿Cuál es la capital de Francia?"
     * }
     */
    @POST
    @Consumes(MediaType.APPLICATION_JSON)
    @Produces(MediaType.APPLICATION_JSON)
    public Response sendPrompt(PromptRequestDTO req)
    {
        if (req == null || req.prompt == null || req.prompt.isBlank())
            return Response.status(Response.Status.BAD_REQUEST)
                    .entity(new PromptResponseDTO(false, "El campo 'prompt' es obligatorio"))
                    .build();

        // Si no se proporciona userId se asigna un valor por defecto (sin JWT en esta entrega)
        int userId = req.userId > 0 ? req.userId : 1;
        String dialogueId = (req.dialogueId != null && !req.dialogueId.isBlank())
                ? req.dialogueId : "default-dialogue";

        try
        {
            PromptResponse grpcResponse = impl.sendPrompt(userId, dialogueId, req.prompt);
            PromptResponseDTO dto = new PromptResponseDTO(grpcResponse.getSuccess(), grpcResponse.getMessage());
            return Response.ok(dto).build();
        }
        catch (Exception e)
        {
            return Response.status(Response.Status.SERVICE_UNAVAILABLE)
                    .entity(new PromptResponseDTO(false, "Error contactando el servidor gRPC: " + e.getMessage()))
                    .build();
        }
    }
}
