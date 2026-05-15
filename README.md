# AI Search Assistant

A small search app that answers questions using **your documents** (not made-up facts). You type a question in a chat window; the system finds relevant text, then a language model writes an answer and shows **which documents** it used.

This repo runs everything with **Docker** so you do not need to install Java, Python, or databases by hand for a first try.

---

## What gets started

When you run Docker Compose, these parts work together:

| Part | What it does | URL (on your machine) |
|------|----------------|------------------------|
| **web** | Chat page in the browser | http://localhost:3000 |
| **bff** | Front API (security, forwards requests) | http://localhost:8080 |
| **ai-core** | Search + AI logic | http://localhost:8081 |
| **qdrant** | Stores document search vectors | http://localhost:6333/dashboard |
| **postgres** | Saves chat audit logs | port 5432 (internal) |
| **ollama** | Runs a local **Llama** model for answers | http://localhost:11434 |

There is **no bundled sample corpus**. Upload your own files on the **Ingest** tab (or use the ingest CLI with a manifest) before chatting.

---

## End-to-end workflow (one chat message)

When you send one question from the chat page, the system runs through these steps. Each row is **one step** and names the **component** that does the work.

| Step | What happens | Component |
|:----:|----------------|-----------|
| 1 | You type a question and press **Send** | **Your browser** |
| 2 | The chat page sends the message to the app’s own API route (avoids browser security issues) | **web** — Next.js server route `/api/chat` |
| 3 | That route forwards JSON to the public chat API and adds a correlation id if needed | **bff** — Spring Boot (`AssistController` → `AiCoreGateway`) |
| 4 | The BFF adds **who you are** (dev user in Docker) and calls the internal Python API | **bff** → **ai-core** |
| 5 | Python loads your message, optionally rewrites it, then **searches vectors** for similar document chunks | **ai-core** — LangGraph + `QdrantRetriever` |
| 6 | The vector database returns matching chunks (text + metadata) | **qdrant** |
| 7 | Python sends your question + retrieved text to the **language model** and asks for a grounded answer | **ai-core** → **ollama** (Llama) |
| 8 | The model returns answer text; Python attaches **citations** and may write an **audit** row | **ai-core**; optional row in **postgres** |
| 9 | The response travels back through the BFF and Next.js to your browser | **ai-core** → **bff** → **web** → **browser** |

Same flow as a picture (time flows **down** the diagram; step numbers match the table):

```mermaid
sequenceDiagram
    autonumber
    participant Browser as Your browser
    participant Web as web Next.js
    participant BFF as bff Spring Boot
    participant Core as ai-core FastAPI
    participant Qdrant as Qdrant
    participant Ollama as Ollama Llama
    participant PG as Postgres

    Browser->>Web: POST /api/chat JSON message
    Web->>BFF: POST /api/v1/assist/chat
    BFF->>Core: POST /internal/v1/assist/chat + user headers
    Core->>Qdrant: vector search same network
    Qdrant-->>Core: document chunks
    Core->>Ollama: chat completion with CONTEXT
    Ollama-->>Core: answer text
    Core->>PG: optional audit insert
    Core-->>BFF: answer + citations + graph_path
    BFF-->>Web: JSON response
    Web-->>Browser: show answer and citations
```

**Ingest (separate workflow):** when you upload files in the UI or run `ingest_cli`, only **ai-core**, **Qdrant**, and the **embedder** (FastEmbed inside **ai-core**) are involved — that path loads documents into Qdrant; it does not use the BFF or Ollama.

---

## Before you start

1. **Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)** (Mac, Windows, or Linux).
2. **Open Docker Desktop** and wait until it says it is running.
3. **Clone this repo** and open a terminal in the project folder:

```bash
cd ai-search-assistant
```

You need a working internet connection for the first run (downloads images and the AI model).

---

## Step-by-step setup (beginner)

### Step 1 — Start all services

From the project folder:

```bash
docker compose up --build
```

- The first time can take **several minutes** (downloads images and builds the app).
- Leave this terminal open, or add `-d` to run in the background:

```bash
docker compose up --build -d
```

Wait until you see the **ai-core**, **bff**, and **web** services running without errors.

### Step 2 — Download the Llama model (one time)

The chat brain runs in **Ollama**. You must pull the model once (large download, ~2 GB for the default):

```bash
docker compose exec ollama ollama pull llama3.2:3b
```

**On a slow or small machine**, use a smaller model instead:

```bash
docker compose exec ollama ollama pull llama3.2:1b
```

Then edit [`docker-compose.yml`](docker-compose.yml): under **ai-core** → `environment`, change `LLM_MODEL` to `llama3.2:1b`, and run:

```bash
docker compose up -d --force-recreate ai-core
```

You may see a warning like `onnxruntime cpuid_info warning: Unknown CPU vendor`. That is normal in some VMs and can be ignored.

