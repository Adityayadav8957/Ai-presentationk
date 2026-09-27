"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

import { SlideRenderer } from "@/components/slides/SlideRenderer";
import {
  type ChatMessage,
  type ProvidersResponse,
  createPresentation,
  getJobStatus,
  getMessages,
  getPresentation,
  getProviders,
  sendChatMessage,
} from "@/lib/api";
import type { SlideContent, Theme } from "@/lib/slide-schema";

type QAReport = { issues?: string[]; passed?: boolean; skipped?: boolean };
type Slide = { id: string; content: SlideContent; qa_report?: QAReport };

const STEP_LABELS: Record<string, string> = {
  understanding: "Understanding your request",
  understanding_request: "Understanding your request",
  pulling_model: "Preparing the model",
  researching: "Researching",
  story_building: "Building the narrative",
  slide_planning: "Planning slides",
  revising: "Revising the presentation",
  designing: "Designing the theme",
  image_generation: "Generating visuals",
  qa: "Reviewing quality",
  final: "Finishing up",
};

function stepLabel(step: string | null): string {
  if (!step) return "Working…";
  return STEP_LABELS[step] ?? step.replace(/_/g, " ");
}

function Loader({ label }: { label: string }) {
  return (
    <div className="flex flex-col items-center gap-5">
      <div className="relative h-14 w-14">
        <div className="absolute inset-0 rounded-full border-4 border-neutral-200" />
        <div className="absolute inset-0 animate-spin rounded-full border-4 border-transparent border-t-neutral-900 border-r-neutral-900" />
      </div>
      <div className="flex flex-col items-center gap-2">
        <span className="text-sm font-medium text-neutral-800">{label}</span>
        <div className="h-1.5 w-48 overflow-hidden rounded-full bg-neutral-200">
          <div className="h-full w-1/3 rounded-full bg-neutral-900 animate-loading-bar" />
        </div>
      </div>
    </div>
  );
}

const PRESET_PROMPTS = [
  {
    label: "Investor pitch deck",
    prompt: "Create a 10-slide pitch deck for an AI healthcare startup targeting investors",
  },
  {
    label: "Product launch",
    prompt: "Create a 6-slide product launch overview for a new mobile app",
  },
  {
    label: "Quarterly review",
    prompt: "Create an 8-slide quarterly business review for company leadership",
  },
  {
    label: "Educational overview",
    prompt: "Create a 5-slide educational overview of climate change for students",
  },
];

