package es.um.sisdist.backend.Service;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.ExpiredJwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import jakarta.annotation.Priority;
import jakarta.ws.rs.Priorities;
import jakarta.ws.rs.container.ContainerRequestContext;
import jakarta.ws.rs.container.ContainerRequestFilter;
import jakarta.ws.rs.core.HttpHeaders;
import jakarta.ws.rs.core.Response;
import jakarta.ws.rs.ext.Provider;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Set;

@Provider
@Priority(Priorities.AUTHENTICATION)
public class JwtAuthFilter implements ContainerRequestFilter
{
    private static final Set<String> PUBLIC_PATHS = Set.of(
            "/Service/checkLogin",
            "/Service/ping",
            "/Service/metrics"
    );

    @Override
    public void filter(ContainerRequestContext ctx)
    {
        String path = ctx.getUriInfo().getAbsolutePath().getPath();
        for (String pub : PUBLIC_PATHS)
        {
            if (path.startsWith(pub))
                return;
        }

        // El registro de usuario es público (POST /u exacto)
        if ("POST".equals(ctx.getMethod()) && "/Service/u".equals(path))
            return;

        String authHeader = ctx.getHeaderString(HttpHeaders.AUTHORIZATION);
        if (authHeader == null || !authHeader.toLowerCase().startsWith("bearer "))
        {
            abort(ctx, "missing or malformed Authorization header");
            return;
        }

        String token = authHeader.substring(7).trim();
        String secret = System.getenv("FLASK_SECRET");
        if (secret == null || secret.isBlank())
        {
            abort(ctx, "server misconfiguration: FLASK_SECRET not set");
            return;
        }

        try
        {
            SecretKey key = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
            Claims claims = Jwts.parser()
                    .verifyWith(key)
                    .build()
                    .parseSignedClaims(token)
                    .getPayload();

            ctx.setProperty("jwt.sub", claims.getSubject());
        }
        catch (ExpiredJwtException e)
        {
            abort(ctx, "token expired");
        }
        catch (Exception e)
        {
            abort(ctx, "invalid token");
        }
    }

    private void abort(ContainerRequestContext ctx, String reason)
    {
        ctx.abortWith(Response.status(Response.Status.UNAUTHORIZED)
                .entity("{\"error\":\"" + reason + "\"}")
                .type("application/json")
                .build());
    }
}
