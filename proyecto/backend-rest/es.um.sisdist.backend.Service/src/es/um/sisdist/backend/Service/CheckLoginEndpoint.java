package es.um.sisdist.backend.Service;

import com.fasterxml.jackson.databind.ObjectMapper;
import es.um.sisdist.backend.Service.impl.AppLogicImpl;
import es.um.sisdist.models.UserDTO;
import es.um.sisdist.models.UserDTOUtils;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import jakarta.ws.rs.*;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import jakarta.ws.rs.core.Response.Status;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;
import java.util.Map;

@Path("/checkLogin")
public class CheckLoginEndpoint
{
    private AppLogicImpl impl = AppLogicImpl.getInstance();
    private ObjectMapper mapper = new ObjectMapper();

    @POST
    @Consumes(MediaType.APPLICATION_JSON)
    @Produces(MediaType.APPLICATION_JSON)
    public Response checkUser(UserDTO uo)
    {
        var u = impl.checkLogin(uo.getEmail(), uo.getPassword());
        if (u.isEmpty())
            return Response.status(Status.FORBIDDEN).build();

        String secret = System.getenv("FLASK_SECRET");
        if (secret == null || secret.isBlank())
            return Response.status(500).entity("{\"error\":\"FLASK_SECRET not configured\"}").build();

        SecretKey key = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
        String jwtToken = Jwts.builder()
                .subject(u.get().getId())
                .issuedAt(new Date())
                .expiration(new Date(System.currentTimeMillis() + 30L * 60 * 1000))
                .signWith(key)
                .compact();

        try
        {
            UserDTO userDto = UserDTOUtils.toDTO(u.get());
            String body = mapper.writeValueAsString(Map.of("user", userDto, "jwtToken", jwtToken));
            return Response.ok(body).type(MediaType.APPLICATION_JSON).build();
        }
        catch (Exception e)
        {
            return Response.status(500).entity("{\"error\":\"" + e.getMessage() + "\"}").build();
        }
    }
}
