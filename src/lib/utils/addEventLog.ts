import type { EventLogs } from "@/lib/utils/utilsTypes";

// exam-start reference for elapsed_ms. performance.now() alone is ms since
// PAGE LOAD, which is meaningless once the event is stored - enrichAnalytics
// only ever took differences so it never noticed. Set by setEventEpoch() when
// the exam starts.
let eventEpoch: number | null = null;
// monotonic ordinal so stored events keep their order even when two land in
// the same millisecond.
let eventSeq = 0;

// called from MCQNav.startExam(). Resets both counters so a second attempt
// in the same page session starts clean.
export function setEventEpoch(epoch: number) {
  eventEpoch = epoch;
  eventSeq = 0;
}

// the IANA zone is resolved once here rather than per event.
export function currentTimezone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone;
}

export function addEventLog(eventLogs: EventLogs, elementType: string, actionType: string, question: number, option: number | undefined) {
  const dateNow = new Date();
  const performanceTimestamp = performance.now();
  const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

  eventLogs.push({
    dateTimestamp: dateNow.toISOString(),
    performanceTimestamp: performanceTimestamp,
    timezone: userTimezone,
    // pre-existing type error, cast at the boundary - callers legitimately
    // pass plain strings (selectOption.ts looks its action up in a
    // Record<string,string>), so the values are correct at runtime but
    // TypeScript cannot prove it against the literal unions in EventLogs.
    elementType: elementType as EventLogs[number]["elementType"],
    actionType: actionType as EventLogs[number]["actionType"],
    question: question,
    option: option,
    // added for persistence. seq preserves ordering; elapsedMs is measured
    // from exam start so it stays meaningful after the row is written.
    seq: eventSeq++,
    elapsedMs: eventEpoch === null ? 0 : Math.max(0, Math.round(performanceTimestamp - eventEpoch)),
  });
}
