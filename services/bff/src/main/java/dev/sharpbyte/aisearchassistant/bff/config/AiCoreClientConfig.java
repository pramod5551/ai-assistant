package dev.sharpbyte.aisearchassistant.bff.config;

import java.net.http.HttpClient;
import java.time.Duration;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

/**
 * Configures the {@link RestClient} used for AI core calls, forcing HTTP/1.1 to avoid Uvicorn/h2c issues.
 */
@Configuration
public class AiCoreClientConfig {

    /**
     * @param baseUrl AI core root (e.g. {@code http://localhost:8000})
     * @param timeoutSeconds read timeout for long LLM responses
     */
    @Bean
    RestClient aiCoreRestClient(
            @Value("${bff.ai-core.base-url}") String baseUrl,
            @Value("${bff.ai-core.timeout-seconds:60}") int timeoutSeconds) {
        /*
         Uvicorn speaks HTTP/1.1 by default. JDK HttpClient may negotiate HTTP/2 (h2c) for http://
         targets, which produces a request line (e.g. PRI) that httptools rejects with
         "Invalid HTTP request received." Force HTTP/1.1 for the AI core hop.
         */
        HttpClient jdk =
                HttpClient.newBuilder()
                        .version(HttpClient.Version.HTTP_1_1)
                        .connectTimeout(Duration.ofSeconds(15))
                        .build();
        var factory = new JdkClientHttpRequestFactory(jdk);
        factory.setReadTimeout(Duration.ofSeconds(timeoutSeconds));
        return RestClient.builder()
                .baseUrl(baseUrl)
                .requestFactory(factory)
                .build();
    }
}
