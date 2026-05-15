package dev.sharpbyte.aisearchassistant.bff.security;

import java.util.List;

/**
 * Minimal cross-service identity: OIDC {@code sub}, normalized roles, and allowed library ids for retrieval RBAC.
 *
 * @param subject JWT subject (or synthetic dev user)
 * @param roles authority strings with optional {@code ROLE_} prefix stripped upstream
 * @param libraryAccess document library ids the user may query
 */
public record UserContext(String subject, List<String> roles, List<String> libraryAccess) {}
