import type { DocumentFocusAreas } from "./focusAreasTypes";

export function getActiveFocusArea(documentFocusAreas: DocumentFocusAreas) {
  for (const page of documentFocusAreas) {
    for (const f of page) {
      if (f.active) return f;
    }
  }
  return undefined;
}