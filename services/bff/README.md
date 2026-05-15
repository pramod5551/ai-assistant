# ai-search-assistant-bff

Standalone **Spring Boot** service (separate Maven project and Docker image from `services/ai-core`). Deploy as its **own Kubernetes Deployment**; it calls the AI core over HTTP using `BFF_AI_CORE_BASE_URL`.

## Build & run

```bash
cd "$(dirname "$0")"
mvn -q package
java -jar target/ai-search-assistant-bff-*-SNAPSHOT.jar
```

Local dev with AI core on 8081:

```bash
mvn spring-boot:run -Dspring-boot.run.profiles=dev \
  -Dspring-boot.run.arguments=--bff.ai-core.base-url=http://localhost:8081,--bff.ai-core.internal-token=dev-internal-token
```

## Docker

From repo root:

```bash
docker build -t ai-search-assistant-bff:latest -f services/bff/Dockerfile services/bff
```

## Kubernetes

See [`deploy/kubernetes/`](../deploy/kubernetes/) for example **Service**, **Deployment**, and **Secret** manifests. Required env at minimum: **`BFF_AI_CORE_BASE_URL`**, **`BFF_AI_CORE_INTERNAL_TOKEN`** (must match AI core **`INTERNAL_TOKEN`**), and production **`JWT_ISSUER_URI`** / OAuth settings (replace `dev` profile).
