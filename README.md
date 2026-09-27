# AI Presentation Studio

Prompt-driven presentation generator. The user describes what they want, an
agent pipeline researches and plans the content, a layout engine turns
semantic content into slide geometry, and a visual QA loop screenshots the
result and critiques it. There is no manual slide editor — every change
happens through the chat panel.

## Architecture

```
                         USER
                          │
                          ▼
                 ┌─────────────────┐
                 │  FRONTEND       │  Next.js — chat UI, provider/model
                 │  (Next.js)      │  picker, slide canvas, layout engine,
                 │                 │  render route
                 └────────┬────────┘
                          │ REST (create / status / chat / providers)
                          ▼
                 ┌─────────────────┐
                 │  BACKEND API    │  FastAPI — presentations, jobs,
                 │  (FastAPI)      │  chat, provider config
                 └────────┬────────┘
                          │ enqueues
                          ▼
                 ┌─────────────────┐
                 │  REDIS          │  broker + result backend
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │  CELERY WORKER  │  runs the agent pipeline
                 └────────┬────────┘
                          │
        ┌─────────────────┼──────────────────┐
        ▼                 ▼                  ▼
   RESEARCH AGENT    STORY AGENT       SLIDE PLANNER AGENT
        │                 │           (structured JSON, with a
        │                 │            plain-text fallback if the
        │                 │            model's JSON doesn't parse)
        └─────────────────┼──────────────────┘
                          ▼
                  DESIGN AGENT (deterministic theme pick)
                          ▼
                  IMAGE AGENT (generates + saves slide images)
                          ▼
                 semantic slide JSON  ──────────►  saved to Postgres
                          │
                          ▼
        Playwright hits the frontend's own
        /render/:presentationId/:slideId route
        (same React components the user sees)
                          │
                          ▼
                    screenshot
                          │
                          ▼
          QA AGENT (vision-capable model critiques it;
           failures/missing models are skipped, never fatal)
                          │
                          ▼
                    mark job done

  Chat follow-ups ("make this more premium") go through a separate
  RevisionAgent → regenerates the deck JSON → re-runs image + QA agents.
```

**Key architectural decision:** the AI never outputs pixel coordinates. It
only produces semantic JSON (`{"type": "data_story", "elements": [...]}`).
The frontend's layout engine (`frontend/src/lib/layout-engine.ts`) is the
only thing that turns that into an actual arrangement, which keeps output
consistent and makes automated QA possible.

## LLM / image provider abstraction

Nearly every provider (OpenAI, SiliconFlow, Ollama running locally, DeepSeek,
Together...) exposes an **OpenAI-compatible** chat completions endpoint, so
one client class covers all of them — only the `base_url` and API key
change. Anthropic gets its own small client since its message format
differs.

```
backend/app/providers/llm/
  base.py                 → LLMProvider interface (chat / stream)
  openai_compatible.py     → OpenAI, SiliconFlow, Ollama, DeepSeek, Together...
  anthropic_provider.py    → Claude
  registry.py              → get_llm_provider(name, model) picks the active one
  catalog.py               → GET /providers model listing (live models.list()
                             where available, curated fallback otherwise)
  ollama_utils.py          → list pulled models / pull a model on demand

backend/app/providers/image/
  base.py
  siliconflow.py           → FLUX/SD image generation
  pollinations.py          → free, keyless fallback
  registry.py
```

The frontend has a **provider + model picker** in the chat panel (like any
chat app) — LLM provider, model, and image provider, sourced live from
`GET /providers`. Selections are locked once a presentation exists (a
presentation's provider doesn't change mid-conversation).

**Ollama models are selectable even before they're pulled.** The picker
shows a small curated list of common models; ones not yet present locally
are marked "(downloads on first use)". Selecting one and generating
triggers `ensure_model_pulled()` in the Celery task before the pipeline
runs, reported as a `pulling_model` progress step.

## Repository structure

```
ai_presentation/
├── docker-compose.yml          # postgres, redis, backend, celery worker, flower
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI app, router registration, /media static mount
│   │   ├── core/config.py      # env-driven settings (pydantic-settings)
│   │   ├── db/session.py       # SQLModel engine + session
│   │   ├── models/              # Presentation, Slide, Job, Message
│   │   ├── providers/
│   │   │   ├── llm/            # provider-agnostic LLM clients + catalog + ollama utils
│   │   │   └── image/          # provider-agnostic image clients
│   │   ├── agents/
│   │   │   ├── orchestrator.py # runs the content pipeline, reports progress
│   │   │   ├── research_agent.py
│   │   │   ├── story_agent.py
│   │   │   ├── slide_planner.py  # structured JSON output + fallback
│   │   │   ├── design_agent.py   # deterministic theme selection
│   │   │   ├── image_agent.py    # generates + saves slide images
│   │   │   ├── qa_agent.py       # screenshot + vision critique
│   │   │   ├── revision_agent.py # chat-based whole-deck edits
│   │   │   └── json_utils.py     # robust JSON extraction from model output
│   │   ├── worker/
│   │   │   ├── celery_app.py   # Celery configured against Redis
│   │   │   └── tasks.py        # generate_presentation / refine_presentation
│   │   ├── rendering/
│   │   │   └── qa_screenshot.py # Playwright screenshot of the frontend's render route
│   │   ├── media/               # generated images (gitignored, served at /media)
│   │   └── api/routes/         # presentations, chat, providers
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
└── frontend/
    ├── src/app/
    │   ├── page.tsx            # 3-pane UI: slides / canvas / AI chat + provider picker
    │   └── render/[presentationId]/[slideId]/page.tsx  # bare slide render, used by Playwright for QA
    ├── src/components/slides/  # SlideRenderer + per-element components
    ├── src/lib/
    │   ├── slide-schema.ts     # semantic JSON types + Theme type
    │   ├── layout-engine.ts    # semantic JSON → arrangement (no pixels)
    │   └── api.ts              # backend client
    └── .env.local.example
```

