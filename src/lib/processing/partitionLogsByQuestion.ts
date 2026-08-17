import type { EventLogs } from "../utils/utilsTypes";

export function partitionLogsByQuestion(eventLogs: EventLogs) {
  const map = new Map<number, EventLogs>();
  for (const ev of eventLogs) {
    const q = ev.question ?? -1;
    if (!map.has(q)) map.set(q, []);
    map.get(q)!.push(ev);
  }
  return map;
}