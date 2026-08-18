// `stopTimeWatcher` added. renderFocusAreas() creates a Vue `watch` on
// focusArea.time to keep the on-screen timer live, but it runs OUTSIDE any
// component setup scope, so Vue has no owner to stop it for us. Without a
// handle to call, every re-render (i.e. every resize) stacked another watcher
// on the same source, each writing into a DOM node that had been replaced.
export type FocusArea = {
  y: number;
  y2: number;
  active: boolean;
  time: number;
  questionNumber: number;
  el?: HTMLElement;
  stopTimeWatcher?: () => void;
};
export type PageFocusAreas = FocusArea[];
export type DocumentFocusAreas = PageFocusAreas[];