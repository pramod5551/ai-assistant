package dev.sharpbyte.aiassistant.bff;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;

import dev.sharpbyte.aiassistant.bff.config.AiCoreProperties;

/**
 * Spring Boot entry point for the AI assistant BFF: authenticates callers, maps JWT claims to
 * {@link dev.sharpbyte.aiassistant.bff.security.UserContext}, and proxies chat requests to the Python AI core.
 */
@SpringBootApplication
@ConfigurationPropertiesScan(basePackageClasses = AiCoreProperties.class)
public class AiAssistantBffApplication {

    public static void main(String[] args) {
        SpringApplication.run(AiAssistantBffApplication.class, args);
    }
}
