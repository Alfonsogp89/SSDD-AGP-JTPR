package es.um.sisdist.backend.Service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import es.um.sisdist.backend.Service.impl.AppLogicImpl;
import es.um.sisdist.backend.dao.models.utils.UserUtils;
import es.um.sisdist.models.UserDTOUtils;
import jakarta.ws.rs.*;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.util.Random;

@Path("/u")
public class UsersEndpoint
{
    private AppLogicImpl impl = AppLogicImpl.getInstance();
    private ObjectMapper mapper = new ObjectMapper();

    @GET
    @Path("/{username}")
    @Produces(MediaType.APPLICATION_JSON)
    public Response getUserInfo(@PathParam("username") String username)
    {
        return impl.getUserByEmail(username)
                .map(u -> Response.ok(UserDTOUtils.toDTO(u)).build())
                .orElse(Response.status(404).build());
    }

    @POST
    @Consumes(MediaType.APPLICATION_JSON)
    @Produces(MediaType.APPLICATION_JSON)
    public Response registerUser(String body)
    {
        try
        {
            JsonNode json = mapper.readTree(body);
            String email = json.get("email").asText();
            String password = json.get("password").asText();
            String name = json.has("name") ? json.get("name").asText() : email;

            // ID numérico como string para compatibilidad con DialogueEndpoint (int path param)
            String userId = String.valueOf(100000 + new Random().nextInt(900000));
            String hashedPass = UserUtils.md5pass(password);

            String sql = "INSERT INTO users (id, email, password_hash, name, token, visits) VALUES (?, ?, ?, ?, '', 0)";
            try (Connection conn = getConnection(); PreparedStatement pstmt = conn.prepareStatement(sql))
            {
                pstmt.setString(1, userId);
                pstmt.setString(2, email);
                pstmt.setString(3, hashedPass);
                pstmt.setString(4, name);
                pstmt.executeUpdate();
            }

            String resp = "{\"id\":\"" + userId + "\",\"email\":\"" + email + "\",\"name\":\"" + name + "\"}";
            return Response.status(201).entity(resp).type(MediaType.APPLICATION_JSON).build();
        }
        catch (SQLException e)
        {
            if (e.getMessage() != null && e.getMessage().contains("Duplicate entry"))
                return Response.status(409).entity("{\"error\":\"Email ya registrado\"}").build();
            return Response.status(500).entity("{\"error\":\"" + e.getMessage() + "\"}").build();
        }
        catch (Exception e)
        {
            return Response.status(400).entity("{\"error\":\"" + e.getMessage() + "\"}").build();
        }
    }

    private Connection getConnection() throws SQLException
    {
        return DBConnectionPool.getConnection();
    }
}
