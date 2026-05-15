# AI Assistant

A small demo app that answers questions using **your documents** (not made-up facts). You type a question in a chat window; the system finds relevant text, then a language model writes an answer and shows **which documents** it used.

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

Sample documents live in [`services/ai-core/ai_assistant/ingestion/bundled_docs/`](services/ai-core/ai_assistant/ingestion/bundled_docs/) (including **RFC 2119** about words like MUST and SHOULD).

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

**Ingest (separate workflow):** when you run `ingest_cli`, only **ai-core**, **Qdrant**, and the **embedder** (FastEmbed inside **ai-core**) are involved — that path loads documents into Qdrant; it does not use the BFF or Ollama.

---

## Before you start

1. **Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)** (Mac, Windows, or Linux).
2. **Open Docker Desktop** and wait until it says it is running.
3. **Clone this repo** and open a terminal in the project folder:

```bash
cd ai-assistant
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

### Step 3 — Load the sample documents into search

On a **fresh** install, documents are loaded automatically when Qdrant is empty.

If search results look wrong (see [Fix common problems](#fix-common-problems) below), reload the bundled sample docs:

```bash
docker compose build --no-cache ai-core
docker compose up -d --force-recreate ai-core
docker compose exec ai-core python -m ai_assistant.ingestion.ingest_cli --recreate-collection --yes
```

When it finishes, you should see something like: `Done: upserted N points into 'assistant_chunks'`.

### Step 4 — Open the chat and ask a question

1. Open **http://localhost:3000** in your browser.
2. Type a question, for example:

   > In IETF requirements language, what is the difference between MUST and SHOULD?

3. Press **Send** and wait (local CPU answers can take **30 seconds or more**).

A good answer will mention **RFC 2119** and cite a document id like **`ietf-bcp14-rfc2119`**.

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
  -d '{"message":"In IETF requirements language, what is the difference between MUST and SHOULD?","structured_output":false}' | jq .
```

---

## Fix common problems

### “Grounded reply (no LLM configured)”

The app found documents but **no chat model** is connected. Do **Step 2** (`ollama pull`) and make sure **ollama** and **ai-core** are running:

```bash
docker compose ps
```

### “I do not have enough grounded information…” and citations look wrong

Example bad citations: `doc-policy-001`, `doc-external-99` — those are **not** from this repo’s sample set.

**Fix:** reload the bundled documents (**Step 3**). After that, citations should include names like **`ietf-bcp14-rfc2119`**.

### Ingest command fails with `unexpected keyword argument 'ge'`

The **ai-core** container is using an **old image**. Rebuild and recreate:

```bash
docker compose build --no-cache ai-core
docker compose up -d --force-recreate ai-core
docker compose exec ai-core grep "_bounded_int" /app/ai_assistant/ingestion/ingest_cli.py
```

If that `grep` shows a match, run ingest again (**Step 3**).

### Chat is very slow

Local **Llama on CPU** is slow. Use the smaller `llama3.2:1b` model, or give Ollama a GPU (Linux + NVIDIA — see comments in [`docker-compose.yml`](docker-compose.yml) under **ollama**).

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
| `SEED_VECTOR_COLLECTION_ON_STARTUP` | `true` (if set) | Auto-load sample docs when Qdrant is empty |

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

**Ingest CLI** (reload documents):

```bash
docker compose exec ai-core python -m ai_assistant.ingestion.ingest_cli --dry-run
docker compose exec ai-core python -m ai_assistant.ingestion.ingest_cli --recreate-collection --yes
```

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

- Add your own documents via [`manifest.json`](services/ai-core/ai_assistant/ingestion/bundled_docs/manifest.json) and run the ingest CLI.
- Swap Ollama for OpenAI, vLLM, or another OpenAI-compatible API via `LLM_BASE_URL` + `LLM_MODEL`.
- Optional: OpenTelemetry, custom vector DBs — see code under `services/ai-core/ai_assistant/`.
