package dev.sharpbyte.aisearchassistant.bff.security;

import java.util.Collections;
import java.util.List;
import java.util.stream.Collectors;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.stereotype.Component;

/**
 * Extracts a portable user context from the JWT for downstream AI core RBAC.
 */
@Component
public class UserContextFactory {

    /**
     * @param authentication must be {@link JwtAuthenticationToken}
     * @return immutable context including {@code library_access} or legacy {@code libraries} claim
     * @throws IllegalStateException if authentication is not JWT-based
     */
    public UserContext fromAuthentication(Authentication authentication) {
        if (!(authentication instanceof JwtAuthenticationToken jwtAuth)) {
            throw new IllegalStateException("Expected JWT authentication");
        }
        Jwt jwt = jwtAuth.getToken();
        String subject = jwt.getSubject() != null ? jwt.getSubject() : "unknown";
        List<String> roles = jwtAuth.getAuthorities().stream()
                .map(GrantedAuthority::getAuthority)
                .map(a -> a.startsWith("ROLE_") ? a.substring("ROLE_".length()) : a)
                .collect(Collectors.toList());

        List<String> libraryAccess = parseStringListClaim(jwt, "library_access");
        if (libraryAccess.isEmpty()) {
            libraryAccess = parseStringListClaim(jwt, "libraries");
        }
        return new UserContext(subject, List.copyOf(roles), List.copyOf(libraryAccess));
    }

    private static List<String> parseStringListClaim(Jwt jwt, String claim) {
        Object v = jwt.getClaim(claim);
        if (v == null) {
            return Collections.emptyList();
        }
        if (v instanceof List<?> list) {
            return list.stream().map(Object::toString).toList();
        }
        if (v instanceof String s) {
            return List.of(s.split(","));
        }
        return Collections.emptyList();
    }
}
