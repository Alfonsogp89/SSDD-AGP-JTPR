package es.um.sisdist.backend.Service;

import es.um.sisdist.backend.Service.impl.AppLogicImpl;
import es.um.sisdist.models.DialogueDTO;
import es.um.sisdist.models.MessageDTO;
import jakarta.ws.rs.*;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.sql.*;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

/**
 * Endpoint REST para gestionar diálogos/conversaciones de usuarios.
 * 
 * Endpoints:
 * GET    /u/{userId}/dialogue              → lista de diálogos del usuario
 * POST   /u/{userId}/dialogue              → crear nuevo diálogo
 * GET    /u/{userId}/dialogue/{dialogueName} → obtener un diálogo específico
 * PUT    /u/{userId}/dialogue/{dialogueName} → actualizar/crear diálogo
 * POST   /u/{userId}/dialogue/{dialogueName}/next → enviar prompt
 */
@Path("/u/{userId}/dialogue")
public class DialogueEndpoint
{
    private AppLogicImpl impl = AppLogicImpl.getInstance();
    private ObjectMapper mapper = new ObjectMapper()
            .registerModule(new com.fasterxml.jackson.datatype.jsr310.JavaTimeModule());

    /**
     * GET /u/{userId}/dialogue
     * Obtiene la lista de diálogos del usuario
     */
    @GET
    @Produces(MediaType.APPLICATION_JSON)
    public Response listDialogues(@PathParam("userId") int userId)
    {
        try
        {
            List<DialogueDTO> dialogues = getDialoguesFromDB(userId);
            String json = mapper.writeValueAsString(java.util.Map.of("dialogues", dialogues));
            return Response.ok(json).type(MediaType.APPLICATION_JSON).build();
        }
        catch (Exception e)
        {
            return Response.status(500).entity("{\"error\":\"" + e.getMessage() + "\"}").build();
        }
    }

    /**
     * POST /u/{userId}/dialogue
     * Crea un nuevo diálogo
     * Body: {"name": "dialogue_name"}
     */
    @POST
    @Consumes(MediaType.APPLICATION_JSON)
    @Produces(MediaType.APPLICATION_JSON)
    public Response createDialogue(@PathParam("userId") int userId, String body)
    {
        try
        {
            JsonNode json = mapper.readTree(body);
            String dialogueName = json.has("name") ? json.get("name").asText() : "default-" + System.currentTimeMillis();

            // Insertar en BD
            String sql = "INSERT INTO dialogues (user_id, name, status) VALUES (?, ?, 'READY')";
            try (Connection conn = getConnection(); PreparedStatement pstmt = conn.prepareStatement(sql))
            {
                pstmt.setInt(1, userId);
                pstmt.setString(2, dialogueName);
                pstmt.executeUpdate();
            }

            return Response.status(201).entity("{\"status\":\"created\",\"name\":\"" + dialogueName + "\"}").build();
        }
        catch (SQLException e)
        {
            if (e.getMessage().contains("Duplicate entry"))
                return Response.status(409).entity("{\"error\":\"Dialogue already exists\"}").build();
            return Response.status(500).entity("{\"error\":\"" + e.getMessage() + "\"}").build();
        }
        catch (Exception e)
        {
            return Response.status(500).entity("{\"error\":\"" + e.getMessage() + "\"}").build();
        }
    }

    /**
     * GET /u/{userId}/dialogue/{dialogueName}
     * Obtiene un diálogo específico con sus mensajes
     */
    @GET
    @Path("/{dialogueName}")
    @Produces(MediaType.APPLICATION_JSON)
    public Response getDialogue(@PathParam("userId") int userId, @PathParam("dialogueName") String dialogueName)
    {
        try
        {
            DialogueDTO dialogue = getDialogueFromDB(userId, dialogueName);
            if (dialogue == null)
                return Response.status(404).entity("{\"error\":\"Dialogue not found\"}").build();

            String json = mapper.writeValueAsString(java.util.Map.of("dialogue", dialogue));
            return Response.ok(json).type(MediaType.APPLICATION_JSON).build();
        }
        catch (Exception e)
        {
            return Response.status(500).entity("{\"error\":\"" + e.getMessage() + "\"}").build();
        }
    }
    
