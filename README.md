# AI Presentation Studio

Prompt-driven presentation generator. The user describes what they want, an
agent pipeline researches and plans the content, a layout engine turns
semantic content into slide geometry, and a visual QA loop screenshots the
result and fixes issues automatically. There is no manual slide editor —
every change happens through the chat panel.

## Architecture

```
                         USER
                          │
                          ▼
                 ┌─────────────────┐
                 │  FRONTEND       │  Next.js — chat UI, slide canvas,
                 │  (Next.js)      │  layout engine, render route
                 └────────┬────────┘
                          │ REST (create / status / chat)
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
        │                 │                  │
        └─────────────────┼──────────────────┘
                          ▼
                  DESIGN AGENT (theme)
                          │
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
                  QA AGENT (vision model)
                          │
                 issues found? ──yes──► patch semantic JSON ──► re-render
                          │
                          no
                          ▼
                    mark job done
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
  registry.py              → get_llm_provider(name) picks the active one

backend/app/providers/image/
  base.py
  siliconflow.py           → free-tier FLUX/SD image generation
  pollinations.py          → free, keyless fallback
  registry.py
```

Which provider is active is controlled by `DEFAULT_LLM_PROVIDER` /
`DEFAULT_IMAGE_PROVIDER` in `backend/.env`, or per-presentation via the
`llm_provider` / `image_provider` columns on the `Presentation` row.

## Repository structure

```
ai_presentation/
├── docker-compose.yml          # postgres, redis, backend, celery worker, flower
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI app, router registration
│   │   ├── core/config.py      # env-driven settings (pydantic-settings)
│   │   ├── db/session.py       # SQLModel engine + session
│   │   ├── models/              # Presentation, Slide, Job, Message
│   │   ├── providers/
│   │   │   ├── llm/            # provider-agnostic LLM clients
│   │   │   └── image/          # provider-agnostic image clients
│   │   ├── agents/
│   │   │   ├── orchestrator.py # runs the pipeline, reports progress
│   │   │   ├── research_agent.py
│   │   │   ├── story_agent.py
│   │   │   ├── slide_planner.py
│   │   │   ├── design_agent.py
│   │   │   └── qa_agent.py
│   │   ├── worker/
│   │   │   ├── celery_app.py   # Celery configured against Redis
│   │   │   └── tasks.py        # generate_presentation task
│   │   ├── rendering/
│   │   │   └── qa_screenshot.py # Playwright screenshot of the frontend's render route
│   │   └── api/routes/         # presentations, chat, providers
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
└── frontend/
    ├── src/app/
    │   ├── page.tsx            # 3-pane UI: slides / canvas / AI chat
    │   └── render/[presentationId]/[slideId]/page.tsx  # bare slide render, used by Playwright for QA
    ├── src/components/slides/  # SlideRenderer + per-element components
    ├── src/lib/
    │   ├── slide-schema.ts     # semantic JSON types
    │   ├── layout-engine.ts    # semantic JSON → arrangement (no pixels)
    │   └── api.ts              # backend client
    └── .env.local.example
```

## Generation flow

1. User types a prompt in the chat panel → `POST /presentations`.
2. Backend creates a `Presentation` row and enqueues `generate_presentation`
   on Celery.
3. The worker runs the `Orchestrator`, which calls each agent in turn
   (research → story → slide planning → design) and reports its current
   step back through `Job.step`, polled by the frontend.
4. Semantic slide JSON is saved as `Slide` rows.
5. For each slide, Playwright screenshots the frontend's own render route
   and a vision-capable model critiques it; problems get patched back into
   the semantic JSON and re-rendered.
6. Job is marked done; the frontend loads the finished slides.
7. Further prompts ("make this more premium", "shorten slide 5") go through
   `POST /presentations/{id}/chat` — this refinement path is stubbed for now
   (see Roadmap).

## Local development

**Requirements:** Docker, Node 20+, a SiliconFlow API key (free tier) or a
local Ollama install.

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

## Current status (MVP scaffold)

What's wired end to end: API → Postgres → Redis/Celery job → progress
polling → frontend rendering → Playwright render route.

What's stubbed and needs real logic next:
- Agents currently make a single LLM call each and don't yet parse
  structured output into real `Slide` rows (`slide_planner.py` returns `[]`).
- `design_agent.py` and `qa_agent.py` are pass-throughs — no theme
  application or actual screenshot/critique loop yet.
- The layout engine only does a two-column primary/secondary split — no
  constraint rules (overlap avoidance, min font size, density limits) yet.
- Chat-based refinement (`/chat` route) doesn't call the orchestrator yet.
- No source/citation tracking on research claims yet.

## Roadmap

- Structured-output slide generation (JSON-schema-constrained LLM calls)
- Constraint-based layout engine (safe margins, min font size, overlap checks)
- Real QA loop: screenshot → vision model → patch → re-render
- Research agent with actual web search + source tracking
- Diagram/chart agents (D3-based rendering)
- Version history per presentation
- Context-aware chat editing (element / slide / deck / narrative scope)
