import type { EventLogs } from "@/lib/utils/utilsTypes";

export function addEventLog(eventLogs: EventLogs, elementType: string, actionType: string, question: number, option: number | undefined) {
  const dateNow = new Date();
  const performanceTimestamp = performance.now();
  const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

  eventLogs.push({
    dateTimestamp: dateNow.toISOString(),
    performanceTimestamp: performanceTimestamp,
    timezone: userTimezone,
    elementType: elementType,
    actionType: actionType,
    question: question,
    option: option
  });
}