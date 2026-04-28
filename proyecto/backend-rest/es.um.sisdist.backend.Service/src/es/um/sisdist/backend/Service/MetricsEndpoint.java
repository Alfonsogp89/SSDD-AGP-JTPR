package es.um.sisdist.backend.Service;

import jakarta.ws.rs.GET;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;

@Path("/metrics")
public class MetricsEndpoint {

    @GET
    @Produces(MediaType.TEXT_PLAIN)
    public Response getMetrics() {
        String response = MetricsManager.getInstance().getRegistry().scrape();
        return Response.ok(response).build();
    }
}
