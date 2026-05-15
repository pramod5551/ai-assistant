package dev.sharpbyte.aisearchassistant.bff.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * Bindings for {@code bff.ai-core.*} (internal token and whether to forward Authorization to the core).
 */
@ConfigurationProperties(prefix = "bff.ai-core")
public class AiCoreProperties {

    /**
     * Shared secret the BFF sends so the AI core can reject arbitrary Internet callers.
     */
    private String internalToken = "dev-only-change-me";

    /**
     * When true, forwards the original Authorization header to the AI core (dev / same IdP).
     * In production, prefer internal token + structured user headers only.
     */
    private boolean forwardAuthorization = true;

    public String getInternalToken() {
        return internalToken;
    }

    public void setInternalToken(String internalToken) {
        this.internalToken = internalToken;
    }

    public boolean isForwardAuthorization() {
        return forwardAuthorization;
    }

    public void setForwardAuthorization(boolean forwardAuthorization) {
        this.forwardAuthorization = forwardAuthorization;
    }
}