function PresentationApp() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [prompt, setPrompt] = useState("");
  const [presentationId, setPresentationId] = useState<string | null>(null);
  const [step, setStep] = useState<string | null>(null);
  const [slides, setSlides] = useState<Slide[]>([]);
  const [theme, setTheme] = useState<Theme | undefined>(undefined);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [activeSlide, setActiveSlide] = useState(0);
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [providers, setProviders] = useState<ProvidersResponse | null>(null);
  const [llmProvider, setLlmProvider] = useState("");
  const [llmModel, setLlmModel] = useState("");
  const [imageProvider, setImageProvider] = useState("");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    getProviders().then((data) => {
      setProviders(data);
      setLlmProvider(data.defaults.llm);
      setImageProvider(data.defaults.image);
      const defaultModels = data.llm.find((p) => p.name === data.defaults.llm)?.models;
      setLlmModel(defaultModels?.[0]?.id ?? "");
    });
  }, []);

  // Resume from the URL on load/refresh instead of dropping back to blank state.
  useEffect(() => {
    const id = searchParams.get("id");
    if (!id) return;

    setPresentationId(id);
    setIsBusy(true);

    (async () => {
      await Promise.all([refreshPresentation(id), refreshMessages(id)]);
      const job = await getJobStatus(id);
      if (job?.status === "done") {
        setIsBusy(false);
      } else if (job?.status === "failed") {
        setError(job.error ?? "Generation failed for an unknown reason.");
        setIsBusy(false);
      } else {
        setStep(job?.step ?? null);
        pollUntilDone(
          id,
          async () => {
            await Promise.all([refreshPresentation(id), refreshMessages(id)]);
            setIsBusy(false);
          },
          (message) => {
            setError(message);
            setIsBusy(false);
          },
        );
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleLlmProviderChange(name: string) {
    setLlmProvider(name);
    setLlmModel(providers?.llm.find((p) => p.name === name)?.models?.[0]?.id ?? "");
  }

  async function refreshPresentation(id: string) {
    const data = await getPresentation(id);
    setSlides(data.slides ?? []);
    setTheme(data.presentation?.theme);
  }

  async function refreshMessages(id: string) {
    const msgs = await getMessages(id);
    setMessages(msgs);
  }

  function pollUntilDone(id: string, onDone: () => void, onFail: (message: string) => void) {
    pollRef.current = setInterval(async () => {
      const job = await getJobStatus(id);
      setStep(job?.step ?? null);
      if (job?.status === "done") {
        if (pollRef.current) clearInterval(pollRef.current);
        onDone();
      } else if (job?.status === "failed") {
        if (pollRef.current) clearInterval(pollRef.current);
        onFail(job.error ?? "Generation failed for an unknown reason.");
      }
    }, 2000);
  }

  async function handleSubmit(presetPrompt?: string) {
    const currentPrompt = presetPrompt ?? prompt;
    if (!currentPrompt.trim() || isBusy) return;
    setPrompt("");
    setIsBusy(true);
    setError(null);

    setMessages((prev) => [
      ...prev,
      { id: `local-${Date.now()}`, role: "user", content: currentPrompt, created_at: "" },
    ]);

    if (!presentationId) {
      const { presentation_id } = await createPresentation({
        topic: currentPrompt,
        llm_provider: llmProvider || undefined,
        llm_model: llmModel || undefined,
        image_provider: imageProvider || undefined,
      });
      setPresentationId(presentation_id);
      router.replace(`/?id=${presentation_id}`);
      pollUntilDone(
        presentation_id,
        async () => {
          await refreshPresentation(presentation_id);
          setIsBusy(false);
        },
        (message) => {
          setError(message);
          setIsBusy(false);
        },
      );
      return;
    }

    await sendChatMessage(presentationId, currentPrompt);
    pollUntilDone(
      presentationId,
      async () => {
        await Promise.all([refreshPresentation(presentationId), refreshMessages(presentationId)]);
        setIsBusy(false);
      },
      (message) => {
        setError(message);
        setIsBusy(false);
      },
    );
  }

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const active = slides[activeSlide];

  return (
    <div className="grid h-screen grid-cols-[220px_1fr_340px] bg-neutral-50 text-neutral-900">
      <aside className="border-r border-neutral-200 p-4">
        <h2 className="mb-4 text-sm font-medium text-neutral-500">Slides</h2>
        <ul className="flex flex-col gap-2">
          {slides.map((slide, i) => (
            <li key={slide.id}>
              <button
                onClick={() => setActiveSlide(i)}
                className={`relative w-full rounded-md border px-3 py-2 text-left text-sm ${
                  i === activeSlide
                    ? "border-neutral-900 bg-neutral-900 text-white"
                    : "border-neutral-200 bg-white"
                }`}
              >
                {String(i + 1).padStart(2, "0")}
                {slide.qa_report?.issues && slide.qa_report.issues.length > 0 && (
                  <span
                    title={slide.qa_report.issues.join("; ")}
                    className="absolute right-2 top-2 h-2 w-2 rounded-full bg-amber-500"
                  />
                )}
              </button>
            </li>
          ))}
        </ul>
      </aside>

      <main className="flex items-center justify-center overflow-auto p-8">
        {error ? (
          <div className="max-w-md rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            <p className="font-medium">Generation failed</p>
            <p className="mt-1 text-xs">{error}</p>
          </div>
        ) : active ? (
          <div className="w-full max-w-4xl shadow-lg">
            <SlideRenderer content={active.content} theme={theme} />
          </div>
        ) : isBusy ? (
          <Loader label={stepLabel(step)} />
        ) : (
          <div className="text-center text-neutral-400">
            <span className="text-sm">No presentation yet — describe one on the right.</span>
          </div>
        )}
      </main>

      <aside className="flex flex-col border-l border-neutral-200 p-4">
        <h2 className="mb-4 text-sm font-medium text-neutral-500">AI Assistant</h2>

        <div className="flex-1 space-y-3 overflow-y-auto">
          {messages.map((m) => (
            <div
              key={m.id}
              className={`rounded-md px-3 py-2 text-sm ${
                m.role === "user" ? "bg-neutral-900 text-white" : "bg-neutral-100"
              }`}
            >
              {m.content}
            </div>
          ))}
        </div>

        <div className="mt-3 flex flex-col gap-3">
          {!presentationId && (
            <div className="flex flex-wrap gap-2">
              {PRESET_PROMPTS.map((p) => (
                <button
                  key={p.label}
                  onClick={() => handleSubmit(p.prompt)}
                  disabled={isBusy}
                  className="rounded-full border border-neutral-200 bg-white px-3 py-1 text-xs text-neutral-600 hover:border-neutral-400 disabled:opacity-50"
                >
                  {p.label}
                </button>
              ))}
            </div>
          )}

          <div className="flex gap-2">
            <select
              value={llmProvider}
              onChange={(e) => handleLlmProviderChange(e.target.value)}
              disabled={!!presentationId}
              className="flex-1 rounded-md border border-neutral-200 bg-white p-2 text-xs disabled:opacity-50"
            >
              {providers?.llm.map((p) => (
                <option key={p.name} value={p.name} disabled={!p.configured}>
                  {p.label}
                  {!p.configured ? " (no key)" : ""}
                </option>
              ))}
            </select>
            <select
              value={llmModel}
              onChange={(e) => setLlmModel(e.target.value)}
              disabled={!!presentationId}
              className="flex-1 rounded-md border border-neutral-200 bg-white p-2 text-xs disabled:opacity-50"
            >
              {(providers?.llm.find((p) => p.name === llmProvider)?.models ?? []).map((m) => (
                <option key={m.id} value={m.id}>
                  {m.id}
                  {!m.ready ? " (downloads on first use)" : ""}
                </option>
              ))}
            </select>
          </div>
          <select
            value={imageProvider}
            onChange={(e) => setImageProvider(e.target.value)}
            disabled={!!presentationId}
            className="rounded-md border border-neutral-200 bg-white p-2 text-xs disabled:opacity-50"
          >
            {providers?.image.map((p) => (
              <option key={p.name} value={p.name} disabled={!p.configured}>
                {p.label} (images){!p.configured ? " (no key)" : ""}
              </option>
            ))}
          </select>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder={
              presentationId
                ? "Make this more premium…"
                : "Create a 12-slide pitch deck for an AI healthcare startup targeting investors..."
            }
            className="h-24 resize-none rounded-md border border-neutral-200 p-3 text-sm outline-none focus:border-neutral-400"
          />
          <button
            onClick={() => handleSubmit()}
            disabled={isBusy}
            className="rounded-md bg-neutral-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {isBusy ? "Working…" : presentationId ? "Send" : "Generate presentation"}
          </button>
        </div>
      </aside>
    </div>
  );
}

export default function Home() {
  return (
    <Suspense fallback={null}>
      <PresentationApp />
    </Suspense>
  );
}
