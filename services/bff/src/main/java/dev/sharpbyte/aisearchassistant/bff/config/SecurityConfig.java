package dev.sharpbyte.aisearchassistant.bff.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;

/**
 * Production security: stateless JWT resource server; health endpoints stay public.
 */
@Configuration
@EnableWebSecurity
@Profile("!dev")
public class SecurityConfig {

    /**
     * @param http Spring Security DSL
     * @return filter chain requiring authentication except actuator health
     */
    @Bean
    SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http.csrf(csrf -> csrf.disable())
                .sessionManagement(sm -> sm.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(
                        auth -> auth.requestMatchers("/actuator/health", "/actuator/health/**")
                                .permitAll()
                                .anyRequest()
                                .authenticated())
                .oauth2ResourceServer(oauth2 -> oauth2.jwt(jwt -> {}));
        return http.build();
    }
}
