import { computeLayout } from "@/lib/layout-engine";
import type { SlideContent, Theme } from "@/lib/slide-schema";
import { SlideElementView } from "./Elements";

export function SlideRenderer({
  content,
  theme,
}: {
  content: SlideContent;
  theme?: Theme;
}) {
  const layout = computeLayout(content);
  const primary = layout.placements.filter((p) => p.region === "primary");
  const secondary = layout.placements.filter((p) => p.region === "secondary");

  return (
    <div
      className="flex aspect-video w-full flex-col justify-center gap-6 p-12"
      style={{
        backgroundColor: theme?.background ?? "#ffffff",
        color: theme?.primary ?? "#171717",
        fontFamily: theme?.font ?? "inherit",
      }}
    >
      {layout.title && <h1 className="text-4xl font-bold">{layout.title}</h1>}
      <div className="grid grid-cols-3 gap-8">
        <div className="col-span-2 flex flex-col gap-4">
          {primary.map((p, i) => (
            <SlideElementView key={i} element={p.element} accent={theme?.accent} />
          ))}
        </div>
        <div className="flex flex-col gap-4">
          {secondary.map((p, i) => (
            <SlideElementView key={i} element={p.element} accent={theme?.accent} />
          ))}
        </div>
      </div>
    </div>
  );
}
