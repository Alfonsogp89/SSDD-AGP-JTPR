package es.um.sisdist.models;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.LocalDateTime;

public class MessageDTO
{
    @JsonProperty("role")
    public String role;

    @JsonProperty("content")
    public String content;

    @JsonProperty("timestamp")
    public LocalDateTime timestamp;

    public MessageDTO()
    {
    }

    public MessageDTO(String role, String content, LocalDateTime timestamp)
    {
        this.role = role;
        this.content = content;
        this.timestamp = timestamp;
    }
}
