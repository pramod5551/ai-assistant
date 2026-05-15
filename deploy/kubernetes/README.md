# Kubernetes (separate workloads)

The repo is structured so **BFF** (`services/bff/`) and **AI core** (`services/ai-core/`) are **independent images** and **independent Deployments**. Compose is for local dev only.

## Build images

Use your registry instead of `example/`:

```bash
docker build -t example/ai-assistant-bff:latest services/bff
docker build -t example/ai-assistant-core:latest services/ai-core
docker push example/ai-assistant-bff:latest
docker push example/ai-assistant-core:latest
```

Edit each manifest’s `image:` before `kubectl apply`.

Before applying workloads, create the shared internal token (edit the value first):

```bash
kubectl apply -f ai-assistant-internal-secret.example.yaml
```

Then:

```bash
kubectl apply -f ai-core-deployment.yaml
kubectl apply -f bff-deployment.yaml
```

Order: deploy **AI core** (and its backing **Postgres**, **Qdrant**, etc.) first, then the **BFF** so `BFF_AI_CORE_BASE_URL` resolves to the core **Service** (e.g. `http://ai-assistant-core:8081` in the same namespace).

## Secrets

- **`internal-token`**: must match **`INTERNAL_TOKEN`** on the AI core and **`BFF_AI_CORE_INTERNAL_TOKEN`** on the BFF. The example manifests use a `Secret` named `ai-assistant-internal`; replace with ExternalSecrets / your CM in production.

## Production notes

- Run **Postgres** and **Qdrant** as managed services or separate charts; point `DATABASE_URL`, `QDRANT_URL`, and the BFF’s `BFF_AI_CORE_BASE_URL` at those endpoints.
- Configure the BFF **OIDC issuer** via `JWT_ISSUER_URI` / Spring properties instead of the `dev` profile.
- Use **HorizontalPodAutoscaler** and **PodDisruptionBudgets** per service as needed.