    /**
     * DELETE /u/{userId}/dialogue/{dialogueName}
     * Elimina un diálogo específico
     */
    @DELETE
    @Path("/{dialogueName}")
    @Produces(MediaType.APPLICATION_JSON)
    public Response deleteDialogue(@PathParam("userId") int userId, @PathParam("dialogueName") String dialogueName)
    {
        try
        {
            DialogueDTO d = getDialogueFromDB(userId, dialogueName);
            if (d == null)
            {
                return Response.status(404).entity("{\"error\":\"Dialogue not found\"}").build();
            }

            // Eliminar mensajes asociados primero
            String sqlMessages = "DELETE FROM messages WHERE dialogue_id = ?";
            String sqlDialogue = "DELETE FROM dialogues WHERE id = ?";

            try (Connection conn = getConnection())
            {
                conn.setAutoCommit(false);
                try (PreparedStatement pstmtMsg = conn.prepareStatement(sqlMessages);
                     PreparedStatement pstmtDlg = conn.prepareStatement(sqlDialogue))
                {
                    pstmtMsg.setInt(1, d.id);
                    pstmtMsg.executeUpdate();

                    pstmtDlg.setInt(1, d.id);
                    pstmtDlg.executeUpdate();

                    conn.commit();
                }
                catch (SQLException e)
                {
                    conn.rollback();
                    throw e;
                }
            }

            return Response.ok("{\"status\":\"deleted\",\"name\":\"" + dialogueName + "\"}").build();
        }
        catch (Exception e)
        {
            return Response.status(500).entity("{\"error\":\"" + e.getMessage() + "\"}").build();
        }
    }

    /**
     * PUT /u/{userId}/dialogue/{dialogueName}
     * Crea o actualiza un diálogo
     */
    @PUT
    @Path("/{dialogueName}")
    @Consumes(MediaType.APPLICATION_JSON)
    @Produces(MediaType.APPLICATION_JSON)
    public Response upsertDialogue(@PathParam("userId") int userId, @PathParam("dialogueName") String dialogueName, String body)
    {
        try
        {
            String sql = "INSERT INTO dialogues (user_id, name, status) VALUES (?, ?, 'READY') " +
                    "ON DUPLICATE KEY UPDATE status = VALUES(status)";
            try (Connection conn = getConnection(); PreparedStatement pstmt = conn.prepareStatement(sql))
            {
                pstmt.setInt(1, userId);
                pstmt.setString(2, dialogueName);
                pstmt.executeUpdate();
            }

            return Response.status(200).entity("{\"status\":\"updated\"}").build();
        }
        catch (Exception e)
        {
            return Response.status(500).entity("{\"error\":\"" + e.getMessage() + "\"}").build();
        }
    }

    /**
     * POST /u/{userId}/dialogue/{dialogueName}/next
     * Envía un prompt al diálogo
     */
    @POST
    @Path("/{dialogueName}/next")
    @Consumes(MediaType.APPLICATION_JSON)
    @Produces(MediaType.APPLICATION_JSON)
    public Response sendPrompt(@PathParam("userId") int userId, @PathParam("dialogueName") String dialogueName, String body)
    {
        try
        {
            JsonNode json = mapper.readTree(body);
            String prompt = json.has("prompt") ? json.get("prompt").asText() : "";

            if (prompt.isEmpty())
                return Response.status(400).entity("{\"error\":\"prompt is required\"}").build();

            // Obtener diálogo y verificar estado
            DialogueDTO dialogue = getDialogueFromDB(userId, dialogueName);
            if (dialogue == null)
                return Response.status(404).entity("{\"error\":\"Dialogue not found\"}").build();

            // Agregar mensaje del usuario a la BD
            addMessageToDB(dialogue.id, "user", prompt);

            // Llamar al servicio gRPC para obtener respuesta
            impl.sendPrompt(userId, dialogueName, prompt);
            
            return Response.status(201).entity("{\"status\":\"accepted\"}").build();
        }
        catch (Exception e)
        {
            return Response.status(500).entity("{\"error\":\"" + e.getMessage() + "\"}").build();
        }
    }

