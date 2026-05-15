package dev.sharpbyte.aisearchassistant.bff.config;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.time.Instant;
import java.util.Collection;
import java.util.List;
import java.util.stream.Stream;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;
import org.springframework.core.annotation.Order;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContext;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * Local development without an IdP: injects a synthetic JWT-shaped principal compatible with
 * {@link dev.sharpbyte.aisearchassistant.bff.security.UserContextFactory}. Do not enable outside dev.
 */
@Configuration
@Profile("dev")
public class DevSecurityConfig {

    @Bean
    @Order(0)
    SecurityFilterChain devChain(org.springframework.security.config.annotation.web.builders.HttpSecurity http)
            throws Exception {
        http.securityMatcher("/**")
                .csrf(csrf -> csrf.disable())
                .authorizeHttpRequests(auth -> auth.anyRequest().permitAll())
                .addFilterBefore(new SyntheticJwtFilter(), org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter.class);
        return http.build();
    }

    /**
     * Injects a synthetic JWT and authorities so {@link dev.sharpbyte.aisearchassistant.bff.security.UserContextFactory}
     * works without a real IdP. Clears {@link SecurityContextHolder} after each request.
     */
    static final class SyntheticJwtFilter extends OncePerRequestFilter {

        @Override
        protected void doFilterInternal(
                HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
                throws ServletException, IOException {
            SecurityContext context = SecurityContextHolder.createEmptyContext();
            Jwt jwt = Jwt.withTokenValue("dev-token")
                    .headers(h -> h.put("alg", "none"))
                    .claims(c -> {
                        c.put("sub", "dev-user");
                        c.put(
                                "library_access",
                                List.of("POLICIES", "PROCEDURES", "EXTERNAL_REF"));
                    })
                    .issuedAt(Instant.now())
                    .expiresAt(Instant.now().plusSeconds(3600))
                    .build();
            Collection<GrantedAuthority> authorities =
                    Stream.of("OPERATOR", "ROLE_OPERATOR")
                            .map(SimpleGrantedAuthority::new)
                            .map(a -> (GrantedAuthority) a)
                            .toList();
            JwtAuthenticationToken token = new JwtAuthenticationToken(jwt, authorities);
            token.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));
            context.setAuthentication(token);
            SecurityContextHolder.setContext(context);
            try {
                filterChain.doFilter(request, response);
            } finally {
                SecurityContextHolder.clearContext();
            }
        }
    }
}
