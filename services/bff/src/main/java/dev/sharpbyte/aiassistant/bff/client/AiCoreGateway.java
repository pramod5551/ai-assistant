package dev.sharpbyte.aiassistant.bff.client;

import java.util.Optional;
import org.springframework.http.HttpHeaders;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientResponseException;

import dev.sharpbyte.aiassistant.bff.config.AiCoreProperties;
import dev.sharpbyte.aiassistant.bff.client.dto.AiChatRequest;
import dev.sharpbyte.aiassistant.bff.client.dto.AiChatResponse;
import dev.sharpbyte.aiassistant.bff.security.UserContext;

/**
 * Typed HTTP client for the AI core internal assist endpoint: maps {@link UserContext} to trust headers.
 */
@Service
public class AiCoreGateway {

    private static final String HDR_CORRELATION = "X-Correlation-Id";
    private static final String HDR_INTERNAL = "X-Internal-Token";
    private static final String HDR_USER_SUB = "X-User-Sub";
    private static final String HDR_USER_ROLES = "X-User-Roles";
    private static final String HDR_LIBRARY_ACCESS = "X-User-Library-Access";

    private final RestClient aiCoreRestClient;
    private final AiCoreProperties aiCoreProperties;

    public AiCoreGateway(RestClient aiCoreRestClient, AiCoreProperties aiCoreProperties) {
        this.aiCoreRestClient = aiCoreRestClient;
        this.aiCoreProperties = aiCoreProperties;
    }

    /**
     * POST {@code /internal/v1/assist/chat} with internal token, user headers, and optional trace propagation.
     *
     * @param request body forwarded as JSON to the core
     * @param user subject, roles, and library access derived from JWT
     * @param correlationId end-to-end id for logs and audit
     * @param authorization original Authorization header if present
     * @param traceparent W3C {@code traceparent} when present
     * @return deserialized core response
     * @throws AiCoreException when the core returns a non-2xx status
     */
    public AiChatResponse chat(
            AiChatRequest request,
            UserContext user,
            String correlationId,
            Optional<String> authorization,
            Optional<String> traceparent) {
        try {
            var req = aiCoreRestClient
                    .post()
                    .uri("/internal/v1/assist/chat")
                    .header(HDR_CORRELATION, correlationId)
                    .header(HDR_INTERNAL, aiCoreProperties.getInternalToken())
                    .header(HDR_USER_SUB, user.subject())
                    .header(HDR_USER_ROLES, String.join(",", user.roles()))
                    .header(HDR_LIBRARY_ACCESS, String.join(",", user.libraryAccess()));

            traceparent.ifPresent(tp -> req.header("traceparent", tp));

            if (aiCoreProperties.isForwardAuthorization()) {
                authorization.ifPresent(a -> req.header(HttpHeaders.AUTHORIZATION, a));
            }

            return req.body(request).retrieve().body(AiChatResponse.class);
        } catch (RestClientResponseException e) {
            throw new AiCoreException(e.getStatusCode().value(), e.getResponseBodyAsString(), e);
        }
    }

    /** Wraps non-success HTTP responses from the AI core while preserving status and raw body. */
    public static final class AiCoreException extends RuntimeException {
        private final int status;
        private final String body;

        public AiCoreException(int status, String body, Throwable cause) {
            super("AI core error: HTTP " + status, cause);
            this.status = status;
            this.body = body;
        }

        public int status() {
            return status;
        }

        public String body() {
            return body;
        }
    }
}
