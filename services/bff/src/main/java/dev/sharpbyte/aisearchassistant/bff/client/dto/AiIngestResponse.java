package dev.sharpbyte.aisearchassistant.bff.client.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

public record AiIngestResponse(
        String collection,
        @JsonProperty("chunks_total") int chunksTotal,
        @JsonProperty("points_upserted") int pointsUpserted,
        List<DocumentSummary> documents,
        @JsonProperty("dry_run") boolean dryRun,
        @JsonProperty("recreated_collection") boolean recreatedCollection) {

    public record DocumentSummary(
            @JsonProperty("document_id") String documentId,
            String title,
            @JsonProperty("library_id") String libraryId,
            @JsonProperty("chunk_count") int chunkCount,
            String source) {}
}
