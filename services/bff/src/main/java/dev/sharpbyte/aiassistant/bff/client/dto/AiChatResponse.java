package dev.sharpbyte.aiassistant.bff.client.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;
import java.util.Map;

/**
 * BFF response DTO aligned with the AI core JSON schema (citations + optional LangGraph path).
 *
 * @param correlationId request id for support correlation
 * @param answerText model or clarification text
 * @param structured optional JSON object when structured output requested
 * @param citations retrieval provenance
 * @param graphPath pipeline path for observability (e.g. {@code rewrite→retrieve→generate})
 */
public record AiChatResponse(
        @JsonProperty("correlation_id") String correlationId,
        @JsonProperty("answer_text") String answerText,
        Map<String, Object> structured,
        List<Citation> citations,
        @JsonProperty("graph_path") String graphPath) {

    /** Single source reference returned to the client UI. */
    public record Citation(
            @JsonProperty("document_id") String documentId,
            String title,
            @JsonProperty("library_id") String libraryId,
            String snippet) {}
}
