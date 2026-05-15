package dev.sharpbyte.aiassistant.bff.client.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * BFF request DTO mirrored to the AI core chat API.
 *
 * @param message user text
 * @param sessionId optional client session id
 * @param structuredOutput when true, core may return a structured object alongside prose
 */
public record AiChatRequest(
        @NotBlank @Size(max = 16_000) String message,
        @JsonProperty("session_id") @Size(max = 128) String sessionId,
        @JsonProperty("structured_output") boolean structuredOutput) {}
