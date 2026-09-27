"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { type PresentationSummary, listPresentations, retryPresentation } from "@/lib/api";

const STATUS_STYLES: Record<string, string> = {
  ready: "bg-green-100 text-green-700",
  draft: "bg-amber-100 text-amber-700",
  failed: "bg-red-100 text-red-700",
  cancelled: "bg-neutral-200 text-neutral-600",
};

export default function DecksPage() {
  const [decks, setDecks] = useState<PresentationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [retrying, setRetrying] = useState<string | null>(null);

  useEffect(() => {
    listPresentations()
      .then((data) => setDecks(data.slice().reverse()))
      .finally(() => setLoading(false));
  }, []);

  async function handleRetry(id: string) {
    setRetrying(id);
    try {
      const { presentation_id } = await retryPresentation(id);
      window.location.href = `/?id=${presentation_id}`;
    } finally {
      setRetrying(null);
    }
  }

  return (
    <div className="mx-auto max-w-3xl p-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-neutral-900">Your decks</h1>
        <Link href="/" className="text-sm text-neutral-500 hover:text-neutral-900 hover:underline">
          + New presentation
        </Link>
      </div>

      {loading ? (
        <p className="text-sm text-neutral-400">Loading…</p>
      ) : decks.length === 0 ? (
        <p className="text-sm text-neutral-400">No decks yet — create one to see it here.</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {decks.map((d) => (
            <li
              key={d.id}
              className="flex items-center justify-between rounded-md border border-neutral-200 bg-white p-4"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-neutral-900">{d.title}</p>
                <div className="mt-1 flex items-center gap-2">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs ${STATUS_STYLES[d.status] ?? "bg-neutral-100 text-neutral-600"}`}
                  >
                    {d.status}
                  </span>
                  <span className="text-xs text-neutral-400">
                    {new Date(d.created_at).toLocaleString()}
                  </span>
                </div>
              </div>
              <div className="flex shrink-0 gap-2">
                <Link
                  href={`/?id=${d.id}`}
                  className="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-700 hover:border-neutral-400"
                >
                  Open
                </Link>
                <button
                  onClick={() => handleRetry(d.id)}
                  disabled={retrying === d.id}
                  className="rounded-md bg-neutral-900 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"
                >
                  {retrying === d.id ? "Retrying…" : "Retry"}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
