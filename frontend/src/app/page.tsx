"use client";

import { useEffect, useRef, useState } from "react";

import { SlideRenderer } from "@/components/slides/SlideRenderer";
import { createPresentation, getJobStatus, getPresentation } from "@/lib/api";
import type { SlideContent } from "@/lib/slide-schema";

type Slide = { id: string; content: SlideContent };

const PIPELINE_STEPS = [
  "understanding",
  "researching",
  "story_building",
  "slide_planning",
  "designing",
  "rendering",
  "qa",
  "final",
];

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const [presentationId, setPresentationId] = useState<string | null>(null);
  const [step, setStep] = useState<string | null>(null);
  const [slides, setSlides] = useState<Slide[]>([]);
  const [activeSlide, setActiveSlide] = useState(0);
  const [isGenerating, setIsGenerating] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  async function handleGenerate() {
    if (!prompt.trim()) return;
    setIsGenerating(true);
    setSlides([]);
    const { presentation_id } = await createPresentation({ topic: prompt });
    setPresentationId(presentation_id);

    pollRef.current = setInterval(async () => {
      const job = await getJobStatus(presentation_id);
      setStep(job?.step ?? null);

      if (job?.status === "done") {
        if (pollRef.current) clearInterval(pollRef.current);
        const data = await getPresentation(presentation_id);
        setSlides(data.slides ?? []);
        setIsGenerating(false);
      }
    }, 2000);
  }

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  return (
    <div className="grid h-screen grid-cols-[220px_1fr_320px] bg-neutral-50 text-neutral-900">
      <aside className="border-r border-neutral-200 p-4">
        <h2 className="mb-4 text-sm font-medium text-neutral-500">Slides</h2>
        <ul className="flex flex-col gap-2">
          {slides.map((slide, i) => (
            <li key={slide.id}>
              <button
                onClick={() => setActiveSlide(i)}
                className={`w-full rounded-md border px-3 py-2 text-left text-sm ${
                  i === activeSlide
                    ? "border-neutral-900 bg-neutral-900 text-white"
                    : "border-neutral-200 bg-white"
                }`}
              >
                {String(i + 1).padStart(2, "0")}
              </button>
            </li>
          ))}
        </ul>
      </aside>

      <main className="flex items-center justify-center overflow-auto p-8">
        {slides.length > 0 ? (
          <div className="w-full max-w-4xl shadow-lg">
            <SlideRenderer content={slides[activeSlide].content} />
          </div>
        ) : (
          <div className="text-center text-neutral-400">
            {isGenerating ? (
              <div className="flex flex-col gap-2">
                <span className="text-sm">Generating your presentation…</span>
                <span className="text-xs">
                  {PIPELINE_STEPS.map((s) => (s === step ? `[${s}]` : s)).join(" → ")}
                </span>
              </div>
            ) : (
              <span className="text-sm">No presentation yet — describe one on the right.</span>
            )}
          </div>
        )}
      </main>

      <aside className="flex flex-col border-l border-neutral-200 p-4">
        <h2 className="mb-4 text-sm font-medium text-neutral-500">AI Assistant</h2>
        <div className="flex flex-1 flex-col justify-end gap-3">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Create a 12-slide pitch deck for an AI healthcare startup targeting investors..."
            className="h-32 resize-none rounded-md border border-neutral-200 p-3 text-sm outline-none focus:border-neutral-400"
          />
          <button
            onClick={handleGenerate}
            disabled={isGenerating}
            className="rounded-md bg-neutral-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {isGenerating ? "Generating…" : "Generate presentation"}
          </button>
        </div>
      </aside>
    </div>
  );
}