    /**
     * Obtiene lista de diálogos desde BD
     */
    private List<DialogueDTO> getDialoguesFromDB(int userId) throws SQLException
    {
        List<DialogueDTO> dialogues = new ArrayList<>();
        String sql = "SELECT id, name, status, created_at FROM dialogues WHERE user_id = ? ORDER BY updated_at DESC";

        try (Connection conn = getConnection(); PreparedStatement pstmt = conn.prepareStatement(sql))
        {
            pstmt.setInt(1, userId);
            try (ResultSet rs = pstmt.executeQuery())
            {
                while (rs.next())
                {
                    DialogueDTO d = new DialogueDTO();
                    d.id = rs.getInt("id");
                    d.name = rs.getString("name");
                    d.status = rs.getString("status");
                    d.createdAt = rs.getTimestamp("created_at").toLocalDateTime();
                    d.messages = new ArrayList<>();
                    dialogues.add(d);
                }
            }
        }
        return dialogues;
    }

    /**
     * Obtiene un diálogo específico con sus mensajes desde BD
     */
    private DialogueDTO getDialogueFromDB(int userId, String dialogueName) throws SQLException
    {
        String sql = "SELECT id, name, status, created_at FROM dialogues WHERE user_id = ? AND name = ?";

        try (Connection conn = getConnection(); PreparedStatement pstmt = conn.prepareStatement(sql))
        {
            pstmt.setInt(1, userId);
            pstmt.setString(2, dialogueName);
            try (ResultSet rs = pstmt.executeQuery())
            {
                if (rs.next())
                {
                    DialogueDTO d = new DialogueDTO();
                    d.id = rs.getInt("id");
                    d.name = rs.getString("name");
                    d.status = rs.getString("status");
                    d.createdAt = rs.getTimestamp("created_at").toLocalDateTime();
                    d.messages = getMessagesFromDB(d.id);
                    return d;
                }
            }
        }
        return null;
    }

    /**
     * Obtiene mensajes de un diálogo
     */
    private List<MessageDTO> getMessagesFromDB(int dialogueId) throws SQLException
    {
        List<MessageDTO> messages = new ArrayList<>();
        String sql = "SELECT role, content, timestamp FROM messages WHERE dialogue_id = ? ORDER BY timestamp ASC";

        try (Connection conn = getConnection(); PreparedStatement pstmt = conn.prepareStatement(sql))
        {
            pstmt.setInt(1, dialogueId);
            try (ResultSet rs = pstmt.executeQuery())
            {
                while (rs.next())
                {
                    MessageDTO m = new MessageDTO();
                    m.role = rs.getString("role");
                    m.content = rs.getString("content");
                    m.timestamp = rs.getTimestamp("timestamp").toLocalDateTime();
                    messages.add(m);
                }
            }
        }
        return messages;
    }

    /**
     * Agrega mensaje a un diálogo
     */
    private void addMessageToDB(int dialogueId, String role, String content) throws SQLException
    {
        String sql = "INSERT INTO messages (dialogue_id, role, content) VALUES (?, ?, ?)";

        try (Connection conn = getConnection(); PreparedStatement pstmt = conn.prepareStatement(sql))
        {
            pstmt.setInt(1, dialogueId);
            pstmt.setString(2, role);
            pstmt.setString(3, content);
            pstmt.executeUpdate();
        }
    }

    /**
     * Obtiene conexión a BD
     */
    private Connection getConnection() throws SQLException
    {
        String url = System.getenv("DATABASE_URL");
        if (url == null)
            url = "jdbc:mysql://db-mysql:3306/ssdd?useSSL=false&serverTimezone=UTC";

        String user = System.getenv("MYSQL_USER") != null ? System.getenv("MYSQL_USER") : "root";
        String pass = System.getenv("MYSQL_PASSWORD") != null ? System.getenv("MYSQL_PASSWORD") : 
                     (System.getenv("MYSQL_ROOT_PASSWORD") != null ? System.getenv("MYSQL_ROOT_PASSWORD") : "");

        return DriverManager.getConnection(url, user, pass);
    }
}