### Step 3 — Ingest your documents

1. Open **http://localhost:3000** and click the **Ingest** tab.
2. Upload one or more files (drag and drop or file picker).
3. Adjust chunking options if needed, then click **Run ingestion** (use **Preview chunks** for a dry run).

When it finishes, you should see something like: `Ingest complete: N document(s), M chunk(s)`.

**Supported upload formats** (extracted to text on the server, then embedded for search):

| Type | Extensions |
|------|------------|
| Plain text | `.txt`, `.md`, `.csv`, `.json` |
| PDF | `.pdf` |
| Word | `.docx` (native), `.doc` (LibreOffice in Docker image) |
| Other | `.rtf`, `.html`, `.pptx` |

Binary files are sent as base64 from the browser; the default max size is **10 MB** per file (`INGEST_MAX_UPLOAD_BYTES`).

This uses the same pipeline as the CLI (`ingest_cli --manifest …`) but through the browser.

### Step 4 — Open the chat and ask a question

1. Switch to the **Chat** tab.
2. Ask a question about content in the files you ingested, for example:

   > Summarize the main topics in my uploaded documents.

3. Press **Send** and wait (local CPU answers can take **30 seconds or more**).

A good answer will cite **document ids** from your uploads (shown under the reply).

### Step 5 — Stop everything (when you are done)

```bash
docker compose down
```

To also delete stored data (database, vectors, downloaded models):

```bash
docker compose down -v
```

---

## Try without the web UI (optional)

You can call the API directly:

```bash
curl -s -X POST http://localhost:8080/api/v1/assist/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Summarize the main topics in my uploaded documents.","structured_output":false}' | jq .
```

---

## Fix common problems

### “no language model is configured” or “language model could not answer”

**Search worked** (you see sources / context length) but the **chat model** did not produce text.

**If the message says “not configured”** — `OLLAMA_BASE_URL` and `LLM_MODEL` are missing in the environment ai-core sees. For local runs, set them in [`.env`](.env) (see [`.env.example`](.env.example)). For Docker, recreate ai-core after changing [`docker-compose.yml`](docker-compose.yml).

**If it mentions HTTP 404 or “model not found”** — pull the model once:

```bash
docker compose exec ollama ollama pull llama3.2:3b
docker compose up -d --force-recreate ai-core
```

**If it mentions “Cannot reach”** — start Ollama and ai-core:

```bash
docker compose ps
docker compose up -d ollama ai-core
```

**Check what ai-core sees:**

```bash
docker compose exec ai-core python -c "
from ai_search_assistant.config import get_settings
s = get_settings()
print('backend', s.resolved_llm_backend())
print('base_url', s.llm_base_url)
print('model', s.llm_model)
"
```

### “I do not have enough grounded information…” or empty citations

The vector index has **no matching chunks** for your question. Common causes:

- You have not ingested any documents yet (**Step 3**).
- You ingested under a **library** your user cannot access (dev profile allows all libraries).
- The question does not overlap with your document text.

**Fix:** open the **Ingest** tab, upload files, run ingestion, then ask again. To re-index from scratch, enable **Recreate collection** on ingest (destructive).

### Ingest command fails with `unexpected keyword argument 'ge'`

The **ai-core** container is using an **old image**. Rebuild and recreate:

```bash
docker compose build --no-cache ai-core
docker compose up -d --force-recreate ai-core
docker compose exec ai-core grep "_bounded_int" /app/ai_assistant/ingestion/ingest_cli.py
```

If that `grep` shows a match, rebuild **ai-core** and ingest again from the UI (**Step 3**).

### Chat is very slow

Local **Llama on CPU** is slow. Use the smaller `llama3.2:1b` model, or give Ollama a GPU (Linux + NVIDIA — see comments in [`docker-compose.yml`](docker-compose.yml) under **ollama**).

### `password authentication failed for user "aiassistant"` (ai-core won’t start)

Postgres stores credentials in the **`pgdata` volume** on first boot. If you changed `POSTGRES_USER` / `POSTGRES_PASSWORD` in `docker-compose.yml` after the volume was created, the running database still has the **old** user/password.

**Fix (dev — wipes DB audit data):**

```bash
docker compose down -v
docker compose up --build -d
```

Then re-ingest your documents on the **Ingest** tab.

**Without wiping data:** connect with the credentials Postgres was originally created with, or alter the role manually inside the postgres container.

### Port already in use

Another app is using 3000, 8080, or 8081. Stop that app or change the port mapping in `docker-compose.yml`.

---

## Project layout (short)

| Folder | Purpose |
|--------|---------|
| [`services/web/`](services/web/) | Next.js chat UI |
| [`services/bff/`](services/bff/) | Java API gateway |
| [`services/ai-core/`](services/ai-core/) | Python AI + search |
| [`deploy/kubernetes/`](deploy/kubernetes/) | Example Kubernetes manifests (advanced) |

