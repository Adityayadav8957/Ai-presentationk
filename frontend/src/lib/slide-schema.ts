export type SlideElement =
  | { type: "heading"; text: string }
  | { type: "text"; text: string }
  | { type: "stat"; value: string; label: string }
  | { type: "chart"; chartType: "line" | "bar" | "donut"; data: unknown[] }
  | { type: "image"; prompt: string; url?: string }
  | { type: "insight"; text: string };

export type SlideContent = {
  type:
    | "hero"
    | "data_story"
    | "comparison"
    | "timeline"
    | "process"
    | "split"
    | "grid";
  title?: string;
  elements: SlideElement[];
};
