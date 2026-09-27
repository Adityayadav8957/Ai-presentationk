import type { SlideContent, SlideElement } from "./slide-schema";

export type LayoutRegion = "primary" | "secondary";

export type PlacedElement = {
  element: SlideElement;
  region: LayoutRegion;
};

export type SlideLayout = {
  title?: string;
  placements: PlacedElement[];
};

function regionFor(element: SlideElement): LayoutRegion {
  switch (element.type) {
    case "stat":
    case "insight":
      return "secondary";
    default:
      return "primary";
  }
}

/**
 * Converts semantic slide JSON into a geometry-free arrangement (regions,
 * not pixels). Replace this with real constraint-based rules (avoid-overlap,
 * min font size, density limits) as the design agent matures — the AI never
 * outputs coordinates directly, only this function does.
 */
export function computeLayout(content: SlideContent): SlideLayout {
  return {
    title: content.title,
    placements: content.elements.map((element) => ({
      element,
      region: regionFor(element),
    })),
  };
}
