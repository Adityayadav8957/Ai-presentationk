import { notFound } from "next/navigation";

import { SlideRenderer } from "@/components/slides/SlideRenderer";
import { getPresentation } from "@/lib/api";
import type { SlideContent, Theme } from "@/lib/slide-schema";

type Slide = { id: string; content: SlideContent };

export default async function RenderSlidePage({
  params,
}: {
  params: Promise<{ presentationId: string; slideId: string }>;
}) {
  const { presentationId, slideId } = await params;
  const data = await getPresentation(presentationId);
  const slide = (data.slides as Slide[] | undefined)?.find((s) => s.id === slideId);

  if (!slide) notFound();

  const theme = data.presentation?.theme as Theme | undefined;

  return <SlideRenderer content={slide.content} theme={theme} />;
}
