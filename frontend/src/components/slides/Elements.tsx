import type { SlideElement } from "@/lib/slide-schema";

export function SlideElementView({
  element,
  accent,
}: {
  element: SlideElement;
  accent?: string;
}) {
  switch (element.type) {
    case "heading":
      return <h2 className="text-3xl font-semibold tracking-tight">{element.text}</h2>;
    case "text":
      return <p className="text-base leading-relaxed text-neutral-600">{element.text}</p>;
    case "stat":
      return (
        <div className="flex flex-col">
          <span className="text-4xl font-bold" style={{ color: accent }}>
            {element.value}
          </span>
          <span className="text-sm text-neutral-500">{element.label}</span>
        </div>
      );
    case "insight":
      return (
        <p className="text-lg font-medium italic" style={{ color: accent }}>
          {element.text}
        </p>
      );
    case "chart":
      return (
        <div className="flex h-48 w-full items-center justify-center rounded-lg border border-dashed border-neutral-300 text-sm text-neutral-400">
          {element.chartType} chart placeholder
        </div>
      );
    case "image":
      return (
        <div className="flex h-48 w-full items-center justify-center overflow-hidden rounded-lg bg-neutral-100 text-sm text-neutral-400">
          {element.url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={element.url}
              alt={element.prompt}
              className="h-full w-full object-cover"
            />
          ) : (
            `image: ${element.prompt}`
          )}
        </div>
      );
    default:
      return null;
  }
}