## Generation flow

1. User types a prompt (or clicks a preset) in the chat panel →
   `POST /presentations` with the chosen provider/model.
2. Backend creates a `Presentation` row, the URL updates to `/?id=<id>` (so
   a refresh resumes the same presentation instead of dropping back to
   blank), and `generate_presentation` is enqueued on Celery.
3. The worker runs the `Orchestrator` (research → story → structured slide
   JSON → theme → images), reporting each step through `Job.step`, polled
   by the frontend.
4. Slide JSON is saved as `Slide` rows.
5. For each slide, Playwright screenshots the frontend's own render route
   and a vision-capable model critiques it; the result is stored in
   `Slide.qa_report` (shown as a small indicator dot on the slide thumbnail).
   A screenshot or vision-model failure is recorded and skipped, never fatal.
6. Job is marked done (or `failed`, with the error surfaced in the UI —
   job failures no longer hang forever).
7. Further prompts ("make this more premium", "shorten slide 5") go through
   `POST /presentations/{id}/chat` → `refine_presentation` → the
   `RevisionAgent` regenerates the whole deck JSON with the instruction
   applied, then re-runs image generation and QA.

## Local development

**Requirements:** Docker, Node 20+, and at least one working LLM provider:
a SiliconFlow API key, an OpenAI/Anthropic key, or a local Ollama install.

```bash
cp backend/.env.example backend/.env      # fill in provider keys
cp frontend/.env.local.example frontend/.env.local

docker compose up --build                 # postgres, redis, backend api, celery worker, flower
```

Flower (job monitoring) is at `http://localhost:5555`.

Run the frontend separately for hot reload:

```bash
cd frontend
npm run dev                                # http://localhost:3000
```

### Gotchas discovered running this for real

- **SiliconFlow has two separate platforms** — `api.siliconflow.cn` and
  `api.siliconflow.com` — with **separate accounts and keys**. A key from
  one will fail on the other with a misleading `401 Token is invalid`
  instead of a clearer error. Use the domain matching where you created
  the key.
- **`image_size` must be one of SiliconFlow's exact enum values**
  (`512x512`, `768x1024`, `1024x768`, `576x1024`, `1024x576`) —
  `1024x1024` is not accepted.
- **Docker networking:** `backend`/`worker` run in containers, but Ollama
  and (in dev) the Next.js frontend run on your host. From inside a
  container, `localhost` means the container itself — use
  `host.docker.internal` for `OLLAMA_BASE_URL` and `FRONTEND_RENDER_URL`
  (Playwright, which runs in the backend container, needs this to reach
  the frontend dev server for QA screenshots). `PUBLIC_BACKEND_URL` stays
  `localhost` on purpose — it's read by the browser on your host, not by
  container code.
- **Ollama install:** prefer `brew install --cask ollama` (prebuilt binary)
  over `brew install ollama` (formula), which compiles `llama.cpp` from
  source and is drastically slower.
- **Worker restarts mid-task orphan the job row.** If `backend`/`worker`
  restart while a Celery task is running, the process is killed outright —
  our own `except Exception` handler never runs, so the `Job` row is stuck
  at its last reported step forever and the frontend polls it endlessly.
  `GET /presentations/{id}/status` now self-heals this: if a non-terminal
  job hasn't updated in `STALE_JOB_TIMEOUT` (3 minutes), it's marked
  `failed` with an explanatory error on the next poll.

### Debugging

Every agent and the Celery tasks log through the standard `logging` module
(`docker compose logs -f worker`) — each pipeline step, LLM call, JSON
parse failure/fallback, image generation failure, and QA skip reason is
logged at INFO/WARNING so you can see exactly what happened without
reproducing via the API.

## Current status

Fully working end to end, verified with real requests against a running
stack (Postgres, Redis, Celery worker, Flower, FastAPI, Next.js):

- Structured content generation (research → story → JSON slides → theme →
  images), with a plain-text fallback if the model's JSON doesn't parse
- Image generation wired to real slide `image` elements, served via
  `/media`
- Visual QA: real Playwright screenshot → vision-model critique, stored per
  slide, gracefully skipped (not fatal) on any failure
- Chat-based whole-deck revision
- Provider/model picker in the UI, backed by live model listing where the
  provider supports it
- Job failure handling — failed jobs surface the real error instead of
  hanging at "queued" forever
- URL-based resume — refreshing `/?id=<presentation>` reloads that
  presentation's state instead of starting over

What's still simplified and worth revisiting:
- The layout engine only does a two-column primary/secondary split — no
  constraint rules (overlap avoidance, min font size, density limits) yet
- Research agent doesn't track real sources/citations yet
- Chat revision replaces the whole deck rather than diffing individual
  slides — reliable but wasteful for small edits
- No chart/diagram rendering yet (chart elements render as placeholders)

## Roadmap

- Constraint-based layout engine (safe margins, min font size, overlap checks)
- Research agent with actual web search + source tracking
- Diagram/chart agents (D3-based rendering)
- Version history per presentation
- Context-aware, scoped chat editing (element / slide / deck / narrative)
- Targeted slide-level revision instead of whole-deck regeneration
