"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

import Link from "next/link";

import { SlideRenderer } from "@/components/slides/SlideRenderer";
import {
  type ChatMessage,
  type ProvidersResponse,
  type Question,
  type ThemeOption,
  addSlide,
  answerQuestions,
  cancelGeneration,
  createPresentation,
  deleteSlide,
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
  rendering_html: "Designing each slide",
  rendering_slides: "Generating each slide",
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

function SlideSkeleton() {
  return (
    <div className="flex aspect-video w-full flex-col gap-4 rounded-md bg-white p-10">
      <div className="h-8 w-2/3 animate-shimmer rounded-md" />
      <div className="h-4 w-1/3 animate-shimmer rounded-md" />
      <div className="mt-4 grid flex-1 grid-cols-3 gap-6">
        <div className="col-span-2 flex flex-col gap-3">
          <div className="h-4 w-full animate-shimmer rounded" />
          <div className="h-4 w-5/6 animate-shimmer rounded" />
          <div className="mt-2 h-full w-full animate-shimmer rounded-lg" />
        </div>
        <div className="flex flex-col gap-3">
          <div className="h-20 w-full animate-shimmer rounded-lg" />
          <div className="h-20 w-full animate-shimmer rounded-lg" />
        </div>
      </div>
      <div className="flex items-center justify-center gap-2 pt-2 text-xs text-neutral-400">
        <span className="h-2 w-2 animate-pulse rounded-full bg-blue-400" />
        Designing this slide…
      </div>
    </div>
  );
}

function QuestionPanel({
  questions,
  onSubmit,
}: {
  questions: Question[];
  onSubmit: (answers: Record<string, string>) => void;
}) {
  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(questions.map((q) => [q.id, q.suggested ?? ""])),
  );
  const canSubmit = questions.every((q) => values[q.id]);

  return (
    <div className="w-full max-w-2xl rounded-lg border border-neutral-200 bg-white p-6 shadow-sm">
      <h2 className="mb-1 text-base font-semibold text-neutral-900">Quick question before we continue</h2>
      <p className="mb-5 text-xs text-neutral-400">This only happens because guided mode is on.</p>
      <div className="flex flex-col gap-6">
        {questions.map((q) => (
          <div key={q.id}>
            <p className="mb-2 text-sm font-medium text-neutral-700">{q.text}</p>
            {q.type === "theme_picker" ? (
              <div className="grid grid-cols-5 gap-3">
                {(q.options as ThemeOption[] | undefined)?.map((opt) => (
                  <button
                    key={opt.id}
                    onClick={() => setValues((v) => ({ ...v, [q.id]: opt.id }))}
                    className={`rounded-lg border-2 p-2 text-left transition ${
                      values[q.id] === opt.id ? "border-neutral-900" : "border-neutral-200 hover:border-neutral-400"
                    }`}
                  >
                    <div className="mb-2 flex h-10 overflow-hidden rounded">
                      <div className="flex-1" style={{ background: opt.background }} />
                      <div className="flex-1" style={{ background: opt.primary }} />
                      <div className="flex-1" style={{ background: opt.accent }} />
                    </div>
                    <span className="text-[11px] font-medium text-neutral-700">{opt.label}</span>
                  </button>
                ))}
              </div>
            ) : q.options && q.options.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {(q.options as string[]).map((opt) => (
                  <button
                    key={opt}
                    onClick={() => setValues((v) => ({ ...v, [q.id]: opt }))}
                    className={`rounded-full border px-3 py-1.5 text-xs ${
                      values[q.id] === opt
                        ? "border-neutral-900 bg-neutral-900 text-white"
                        : "border-neutral-200 bg-white text-neutral-600 hover:border-neutral-400"
                    }`}
                  >
                    {opt}
                  </button>
                ))}
              </div>
            ) : (
              <input
                type="text"
                value={values[q.id] ?? ""}
                onChange={(e) => setValues((v) => ({ ...v, [q.id]: e.target.value }))}
                placeholder="Type your answer…"
                className="w-full rounded-md border border-neutral-200 px-3 py-2 text-sm outline-none focus:border-neutral-400"
              />
            )}
          </div>
        ))}
      </div>
      <button
        onClick={() => onSubmit(values)}
        disabled={!canSubmit}
        className="mt-6 rounded-md bg-neutral-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
      >
        Continue
      </button>
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
  const [cancelled, setCancelled] = useState(false);
  const [providers, setProviders] = useState<ProvidersResponse | null>(null);
  const [llmProvider, setLlmProvider] = useState("");
  const [llmModel, setLlmModel] = useState("");
  const [imageProvider, setImageProvider] = useState("");
  const [qaEnabled, setQaEnabled] = useState(false);
  const [guidedMode, setGuidedMode] = useState(false);
  const [pendingQuestions, setPendingQuestions] = useState<Question[] | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [addingSlideOpen, setAddingSlideOpen] = useState(false);
  const [newSlideText, setNewSlideText] = useState("");
  const [renderingSlideIds, setRenderingSlideIds] = useState<Set<string>>(new Set());
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const addSlidePollRef = useRef<ReturnType<typeof setInterval> | null>(null);

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
      } else if (job?.status === "waiting_for_input") {
        // pendingQuestions was already populated by refreshPresentation above.
        setIsBusy(false);
      } else if (job?.status === "cancelled") {
        setCancelled(true);
        setIsBusy(false);
      } else if (job?.status === "failed") {
        // Slides were already fetched above — a failed job (e.g. a stalled
        // QA step) doesn't mean the content itself is gone.
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
          async (message) => {
            await Promise.all([refreshPresentation(id), refreshMessages(id)]);
            setError(message);
            setIsBusy(false);
          },
          () => {
            setCancelled(true);
            setIsBusy(false);
          },
        );
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Left/right arrow keys move between slides, unless the user is typing.
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      const tag = (document.activeElement?.tagName ?? "").toLowerCase();
      if (tag === "input" || tag === "textarea" || pendingQuestions) return;
      if (e.key === "ArrowRight") setActiveSlide((i) => Math.min(i + 1, slides.length - 1));
      if (e.key === "ArrowLeft") setActiveSlide((i) => Math.max(i - 1, 0));
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [slides.length, pendingQuestions]);

  function handleLlmProviderChange(name: string) {
    setLlmProvider(name);
    setLlmModel(providers?.llm.find((p) => p.name === name)?.models?.[0]?.id ?? "");
  }

  async function refreshPresentation(id: string) {
    const data = await getPresentation(id);
    setSlides(data.slides ?? []);
    setTheme(data.presentation?.theme);
    setPendingQuestions(data.presentation?.pending_questions?.questions ?? null);
    return data;
  }

  async function refreshMessages(id: string) {
    const msgs = await getMessages(id);
    setMessages(msgs);
  }

  function pollUntilDone(
    id: string,
    onDone: () => void,
    onFail: (message: string) => void,
    onCancel: () => void,
  ) {
    pollRef.current = setInterval(async () => {
      // Slides are checkpointed to the database one at a time as each
      // finishes rendering — refetch every tick (not just at the end) so
      // they appear on screen progressively instead of all at once.
      await refreshPresentation(id);
      const job = await getJobStatus(id);
      setStep(job?.step ?? null);
      if (job?.status === "done") {
        if (pollRef.current) clearInterval(pollRef.current);
        onDone();
      } else if (job?.status === "waiting_for_input") {
        // pendingQuestions was already populated by refreshPresentation above.
        if (pollRef.current) clearInterval(pollRef.current);
        setIsBusy(false);
      } else if (job?.status === "cancelled") {
        if (pollRef.current) clearInterval(pollRef.current);
        onCancel();
      } else if (job?.status === "failed") {
        if (pollRef.current) clearInterval(pollRef.current);
        onFail(job.error ?? "Generation failed for an unknown reason.");
      }
    }, 2000);
  }

  async function handleCancel() {
    if (!presentationId) return;
    if (pollRef.current) clearInterval(pollRef.current);
    setIsBusy(false);
    setCancelled(true);
    await cancelGeneration(presentationId);
  }

  function handleNewPresentation() {
    if (pollRef.current) clearInterval(pollRef.current);
    if (addSlidePollRef.current) clearInterval(addSlidePollRef.current);
    setPresentationId(null);
    setSlides([]);
    setMessages([]);
    setActiveSlide(0);
    setIsBusy(false);
    setError(null);
    setCancelled(false);
    setPendingQuestions(null);
    setPrompt("");
    setRenderingSlideIds(new Set());
    setAddingSlideOpen(false);
    router.replace("/");
  }

  async function handleSubmit(presetPrompt?: string) {
    const currentPrompt = presetPrompt ?? prompt;
    if (!currentPrompt.trim() || isBusy || pendingQuestions) return;
    setPrompt("");
    setIsBusy(true);
    setError(null);
    setCancelled(false);

    setMessages((prev) => [
      ...prev,
      { id: `local-${Date.now()}`, role: "user", content: currentPrompt, created_at: "" },
    ]);

    if (!presentationId) {
      const resp = await createPresentation({
        topic: currentPrompt,
        llm_provider: llmProvider || undefined,
        llm_model: llmModel || undefined,
        image_provider: imageProvider || undefined,
        qa_enabled: qaEnabled,
        guided_mode: guidedMode,
      });
      const presentation_id = resp.presentation_id;
      setPresentationId(presentation_id);
      setSettingsOpen(false);
      router.replace(`/?id=${presentation_id}`);

      if ("needs_input" in resp && resp.needs_input) {
        setPendingQuestions(resp.questions);
        setIsBusy(false);
        return;
      }

      pollUntilDone(
        presentation_id,
        async () => {
          await refreshPresentation(presentation_id);
          setIsBusy(false);
        },
        async (message) => {
          await refreshPresentation(presentation_id);
          setError(message);
          setIsBusy(false);
        },
        () => {
          setCancelled(true);
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
      async (message) => {
        await Promise.all([refreshPresentation(presentationId), refreshMessages(presentationId)]);
        setError(message);
        setIsBusy(false);
      },
      () => {
        setCancelled(true);
        setIsBusy(false);
      },
    );
  }

  async function handleAnswerSubmit(answers: Record<string, string>) {
    if (!presentationId) return;
    setPendingQuestions(null);
    setIsBusy(true);
    setError(null);
    await answerQuestions(presentationId, answers);
    pollUntilDone(
      presentationId,
      async () => {
        await Promise.all([refreshPresentation(presentationId), refreshMessages(presentationId)]);
        setIsBusy(false);
      },
      async (message) => {
        await Promise.all([refreshPresentation(presentationId), refreshMessages(presentationId)]);
        setError(message);
        setIsBusy(false);
      },
      () => {
        setCancelled(true);
        setIsBusy(false);
      },
    );
  }

  async function handleAddSlide() {
    const description = newSlideText.trim();
    if (!presentationId || !description) return;
    setAddingSlideOpen(false);
    setNewSlideText("");

    const { slide_id } = await addSlide(presentationId, description);
    setRenderingSlideIds((prev) => new Set(prev).add(slide_id));
    await refreshPresentation(presentationId);
    setActiveSlide(slides.length); // jump toward the new (appended) slide

    let attempts = 0;
    if (addSlidePollRef.current) clearInterval(addSlidePollRef.current);
    addSlidePollRef.current = setInterval(async () => {
      attempts += 1;
      const data = await refreshPresentation(presentationId);
      const newSlide = (data.slides ?? []).find((s: Slide) => s.id === slide_id);
      if (newSlide?.content?.html || attempts > 30) {
        if (addSlidePollRef.current) clearInterval(addSlidePollRef.current);
        setRenderingSlideIds((prev) => {
          const next = new Set(prev);
          next.delete(slide_id);
          return next;
        });
      }
    }, 2000);
  }

  async function handleDeleteSlide(slideId: string) {
    if (!presentationId) return;
    await deleteSlide(presentationId, slideId);
    const data = await refreshPresentation(presentationId);
    const count = data.slides?.length ?? 0;
    setActiveSlide((prev) => Math.max(0, Math.min(prev, count - 1)));
  }

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
      if (addSlidePollRef.current) clearInterval(addSlidePollRef.current);
    };
  }, []);

  const active = slides[activeSlide];
  const isSlideRendering = (s: Slide) => (isBusy || renderingSlideIds.has(s.id)) && !s.content.html;
  const canManageSlides = !!presentationId && !isBusy;

  return (
    <div className="flex h-screen flex-col bg-neutral-50 text-neutral-900">
      <header className="flex h-14 flex-none items-center justify-between border-b border-neutral-200 bg-white px-5">
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-neutral-900 text-xs font-bold text-white">
            P
          </div>
          <span className="text-sm font-semibold text-neutral-900">Presentation Studio</span>
        </div>
        <div className="flex items-center gap-4">
          <Link href="/decks" className="text-sm text-neutral-500 hover:text-neutral-900">
            My decks
          </Link>
          <button
            onClick={handleNewPresentation}
            className="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-700 hover:border-neutral-400"
          >
            + New presentation
          </button>
        </div>
      </header>

      <div className="grid flex-1 grid-cols-[240px_1fr_360px] overflow-hidden">
        <aside className="flex flex-col overflow-y-auto border-r border-neutral-200 bg-white p-4">
          <h2 className="mb-3 text-sm font-medium text-neutral-500">
            Slides{slides.length > 0 ? ` (${slides.length})` : ""}
          </h2>
          <ul className="flex flex-col gap-2">
            {slides.map((slide, i) => {
              const rendering = isSlideRendering(slide);
              return (
                <li key={slide.id} className="group relative">
                  <button
                    onClick={() => setActiveSlide(i)}
                    className={`relative w-full rounded-md border px-3 py-2 text-left text-sm ${
                      i === activeSlide
                        ? "border-neutral-900 bg-neutral-900 text-white"
                        : "border-neutral-200 bg-white hover:border-neutral-300"
                    } ${rendering ? "opacity-60" : ""}`}
                  >
                    {String(i + 1).padStart(2, "0")}
                    {rendering && (
                      <>
                        <span className="absolute right-2 top-2 h-2 w-2 animate-pulse rounded-full bg-blue-400" />
                        <span className="absolute inset-x-2 bottom-1 h-0.5 animate-shimmer rounded-full" />
                      </>
                    )}
                    {slide.qa_report?.issues && slide.qa_report.issues.length > 0 && (
                      <span
                        title={slide.qa_report.issues.join("; ")}
                        className="absolute right-2 top-2 h-2 w-2 rounded-full bg-amber-500"
                      />
                    )}
                  </button>
                  {canManageSlides && !rendering && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteSlide(slide.id);
                      }}
                      title="Delete slide"
                      className="absolute -right-1.5 -top-1.5 hidden h-5 w-5 items-center justify-center rounded-full bg-neutral-900 text-[10px] text-white hover:bg-red-600 group-hover:flex"
                    >
                      ×
                    </button>
                  )}
                </li>
              );
            })}
          </ul>

          {canManageSlides &&
            (addingSlideOpen ? (
              <div className="mt-3 flex flex-col gap-2">
                <textarea
                  value={newSlideText}
                  onChange={(e) => setNewSlideText(e.target.value)}
                  placeholder="Describe the new slide…"
                  autoFocus
                  className="h-16 resize-none rounded-md border border-neutral-200 p-2 text-xs outline-none focus:border-neutral-400"
                />
                <div className="flex gap-2">
                  <button
                    onClick={() => {
                      setAddingSlideOpen(false);
                      setNewSlideText("");
                    }}
                    className="flex-1 rounded-md border border-neutral-200 px-2 py-1.5 text-xs text-neutral-500 hover:border-neutral-400"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleAddSlide}
                    disabled={!newSlideText.trim()}
                    className="flex-1 rounded-md bg-neutral-900 px-2 py-1.5 text-xs font-medium text-white disabled:opacity-40"
                  >
                    Add
                  </button>
                </div>
              </div>
            ) : (
              <button
                onClick={() => setAddingSlideOpen(true)}
                className="mt-3 flex items-center justify-center gap-1.5 rounded-md border border-dashed border-neutral-300 py-2 text-xs font-medium text-neutral-500 hover:border-neutral-400 hover:text-neutral-700"
              >
                + Add slide
              </button>
            ))}
        </aside>

        <main className="flex flex-col items-center justify-center overflow-auto bg-neutral-100 p-8">
          {pendingQuestions ? (
            <QuestionPanel questions={pendingQuestions} onSubmit={handleAnswerSubmit} />
          ) : active ? (
            <div className="w-full max-w-4xl">
              {isBusy && (
                <div className="mb-3 flex items-center gap-3 rounded-md border border-blue-200 bg-blue-50 px-3 py-2 text-xs text-blue-800">
                  <span className="h-2 w-2 flex-none animate-pulse rounded-full bg-blue-500" />
                  <span className="flex-1">
                    {stepLabel(step)} — {slides.filter((s) => s.content.html).length} of {slides.length} slides ready
                  </span>
                  <div className="h-1.5 w-20 flex-none overflow-hidden rounded-full bg-blue-200">
                    <div
                      className="h-full rounded-full bg-blue-500 transition-all duration-500"
                      style={{
                        width: `${
                          slides.length
                            ? (slides.filter((s) => s.content.html).length / slides.length) * 100
                            : 0
                        }%`,
                      }}
                    />
                  </div>
                </div>
              )}
              {error && (
                <div className="mb-3 rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
                  <span className="font-medium">Note: </span>
                  {error}
                </div>
              )}
              <div className="shadow-lg ring-1 ring-black/5">
                {isSlideRendering(active) ? (
                  <SlideSkeleton />
                ) : (
                  <SlideRenderer content={active.content} theme={theme} />
                )}
              </div>
              <div className="mt-4 flex items-center justify-center gap-3">
                <button
                  onClick={() => setActiveSlide((i) => Math.max(0, i - 1))}
                  disabled={activeSlide === 0}
                  className="flex h-7 w-7 items-center justify-center rounded-md border border-neutral-200 bg-white text-neutral-500 hover:border-neutral-400 disabled:opacity-30"
                >
                  ‹
                </button>
                <span className="text-xs text-neutral-400">
                  {activeSlide + 1} / {slides.length}
                </span>
                <button
                  onClick={() => setActiveSlide((i) => Math.min(slides.length - 1, i + 1))}
                  disabled={activeSlide === slides.length - 1}
                  className="flex h-7 w-7 items-center justify-center rounded-md border border-neutral-200 bg-white text-neutral-500 hover:border-neutral-400 disabled:opacity-30"
                >
                  ›
                </button>
              </div>
            </div>
          ) : error ? (
            <div className="max-w-md rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              <p className="font-medium">Generation failed</p>
              <p className="mt-1 text-xs">{error}</p>
            </div>
          ) : cancelled ? (
            <div className="max-w-md rounded-md border border-neutral-200 bg-white p-4 text-sm text-neutral-600">
              <p className="font-medium">Generation cancelled</p>
              <p className="mt-1 text-xs">You stopped this before it finished.</p>
            </div>
          ) : isBusy ? (
            <div className="flex flex-col items-center gap-6">
              <Loader label={stepLabel(step)} />
              <button
                onClick={handleCancel}
                className="rounded-md border border-neutral-300 bg-white px-4 py-1.5 text-xs font-medium text-neutral-600 hover:border-neutral-400 hover:text-neutral-900"
              >
                Stop generating
              </button>
            </div>
          ) : (
            <div className="text-center text-neutral-400">
              <span className="text-sm">No presentation yet — describe one on the right.</span>
            </div>
          )}
        </main>

        <aside className="flex flex-col overflow-y-auto border-l border-neutral-200 bg-white p-4">
          <h2 className="mb-4 text-sm font-medium text-neutral-500">AI Assistant</h2>

          <div className="flex-1 space-y-3 overflow-y-auto">
            {messages.map((m) => (
              <div
                key={m.id}
                className={`rounded-lg px-3 py-2 text-sm leading-relaxed ${
                  m.role === "user" ? "bg-neutral-900 text-white" : "bg-neutral-100 text-neutral-800"
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

            <div className="rounded-md border border-neutral-200">
              <button
                onClick={() => setSettingsOpen((o) => !o)}
                className="flex w-full items-center justify-between px-3 py-2 text-xs font-medium text-neutral-600"
              >
                <span>
                  Settings
                  {!settingsOpen && providers && (
                    <span className="ml-2 font-normal text-neutral-400">
                      {providers.llm.find((p) => p.name === llmProvider)?.label ?? llmProvider}
                    </span>
                  )}
                </span>
                <span className="text-neutral-400">{settingsOpen ? "−" : "+"}</span>
              </button>
              {settingsOpen && (
                <div className="flex flex-col gap-2 border-t border-neutral-100 p-3">
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

                  <label className="flex items-start gap-2 rounded-md border border-neutral-200 p-2.5 text-xs">
                    <input
                      type="checkbox"
                      checked={qaEnabled}
                      onChange={(e) => setQaEnabled(e.target.checked)}
                      disabled={!!presentationId}
                      className="mt-0.5"
                    />
                    <span>
                      <span className="font-medium text-neutral-700">Run visual QA</span>
                      <span className="block text-neutral-400">
                        Screenshots each slide and asks a vision model to check for overflow,
                        overlap, or tiny text. Slower, especially with a local model.
                      </span>
                    </span>
                  </label>

                  <label className="flex items-start gap-2 rounded-md border border-neutral-200 p-2.5 text-xs">
                    <input
                      type="checkbox"
                      checked={guidedMode}
                      onChange={(e) => setGuidedMode(e.target.checked)}
                      disabled={!!presentationId}
                      className="mt-0.5"
                    />
                    <span>
                      <span className="font-medium text-neutral-700">Ask me clarifying questions</span>
                      <span className="block text-neutral-400">
                        Confirms audience/goal if unclear, and lets you pick the design direction
                        before slides are generated.
                      </span>
                    </span>
                  </label>
                </div>
              )}
            </div>

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
            {isBusy ? (
              <button
                onClick={handleCancel}
                className="rounded-md border border-neutral-300 px-4 py-2 text-sm font-medium text-neutral-700 hover:border-neutral-400"
              >
                Stop generating
              </button>
            ) : (
              <button
                onClick={() => handleSubmit()}
                disabled={!!pendingQuestions}
                className="rounded-md bg-neutral-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              >
                {pendingQuestions ? "Answer the question above…" : presentationId ? "Send" : "Generate presentation"}
              </button>
            )}
          </div>
        </aside>
      </div>
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
