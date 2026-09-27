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
  if (content.html) {
    // Defensive fallback: some models emit var(--accent) etc. despite being
    // told to use literal values — define them anyway so it still renders
    // correctly instead of falling back to browser defaults.
    const doc = `<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<style>
  :root {
    --primary: ${theme?.primary ?? "#171717"};
    --accent: ${theme?.accent ?? "#2563eb"};
    --background: ${theme?.background ?? "#ffffff"};
    --font: ${theme?.font ?? "inherit"};
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; background: var(--background); font-family: var(--font); }
</style>
</head>
<body>${content.html}</body>
</html>`;

    return (
      <iframe
        srcDoc={doc}
        title={content.title ?? "Slide"}
        // Empty sandbox = render-only: no script execution, no same-origin
        // access. The HTML is AI-authored from our own agent, but we still
        // treat it as untrusted content rather than injecting it into the DOM.
        sandbox=""
        className="aspect-video w-full border-0"
      />
    );
  }

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
