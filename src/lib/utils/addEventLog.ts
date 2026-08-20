// this module previously exported one stringly-typed addEventLog() taking
// `elementType: string, actionType: string`. Because AttemptEvent is now a
// discriminated union, each event family gets its own constructor: the compiler
// checks that the action belongs to the element that produced it, and that a
// highlight event carries an option while the others do not. The two `as` casts
// that used to be needed here are gone.

import type {
  ButtonEvent,
  EventEnvelope,
  EventLogs,
  FocusAreaEvent,
  HighlightEvent,
} from "@/lib/utils/utilsTypes";
import {
  ButtonAction,
  ButtonKind,
  EventElement,
  FocusAreaAction,
  HighlightAction,
} from "@/lib/types/enums";

// exam-start reference for elapsedMs. performance.now() alone is ms since
// PAGE LOAD, which is meaningless once the event is stored - enrichAnalytics
// only ever took differences so it never noticed.
let eventEpoch: number | null = null;
// monotonic ordinal so stored events keep their order even when two land in
// the same millisecond.
let eventSeq = 0;

/** called from MCQNav.startExam(). Resets both counters for a fresh attempt. */
export function setEventEpoch(epoch: number): void {
  eventEpoch = epoch;
  eventSeq = 0;
}

/** the browser's IANA zone, resolved once per event. */
export function currentTimezone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone;
}

// builds the fields common to every event.
function envelope(): EventEnvelope {
  const performanceTimestamp = performance.now();
  return {
    dateTimestamp: new Date().toISOString(),
    performanceTimestamp,
    timezone: currentTimezone(),
    seq: eventSeq++,
    elapsedMs: eventEpoch === null ? 0 : Math.max(0, Math.round(performanceTimestamp - eventEpoch)),
  };
}

/** record an option state change. `option` is required - see HighlightEvent. */
export function logHighlight(
  eventLogs: EventLogs,
  actionType: HighlightAction,
  question: number,
  option: number,
): void {
  const event: HighlightEvent = {
    ...envelope(),
    elementType: EventElement.Highlight,
    actionType,
    question,
    option,
  };
  eventLogs.push(event);
}

/** record an attention event on a question. Has no option, by construction. */
export function logFocusArea(
  eventLogs: EventLogs,
  actionType: FocusAreaAction,
  question: number,
): void {
  const event: FocusAreaEvent = {
    ...envelope(),
    elementType: EventElement.FocusArea,
    actionType,
    question,
  };
  eventLogs.push(event);
}

/** record a flag button being toggled on or off. */
export function logButton(
  eventLogs: EventLogs,
  elementType: ButtonKind,
  actionType: ButtonAction,
  question: number,
): void {
  const event: ButtonEvent = {
    ...envelope(),
    elementType,
    actionType,
    question,
  };
  eventLogs.push(event);
}

// the original entry point, kept so nothing outside this refactor breaks.
// It dispatches to the typed constructors above and validates the element at
// runtime, since its callers may still pass plain strings.
export function addEventLog(
  eventLogs: EventLogs,
  elementType: string,
  actionType: string,
  question: number,
  option: number | undefined,
): void {
  if (elementType === EventElement.Highlight) {
    logHighlight(eventLogs, actionType as HighlightAction, question, option ?? 0);
    return;
  }
  if (elementType === EventElement.FocusArea) {
    logFocusArea(eventLogs, actionType as FocusAreaAction, question);
    return;
  }
  if (elementType in ButtonKind) {
    logButton(eventLogs, elementType as ButtonKind, actionType as ButtonAction, question);
    return;
  }
  // unreachable for the four families above. Logged rather than thrown so a
  // bad event can never abort an exam in progress.
  console.warn(`addEventLog: unrecognised elementType '${elementType}', event dropped`);
}

// re-exported so callers can reference action values by name rather than
// repeating string literals.
export { ButtonAction, ButtonKind, EventElement, FocusAreaAction, HighlightAction };
