import type { DocumentFocusAreas } from "./focusAreasTypes";
import { getActiveFocusArea } from "./getActiveFocusArea";

export function startFocusAreaTimer(lastTick: number, documentFocusAreas: DocumentFocusAreas) {

  lastTick = performance.now();

  // return a disposer. The old interval survived every solver navigation
  // and retained the entire parsed paper tree for the rest of the session.
  const intervalId = window.setInterval(() => {
    const active = getActiveFocusArea(documentFocusAreas);
    const now = performance.now();

    const deltaSeconds = (now - lastTick) / 1000;

    if (active) {
      active.time += deltaSeconds;
    }

    lastTick = now;
  }, 1000);

  return () => window.clearInterval(intervalId);
}
