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
        bare slide JSON (no image/html yet) ──► saved to Postgres
        immediately — the frontend can already show slide count
        and raw content here, before anything below finishes
                          │
                          ▼
      ┌───────────────────┴───────────────────┐
      │   PER SLIDE, IN PARALLEL (thread pool)  │
      │                                         │
      │   IMAGE AGENT → HTML AGENT → (if QA     │
      │   enabled) screenshot + vision critique  │
      │                                         │
      │   each slide commits to Postgres the    │
      │   moment IT finishes — independent of   │
      │   every other slide                     │
      └───────────────────┬───────────────────┘
                          ▼
                    mark job done

  Chat follow-ups ("make this more premium") go through a separate
  RevisionAgent → regenerates the deck JSON → same per-slide parallel
  render pipeline.
```

**Key architectural decisions:**

1. The AI never places raw pixels by hand. The `SlidePlannerAgent`/
   `RevisionAgent` produce semantic JSON
   (`{"type": "data_story", "elements": [...]}`) — that stays the editable
   source of truth. A separate `HTMLAgent` then turns each slide's content,
   plus the deck's shared theme, into an actual styled HTML fragment. The
   frontend renders that HTML directly inside a sandboxed `<iframe>`
   (`sandbox=""` — render-only, no script execution). If HTML generation
   fails for a slide, it falls back to the generic component layout
   (`frontend/src/lib/layout-engine.ts`), so a single bad LLM call never
   breaks the whole deck.

2. **Slides render progressively, checkpointed one at a time.** Planning
   (research → story → slide JSON → theme) is inherently sequential and
   runs once for the whole deck, but everything after that — image
   generation, HTML generation, and QA — happens **per slide, in
   parallel**, each on its own thread with its own database session. The
   moment one slide's HTML (and QA, if enabled) is ready, that slide's row
   is committed immediately — not held in memory until the whole deck
   finishes. The frontend polls the presentation while a job is running
   (not just once at the end), so slides pop in one at a time as they
   complete, and if the worker crashes or is restarted mid-deck, whatever
   slides already finished are not lost.

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
  claude_code_provider.py  → uses a user's own Claude Code subscription (see below)
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

**Claude Code as a provider.** If you already pay for a Claude subscription
and have Claude Code set up, you can generate through that instead of a
separate `ANTHROPIC_API_KEY`:

1. On your own machine, run `claude setup-token` (one time) — this issues a
   long-lived OAuth token tied to your subscription.
2. Put it in `backend/.env` as `CLAUDE_CODE_OAUTH_TOKEN=...`.
3. Pick "Claude Code (your subscription)" in the provider picker.

Implementation notes, confirmed by direct testing against this repo:
- The backend/worker Docker image installs Node.js + `@anthropic-ai/claude-code`
  so the `claude` binary is available inside the container.
- `ClaudeCodeProvider` shells out to `claude -p "<prompt>" --output-format json`
  and parses the `result` field from the JSON response.
- **Deliberately not `--bare` mode.** Bare mode (the mode Anthropic's own
  docs recommend for scripted/CI use) only accepts a plain
  `ANTHROPIC_API_KEY` — with only `CLAUDE_CODE_OAUTH_TOKEN` set, bare mode
  replies `"Not logged in · Please run /login"` even though the token is
  valid. Plain (non-bare) `-p` mode does honor the OAuth token correctly.
- Concurrent invocations (tested with 3 simultaneous calls via a thread
  pool, matching how the per-slide pipeline actually runs) each returned
  correct, independent results — no observed session locking issues, even
  though Anthropic's docs don't explicitly document this as safe.
- **Text-only.** Claude Code's headless mode doesn't document image/vision
  input, so this provider isn't used for the vision QA step — sending it a
  multimodal message raises immediately rather than silently mishandling it.

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
│   │   │   ├── html_agent.py     # per-slide HTML generation, run in parallel
│   │   │   ├── design_reference.py # design principles/avoid-list + technique examples
│   │   │   ├── qa_agent.py       # screenshot + vision critique (opt-in, off by default)
│   │   │   ├── revision_agent.py # chat-based whole-deck edits
│   │   │   └── json_utils.py     # robust JSON extraction from model output
│   │   ├── worker/
│   │   │   ├── celery_app.py   # Celery configured against Redis
│   │   │   ├── tasks.py        # generate_presentation / refine_presentation (planning only)
│   │   │   └── slide_pipeline.py # per-slide image+HTML+QA, parallel, checkpointed to Postgres
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
    │   ├── decks/page.tsx      # list all presentations, open or retry any of them
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
3. The worker runs the `Orchestrator` — research → story → structured slide
   JSON → theme — reporting each step through `Job.step`, polled by the
   frontend. This part is sequential (each step needs the last).
4. The resulting bare slide JSON is saved as `Slide` rows immediately, one
   `INSERT` per slide, before any image or HTML exists for them — the
   frontend (which polls the presentation, not just the job, while it's
   running) can already show the deck's slide count and raw content here.
5. `render_slides_in_parallel` then processes every slide **concurrently**,
   one thread per slide: generate its image(s) → generate its HTML → (if
   QA is enabled) screenshot + vision critique. The moment a slide's own
   work finishes, that slide's row is committed — independently of every
   other slide, using its own database session. Slides visibly pop in on
   screen one at a time as they complete, not all at once at the end. A
   screenshot or vision-model failure only affects that slide's
   `qa_report`, never the rest of the deck.
6. Job is marked done (or `failed`, with the error surfaced in the UI —
   job failures no longer hang forever). Past 3 minutes with no progress,
   the status endpoint asks Celery whether the task is actually still
   running before deciding it's dead — see "Gotchas" below.
7. Further prompts ("make this more premium", "shorten slide 5") go through
   `POST /presentations/{id}/chat` → `refine_presentation` → the
   `RevisionAgent` regenerates the whole deck JSON with the instruction
   applied, then goes through the same per-slide parallel render pipeline.
8. **Stop generating** (main canvas or chat panel) calls
   `POST /presentations/{id}/cancel`, which does a real
   `celery_app.control.revoke(task_id, terminate=True)` — this actually
   kills the worker process running the task, not just the frontend's
   poll loop, and marks the `Job` row `cancelled` immediately.
9. **Your decks** (`/decks`) lists every presentation with its status;
   **Retry** on any of them (`POST /presentations/{id}/retry`) clears its
   slides and re-runs `generate_presentation` from the same brief.

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
  our own `except Exception` handler never runs, so the `Job` row would be
  stuck at its last reported step forever and the frontend would poll it
  endlessly.
- **A single LLM call can legitimately take longer than any reasonable
  fixed timeout** — confirmed directly: `SlidePlannerAgent` took ~4m45s
  planning 10 slides on a local CPU model, well past an earlier 3-minute
  cutoff, while the task was still completely healthy. A wall-clock-only
  staleness check can't tell "slow" from "dead". `GET /presentations/{id}/status`
  now uses both: past `SOFT_STALE_TIMEOUT` (3 min) with no progress, it
  asks Celery's `control.inspect().active()` whether the task is actually
  still running — confirmed alive (or undeterminable, e.g. a broker
  hiccup) keeps waiting; confirmed dead marks it `failed` immediately.
  `HARD_STALE_TIMEOUT` (20 min) is a backstop in case liveness can never
  be confirmed. The per-slide parallel pipeline (see Architecture) also
  helps here directly — instead of one giant step covering the whole
  deck, each slide checkpoints (and bumps the job's timestamp) the moment
  it finishes, so the staleness clock resets constantly during normal
  operation rather than only at a few big step boundaries.
- **QA (screenshot + vision-model critique) is genuinely slow** — one
  extra model call per slide — so it's **off by default**, with a UI
  toggle ("Run visual QA") explaining the tradeoff.
- **A failed job doesn't mean the content is gone.** The frontend used to
  hide the slide canvas entirely behind a red error box whenever the job
  ended in `failed` — even if generation had actually completed and only a
  later, unrelated step (like QA) failed. It now always shows whatever
  slides exist, with the error as a small non-blocking note instead.
- **Local small models (e.g. `llama3.2:3b`) partially copy the HTMLAgent's
  style-reference example instead of adapting it** — confirmed directly by
  inspecting output (verbatim placeholder sentences leaking into unrelated
  slides, and outright bugs like `color` matching `background`, or a
  `rotate(45deg)` on a stat number). This is a model capability ceiling,
  not a prompt bug: instruction-following at this scale is unreliable for
  "use this as inspiration, don't copy it." Two hard rules were added
  regardless (never match text color to its background; never rotate
  text), but the HTML quality of this feature scales with model
  capability — SiliconFlow's larger models or OpenAI/Anthropic will
  follow the design guidance far more faithfully than a local 3B model.

### Debugging

Every agent and the Celery tasks log through the standard `logging` module
(`docker compose logs -f worker`) — each pipeline step, LLM call, JSON
parse failure/fallback, image generation failure, and QA skip reason is
logged at INFO/WARNING so you can see exactly what happened without
reproducing via the API.

## Current status

Fully working end to end, verified with real requests against a running
stack (Postgres, Redis, Celery worker, Flower, FastAPI, Next.js):

- Structured content generation (research → story → JSON slides → theme),
  with a plain-text fallback if the model's JSON doesn't parse
- Progressive, checkpointed, parallel per-slide rendering: image
  generation → HTML generation → (if enabled) QA all happen per slide, on
  their own thread, committed to Postgres the moment that slide finishes —
  not held in memory until the whole deck completes. The frontend polls
  the presentation while a job runs and slides appear on screen one at a
  time as they're ready, with a live "N of M ready" indicator
- Per-slide HTML generation: each slide gets a real, styled HTML fragment
  from an LLM call, rendered in a sandboxed iframe, with the generic
  component layout as a fallback if it fails
- Image generation wired to real slide `image` elements, served via
  `/media`
- Visual QA (opt-in, off by default — it's slow): real Playwright
  screenshot → vision-model critique, stored per slide, gracefully skipped
  (not fatal) on any failure
- Chat-based whole-deck revision
- Provider/model picker in the UI, backed by live model listing where the
  provider supports it — including using a user's own Claude Code
  subscription (via `claude setup-token`) instead of a separate API key
- Real cancellation — "Stop generating" actually terminates the worker
  process running the task (`celery_app.control.revoke(..., terminate=True)`),
  not just the frontend's poll loop
- A decks list (`/decks`) to see every presentation and retry any of them
- Job failure handling — failed jobs surface the real error instead of
  hanging at "queued" forever; stale jobs (worker died/restarted mid-task)
  self-heal to `failed` after a timeout instead of polling forever
- URL-based resume — refreshing `/?id=<presentation>` reloads that
  presentation's state instead of starting over
- Agent-level logging — every agent and task logs its steps, LLM calls,
  and failure/fallback reasons (`docker compose logs -f worker`)

What's still simplified and worth revisiting:
- The HTML agent isn't given the other slides' HTML for cross-slide
  consistency checks — occasional per-slide color/style drift is possible
  despite the shared theme
- The generic fallback layout only does a two-column primary/secondary
  split — no constraint rules (overlap avoidance, min font size)
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
- Smarter retry: since slides now checkpoint independently, `Retry` could
  skip slides that already rendered successfully instead of wiping the
  whole deck — not yet implemented, currently still a full restart
- An estimated-time indicator based on provider/model speed and slide
  count (not implemented — needs a clearer spec for what "estimate" should
  be based on before building it)
