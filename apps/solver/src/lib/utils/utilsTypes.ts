import type { ButtonType } from "../buttons";
// the canonical value lists now live in @/lib/types/enums so they can be
// shared with the persistence layer and referenced by name instead of as bare
// string literals.
import type {
  ButtonAction,
  ButtonKind,
  EventElement,
  FocusAreaAction,
  HighlightAction,
  HighlightMode as HighlightModeEnum,
} from "@/lib/types/enums";

// these three aliases are kept under their original names so the ~8 call
// sites and every existing import keep compiling unchanged. They now derive
// from the enum maps rather than repeating the literals.
export type FocusAreaActions = FocusAreaAction;
export type HighlightActions = HighlightAction;
export type ButtonActions = ButtonAction;

// compile-time assertion that ButtonKind (declared in types/enums.ts) and
// ButtonType (derived from BUTTON_CONFIG in lib/buttons/buttonTypes.ts) stay in
// step. If someone adds a fifth flag button to one and not the other, this line
// fails to compile instead of silently producing events nothing can classify.
type AssertButtonKindsMatch = ButtonKind extends ButtonType
  ? ButtonType extends ButtonKind ? true : never
  : never;
const _buttonKindsMatch: AssertButtonKindsMatch = true;
void _buttonKindsMatch;

/**
 * fields every event carries, whatever produced it.
 *
 * `seq` and `elapsedMs` are what make the stream persistable: seq preserves
 * ordering when two events land in the same millisecond, and elapsedMs is
 * measured from exam start (performance.now() alone is ms since page load,
 * which is meaningless once stored).
 */
export interface EventEnvelope {
  /** ISO-8601 wall-clock time the event occurred. */
  dateTimestamp: string;
  /** Raw performance.now() reading. Kept for backward compatibility. */
  performanceTimestamp: number;
  /** IANA zone of the browser that produced it. */
  timezone: string;
  /** Monotonic ordinal within the attempt. */
  seq: number;
  /** Milliseconds since exam start. */
  elapsedMs: number;
}

/**
 * the student changed an option's state.
 * `option` is REQUIRED here - a highlight event without an option index is
 * meaningless, and the old shape made it optional for every event type.
 */
export interface HighlightEvent extends EventEnvelope {
  elementType: typeof EventElement.Highlight;
  actionType: HighlightAction;
  question: number;
  /** 0 = A, 1 = B, ... Index into OPTION_LETTERS. */
  option: number;
}

/**
 * the student's attention entered, left, or clicked into a question.
 * Has no `option` at all - previously it was permitted and always undefined.
 */
export interface FocusAreaEvent extends EventEnvelope {
  elementType: typeof EventElement.FocusArea;
  actionType: FocusAreaAction;
  question: number;
}

/** the student toggled one of the four per-question flag buttons. */
export interface ButtonEvent extends EventEnvelope {
  elementType: ButtonKind;
  actionType: ButtonAction;
  question: number;
}

/**
 * one interaction, discriminated on `elementType`.
 *
 * The previous shape was a single wide object with two INDEPENDENT unions for
 * elementType and actionType, so combinations that cannot occur still
 * typechecked - `{elementType: 'focusArea', actionType: 'setCorrect'}` was
 * legal, as was a highlight event with no option. Narrowing on elementType now
 * tells the compiler exactly which actions and fields are available, and the
 * impossible combinations no longer compile.
 */
export type AttemptEvent = HighlightEvent | FocusAreaEvent | ButtonEvent;

/** the in-memory stream for one attempt. Name kept for compatibility. */
export type EventLogs = AttemptEvent[];

// re-exported from types/enums; kept here so existing imports still resolve.
export type HighlightMode = HighlightModeEnum;
