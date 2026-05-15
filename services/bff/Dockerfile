# ---------- build ----------
FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /src

COPY pom.xml .
COPY src ./src

RUN mvn -q -ntp package -DskipTests \
    && JAR="$(find target -maxdepth 1 -name '*.jar' | head -n1)" \
    && test -n "$JAR" \
    && cp "$JAR" /src/app.jar

# ---------- runtime (Distroless: JRE + CA certs only, no shell/package manager) ----------
FROM gcr.io/distroless/java21-debian12:nonroot
WORKDIR /app

COPY --from=build /src/app.jar /app/app.jar

EXPOSE 8080
USER nonroot
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
