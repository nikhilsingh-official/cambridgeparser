import type { ButtonType } from "../buttons";

export type FocusAreaActions = "userHoveredIn" | "userHoveredOutPage" | "userClick";
export type HighlightActions = "deselectedCorrect" | "elimToCorrect" | "setCorrect" | "correctToElim" | "deselectedElim" | "setElim";
export type ButtonActions = "Selection" | "Deselection";

export type EventLogs = Array<{ dateTimestamp: string, performanceTimestamp: number, timezone: string, elementType: ButtonType | "focusArea" | "highlight", actionType: ButtonActions | FocusAreaActions | HighlightActions, question: number, option?: number }>;
export type HighlightMode = "correct" | "eliminated"