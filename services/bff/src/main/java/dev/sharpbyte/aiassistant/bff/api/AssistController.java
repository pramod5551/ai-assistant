package dev.sharpbyte.aiassistant.bff.api;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import java.util.Optional;
import java.util.UUID;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import dev.sharpbyte.aiassistant.bff.client.AiCoreGateway;
import dev.sharpbyte.aiassistant.bff.client.dto.AiChatRequest;
import dev.sharpbyte.aiassistant.bff.client.dto.AiChatResponse;
import dev.sharpbyte.aiassistant.bff.security.UserContextFactory;

/**
 * Public HTTP API for assist: validates body, derives correlation id, builds user context, delegates to AI core.
 */
@RestController
@RequestMapping("/api/v1/assist")
public class AssistController {

    private final AiCoreGateway aiCoreGateway;
    private final UserContextFactory userContextFactory;

    public AssistController(AiCoreGateway aiCoreGateway, UserContextFactory userContextFactory) {
        this.aiCoreGateway = aiCoreGateway;
        this.userContextFactory = userContextFactory;
    }

    /**
     * Proxies a chat message to the internal AI core, echoing {@code X-Correlation-Id} on the response.
     *
     * @param body validated chat payload
     * @param authentication Spring Security principal (JWT in non-dev profiles)
     * @param request unused today; reserved for future client metadata
     * @param correlationHeader optional id from caller; a random UUID is generated if absent
     * @param authorization optional bearer token, forwarded when configured
     * @param traceparent optional W3C trace context for distributed tracing
     * @return AI core response with correlation header set
     */
    @PostMapping("/chat")
    ResponseEntity<AiChatResponse> chat(
            @Valid @RequestBody AiChatRequest body,
            Authentication authentication,
            HttpServletRequest request,
            @RequestHeader(value = "X-Correlation-Id", required = false) String correlationHeader,
            @RequestHeader(value = "Authorization", required = false) String authorization,
            @RequestHeader(value = "traceparent", required = false) String traceparent) {
        String correlationId =
                correlationHeader != null && !correlationHeader.isBlank()
                        ? correlationHeader
                        : UUID.randomUUID().toString();
        var user = userContextFactory.fromAuthentication(authentication);
        Optional<String> authOpt = Optional.ofNullable(authorization);
        Optional<String> traceOpt = Optional.ofNullable(traceparent);
        AiChatResponse response = aiCoreGateway.chat(body, user, correlationId, authOpt, traceOpt);
        return ResponseEntity.ok()
                .header("X-Correlation-Id", correlationId)
                .body(response);
    }
}
