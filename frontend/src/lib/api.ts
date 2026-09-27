const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type CreatePresentationResponse = {
  presentation_id: string;
  job_id: string;
};

export type JobStatus = {
  id: string;
  status: string;
  step: string;
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
