const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type ThemeOption = {
  id: string;
  label: string;
  primary: string;
  accent: string;
  background: string;
  font: string;
};

export type Question = {
  id: string;
  text: string;
  type?: "theme_picker";
  suggested?: string;
  options?: (string | ThemeOption)[];
};

export type CreatePresentationResponse =
  | { presentation_id: string; job_id: string }
  | { presentation_id: string; needs_input: true; questions: Question[] };

export type JobStatus = {
  id: string;
  status: string;
  step: string;
  error?: string | null;
};

export async function createPresentation(brief: Record<string, unknown>) {
  const response = await fetch(`${API_URL}/presentations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(brief),
  });
  if (!response.ok) throw new Error("Failed to create presentation");
  return (await response.json()) as CreatePresentationResponse;
}

export async function answerQuestions(presentationId: string, answers: Record<string, string>) {
  const response = await fetch(`${API_URL}/presentations/${presentationId}/answer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answers }),
  });
  if (!response.ok) throw new Error("Failed to submit answers");
  return (await response.json()) as { job_id: string };
}

export async function getJobStatus(presentationId: string) {
  const response = await fetch(`${API_URL}/presentations/${presentationId}/status`, {
    cache: "no-store",
  });
  if (!response.ok) throw new Error("Failed to fetch job status");
  return (await response.json()) as JobStatus;
}

export async function getPresentation(presentationId: string) {
  const response = await fetch(`${API_URL}/presentations/${presentationId}`, {
    cache: "no-store",
  });
  if (!response.ok) throw new Error("Failed to fetch presentation");
  return response.json();
}

export type PresentationSummary = {
  id: string;
  title: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export async function listPresentations() {
  const response = await fetch(`${API_URL}/presentations`, { cache: "no-store" });
  if (!response.ok) throw new Error("Failed to list presentations");
  return (await response.json()) as PresentationSummary[];
}

export async function cancelGeneration(presentationId: string) {
  const response = await fetch(`${API_URL}/presentations/${presentationId}/cancel`, {
    method: "POST",
  });
  if (!response.ok) throw new Error("Failed to cancel generation");
  return (await response.json()) as { status: string };
}

export async function retryPresentation(presentationId: string) {
  const response = await fetch(`${API_URL}/presentations/${presentationId}/retry`, {
    method: "POST",
  });
  if (!response.ok) throw new Error("Failed to retry presentation");
  return (await response.json()) as CreatePresentationResponse;
}

export async function addSlide(presentationId: string, description: string, position?: number) {
  const response = await fetch(`${API_URL}/presentations/${presentationId}/slides`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ description, position }),
  });
  if (!response.ok) throw new Error("Failed to add slide");
  return (await response.json()) as { slide_id: string };
}

export async function deleteSlide(presentationId: string, slideId: string) {
  const response = await fetch(`${API_URL}/presentations/${presentationId}/slides/${slideId}`, {
    method: "DELETE",
  });
  if (!response.ok) throw new Error("Failed to delete slide");
  return (await response.json()) as { status: string };
}

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
};

export async function sendChatMessage(presentationId: string, content: string) {
  const response = await fetch(`${API_URL}/presentations/${presentationId}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
  if (!response.ok) throw new Error("Failed to send message");
  return (await response.json()) as { job_id: string };
}

export async function getMessages(presentationId: string) {
  const response = await fetch(`${API_URL}/presentations/${presentationId}/chat`, {
    cache: "no-store",
  });
  if (!response.ok) throw new Error("Failed to fetch messages");
  return (await response.json()) as ChatMessage[];
}

export type ModelOption = {
  id: string;
  ready: boolean;
};

export type ProviderOption = {
  name: string;
  label: string;
  configured: boolean;
  models?: ModelOption[];
};

export type ProvidersResponse = {
  llm: ProviderOption[];
  image: ProviderOption[];
  defaults: { llm: string; image: string };
};

export async function getProviders() {
  const response = await fetch(`${API_URL}/providers`, { cache: "no-store" });
  if (!response.ok) throw new Error("Failed to fetch providers");
  return (await response.json()) as ProvidersResponse;
}
