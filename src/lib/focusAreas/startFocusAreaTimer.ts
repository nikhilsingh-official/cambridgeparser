import type { DocumentFocusAreas } from "./focusAreasTypes";
import { getActiveFocusArea } from "./getActiveFocusArea";

export function startFocusAreaTimer(lastTick: number, documentFocusAreas: DocumentFocusAreas) {

  lastTick = performance.now();

  window.setInterval(() => {
    const active = getActiveFocusArea(documentFocusAreas);
    const now = performance.now();

    const deltaSeconds = (now - lastTick) / 1000;

    if (active) {
      active.time += deltaSeconds;
    }

    lastTick = now;
  }, 1000);
}