package dev.sharpbyte.aisearchassistant.bff.client.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import java.util.List;

public record AiIngestRequest(
        @Valid List<UploadDocument> uploads,
        @Valid IngestOptions options) {

    public record UploadDocument(
            @NotBlank @Size(max = 128) @JsonProperty("document_id") String documentId,
            @NotBlank @Size(max = 512) String title,
            @NotBlank @Size(max = 64) @JsonProperty("library_id") String libraryId,
            @Size(max = 255) @JsonProperty("file_name") String fileName,
            @Size(max = 2_000_000) String content,
            @Size(max = 14_000_000) @JsonProperty("content_base64") String contentBase64) {}

    public record IngestOptions(
            @JsonProperty("batch_size") @Min(1) @Max(256) Integer batchSize,
            @JsonProperty("max_chars") @Min(200) @Max(8000) Integer maxChars,
            @Min(0) @Max(2000) Integer overlap,
            @JsonProperty("recreate_collection") Boolean recreateCollection,
            @JsonProperty("dry_run") Boolean dryRun) {}
}
