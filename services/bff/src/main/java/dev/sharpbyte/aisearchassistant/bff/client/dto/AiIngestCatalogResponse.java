package dev.sharpbyte.aisearchassistant.bff.client.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

public record AiIngestCatalogResponse(
        List<String> libraries,
        String collection,
        @JsonProperty("vector_backend") String vectorBackend,
        @JsonProperty("supported_extensions") List<String> supportedExtensions,
        @JsonProperty("supported_formats") List<String> supportedFormats,
        @JsonProperty("accept_file_types") String acceptFileTypes,
        @JsonProperty("max_upload_bytes") Integer maxUploadBytes) {}
