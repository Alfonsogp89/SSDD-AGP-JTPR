package es.um.sisdist.models;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.LocalDateTime;
import java.util.List;

public class DialogueDTO
{
    @JsonProperty("id")
    public Integer id;

    @JsonProperty("name")
    public String name;

    @JsonProperty("status")
    public String status;

    @JsonProperty("created_at")
    public LocalDateTime createdAt;

    @JsonProperty("messages")
    public List<MessageDTO> messages;

    public DialogueDTO()
    {
    }

    public DialogueDTO(Integer id, String name, String status, LocalDateTime createdAt, List<MessageDTO> messages)
    {
        this.id = id;
        this.name = name;
        this.status = status;
        this.createdAt = createdAt;
        this.messages = messages;
    }
}
