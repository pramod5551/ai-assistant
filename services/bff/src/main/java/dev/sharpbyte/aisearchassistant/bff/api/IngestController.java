package dev.sharpbyte.aisearchassistant.bff.api;

import jakarta.validation.Valid;
import java.util.UUID;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import dev.sharpbyte.aisearchassistant.bff.client.AiCoreGateway;
import dev.sharpbyte.aisearchassistant.bff.client.dto.AiIngestCatalogResponse;
import dev.sharpbyte.aisearchassistant.bff.client.dto.AiIngestRequest;
import dev.sharpbyte.aisearchassistant.bff.client.dto.AiIngestResponse;
import dev.sharpbyte.aisearchassistant.bff.security.UserContextFactory;

/** Public ingest API: document catalog and one-click ingestion into the vector store. */
@RestController
@RequestMapping("/api/v1/ingest")
public class IngestController {

    private final AiCoreGateway aiCoreGateway;
    private final UserContextFactory userContextFactory;

    public IngestController(AiCoreGateway aiCoreGateway, UserContextFactory userContextFactory) {
        this.aiCoreGateway = aiCoreGateway;
        this.userContextFactory = userContextFactory;
    }

    @GetMapping("/catalog")
    ResponseEntity<AiIngestCatalogResponse> catalog(Authentication authentication) {
        var user = userContextFactory.fromAuthentication(authentication);
        return ResponseEntity.ok(aiCoreGateway.ingestCatalog(user));
    }

    @PostMapping("/run")
    ResponseEntity<AiIngestResponse> run(
            @Valid @RequestBody AiIngestRequest body,
            Authentication authentication,
            @RequestHeader(value = "X-Correlation-Id", required = false) String correlationHeader) {
        String correlationId =
                correlationHeader != null && !correlationHeader.isBlank()
                        ? correlationHeader
                        : UUID.randomUUID().toString();
        var user = userContextFactory.fromAuthentication(authentication);
        AiIngestResponse response = aiCoreGateway.ingestRun(body, user, correlationId);
        return ResponseEntity.ok()
                .header("X-Correlation-Id", correlationId)
                .body(response);
    }
}
