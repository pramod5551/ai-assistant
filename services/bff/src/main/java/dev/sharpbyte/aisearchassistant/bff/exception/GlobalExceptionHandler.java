package dev.sharpbyte.aisearchassistant.bff.exception;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.security.authorization.AuthorizationDeniedException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestClientResponseException;

import dev.sharpbyte.aisearchassistant.bff.client.AiCoreGateway.AiCoreException;

/**
 * Maps common failures to RFC 7807 {@link ProblemDetail} responses for consistent API errors.
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    @ExceptionHandler(AiCoreException.class)
    ResponseEntity<ProblemDetail> aiCore(AiCoreException ex) {
        log.warn("AI core returned error status={}", ex.status());
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(
                HttpStatus.valueOf(ex.status()), "Assistant backend error");
        pd.setProperty("body", ex.body());
        return ResponseEntity.status(ex.status()).body(pd);
    }

    /**
     * Connection refused, timeouts, or response bodies that cannot be mapped to DTOs.
     * Common when ai-core is still starting or the ingest API image was not rebuilt.
     */
    @ExceptionHandler(RestClientException.class)
    ResponseEntity<ProblemDetail> restClient(RestClientException ex) {
        if (ex instanceof RestClientResponseException responseEx) {
            log.warn("AI core HTTP error status={}", responseEx.getStatusCode().value());
            ProblemDetail pd = ProblemDetail.forStatusAndDetail(
                    responseEx.getStatusCode(), "The assistant could not complete your request.");
            pd.setProperty("body", responseEx.getResponseBodyAsString());
            return ResponseEntity.status(responseEx.getStatusCode()).body(pd);
        }

        String technical = ex.getMessage() != null ? ex.getMessage() : ex.getClass().getSimpleName();
        log.warn("AI core call failed: {}", technical);

        HttpStatus status = HttpStatus.SERVICE_UNAVAILABLE;
        String userMessage = "The assistant is temporarily unavailable. Please try again in a moment.";

        if (isTimeout(ex, technical)) {
            status = HttpStatus.GATEWAY_TIMEOUT;
            userMessage =
                    "The assistant took too long to respond. On a slow machine the first answer can take a few minutes—try again with a shorter question.";
        } else if (isConnectionFailure(ex, technical)) {
            userMessage =
                    "The assistant service is not reachable. Make sure all services are running (ai-core on port 8081).";
        }

        ProblemDetail pd = ProblemDetail.forStatusAndDetail(status, userMessage);
        pd.setProperty("cause", technical);
        return ResponseEntity.status(status).body(pd);
    }

    private static boolean isTimeout(RestClientException ex, String message) {
        if (ex instanceof ResourceAccessException && message.toLowerCase().contains("timed out")) {
            return true;
        }
        String lower = message.toLowerCase();
        return lower.contains("timed out") || lower.contains("timeout");
    }

    private static boolean isConnectionFailure(RestClientException ex, String message) {
        String lower = message.toLowerCase();
        return lower.contains("connection refused")
                || lower.contains("connection reset")
                || lower.contains("unknown host")
                || lower.contains("connect");
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    ResponseEntity<ProblemDetail> validation(MethodArgumentNotValidException ex) {
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, "Invalid request");
        pd.setProperty("errors", ex.getBindingResult().getAllErrors());
        return ResponseEntity.badRequest().body(pd);
    }

    @ExceptionHandler(AuthorizationDeniedException.class)
    ResponseEntity<ProblemDetail> forbidden(AuthorizationDeniedException ex) {
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(HttpStatus.FORBIDDEN, "Forbidden");
        return ResponseEntity.status(HttpStatus.FORBIDDEN).body(pd);
    }

    @ExceptionHandler(IllegalStateException.class)
    ResponseEntity<ProblemDetail> illegalState(IllegalStateException ex) {
        log.error("Unexpected state", ex);
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(HttpStatus.INTERNAL_SERVER_ERROR, ex.getMessage());
        return ResponseEntity.internalServerError().body(pd);
    }
}