Optional config template: [`.env.example`](.env.example) (copy to `.env` if you customize settings).

---

## How it works (simple)

The numbered table and diagram in **[End-to-end workflow](#end-to-end-workflow-one-chat-message)** describe the same path: browser → **web** → **bff** → **ai-core** → **Qdrant** (search) and **Ollama** (answer) → back out, with **postgres** used only for optional audit logging.

The model is told to **only use the retrieved text**, so wrong or empty search data leads to “not enough information” answers.

---

## Run without Docker (advanced)

You need Java, Maven, Python 3.12+, Postgres, and Qdrant installed yourself. See [`.env.example`](.env.example) for environment variables.

**AI core:**

```bash
cd services/ai-core
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export INTERNAL_TOKEN=dev-internal-token
export DATABASE_URL=postgresql+asyncpg://aiassistant:aiassistant@localhost:5432/aiassistant
export QDRANT_URL=http://localhost:6333
export OLLAMA_BASE_URL=http://localhost:11434
export LLM_MODEL=llama3.2:3b
uvicorn ai_assistant.main:app --reload --port 8081
```

**BFF:**

```bash
cd services/bff
mvn spring-boot:run -Dspring-boot.run.profiles=dev \
  -Dspring-boot.run.arguments=--bff.ai-core.base-url=http://localhost:8081,--bff.ai-core.internal-token=dev-internal-token
```

**Web:**

```bash
cd services/web
npm install
BFF_BASE_URL=http://localhost:8080 npm run dev
```

---

## Configuration reference (AI core)

Most defaults work with Docker Compose. Common variables:

| Variable | Default in Compose | Meaning |
|----------|-------------------|---------|
| `QDRANT_URL` | `http://qdrant:6333` | Vector database |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Local Llama server |
| `LLM_MODEL` | `llama3.2:3b` | Model name in Ollama |
| `VECTOR_SEARCH_LIMIT` | `24` | Max chunks considered per question |
| `SEED_VECTOR_COLLECTION_ON_STARTUP` | `false` | Reserved; no bundled seed data — ingest via UI or CLI |

Full list: [`.env.example`](.env.example) and the table in the original config docs below.

<details>
<summary>Full AI core environment table (click to expand)</summary>

| Variable | Values / default | Notes |
|----------|-------------------|--------|
| **`AUDIT_BACKEND`** | `auto`, `none`, `sql` | `auto` → SQL audit if `DATABASE_URL` set. |
| **`DATABASE_URL`** | async SQLAlchemy URL | e.g. `postgresql+asyncpg://…` |
| **`VECTOR_BACKEND`** | `auto`, `stub`, `qdrant` | `auto` → qdrant if `QDRANT_URL` set. |
| **`QDRANT_URL`** | e.g. `http://qdrant:6333` | Required for vector search. |
| **`VECTOR_COLLECTION`** | `assistant_chunks` | Qdrant collection name. |
| **`EMBEDDING_BACKEND`** | `auto`, `fastembed`, `openai_compatible` | How text is turned into vectors. |
| **`EMBED_MODEL`** | `BAAI/bge-small-en-v1.5` | Embedding model. |
| **`LLM_BACKEND`** | `auto`, `none`, `http` | `auto` → use LLM when URL + model are set. |
| **`LLM_BASE_URL`** | — | OpenAI-compatible API root (often ends in `/v1`). |
| **`OLLAMA_BASE_URL`** | — | If set, app uses `{OLLAMA}/v1` when `LLM_BASE_URL` is empty. |
| **`LLM_REQUEST_TIMEOUT_SECONDS`** | `300` in Compose | Increase if CPU generation times out. |

**Ingest CLI** (batch from a `manifest.json` on disk — advanced):

```bash
docker compose exec ai-core python -m ai_assistant.ingestion.ingest_cli \
  --manifest /path/to/manifest.json --dry-run
docker compose exec ai-core python -m ai_assistant.ingestion.ingest_cli \
  --manifest /path/to/manifest.json --recreate-collection --yes
```

For most users, the **Ingest** tab in the web UI is simpler.

</details>

---

## Kubernetes

Example manifests: [`deploy/kubernetes/`](deploy/kubernetes/). See [`deploy/kubernetes/README.md`](deploy/kubernetes/README.md).

---

## JWT claims (production)

When not using the `dev` profile, users need a JWT with:

- **`library_access`** — which document libraries they can search
- **`roles`** — for future permission rules

---

## Next steps for developers

- Upload documents on the **Ingest** tab, or batch-ingest with `ingest_cli --manifest` and a local `manifest.json`.
- Swap Ollama for OpenAI, vLLM, or another OpenAI-compatible API via `LLM_BASE_URL` + `LLM_MODEL`.
- Optional: OpenTelemetry, custom vector DBs — see code under `services/ai-core/ai_assistant/`.
