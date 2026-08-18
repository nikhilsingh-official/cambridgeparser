// ==========================================================================
//
// Live per-question state for the Overview panel.
//
// WHY A SEPARATE STORE. The Overview needs to know, per question, which option
// is selected, which are eliminated, and which flags are set. Two of those
// already exist in the highlight tree - but createHighlights() returns a plain
// nested array, so mutating `highlight.state` triggers nothing, and the panel
// could never update. (createFocusAreas() does wrap each area in reactive(),
// which is why focus timers update live and highlights did not.)
//
// The obvious fix - wrapping the highlight tree in reactive() - was rejected:
// renderHighlights assigns live DOM nodes onto `highlight.el`, and handing DOM
// elements to Vue's proxy invites subtle breakage in the rendering path that is
// hard to diagnose. This store keeps the reactive projection separate from the
// DOM-bearing tree, and is written to from the same places that mutate it.
// ==========================================================================
import { computed, reactive } from "vue";
import type { OptionState } from "@/lib/highlights/highlightTypes";

/** the three flag buttons, named so callers cannot pass a stray string. */
export const QuestionFlag = {
  Flagged: "flagged",
  Difficult: "difficult",
  Saved: "saved",
} as const;
export type QuestionFlag = typeof QuestionFlag[keyof typeof QuestionFlag];

export interface QuestionState {
  questionNumber: number;
  optionCount: number;
  /** Option index (0 = A), or null when nothing is chosen. */
  selected: number | null;
  /** Option indexes the student has ruled out. */
  eliminated: number[];
  flagged: boolean;
  difficult: boolean;
  saved: boolean;
}

const questions = reactive(new Map<number, QuestionState>());

function blank(questionNumber: number, optionCount: number): QuestionState {
  return {
    questionNumber,
    optionCount,
    selected: null,
    eliminated: [],
    flagged: false,
    difficult: false,
    saved: false,
  };
}

/** called when a new paper is opened, so state never leaks between papers. */
export function resetExamState() {
  questions.clear();
}

/**
 * seed one row per question so the Overview lists the whole paper straight
 * away rather than filling in only as the student interacts.
 */
export function seedQuestions(entries: { questionNumber: number; optionCount: number }[]) {
  for (const { questionNumber, optionCount } of entries) {
    const existing = questions.get(questionNumber);
    if (existing) existing.optionCount = optionCount;
    else questions.set(questionNumber, blank(questionNumber, optionCount));
  }
}

function ensure(questionNumber: number, optionCount = 4): QuestionState {
  let q = questions.get(questionNumber);
  if (!q) {
    q = blank(questionNumber, optionCount);
    questions.set(questionNumber, q);
  }
  return q;
}

/**
 * Mirror a highlight transition into the overview.
 *
 * deliberately mirrors selectOption's DOM rules rather than inventing its
 * own. "correct" is single-choice (picking B clears A), eliminating the option
 * you had chosen also unpicks it, and returning to neutral clears both.
 */
export function setOptionState(
  questionNumber: number,
  optionIndex: number,
  state: OptionState,
) {
  const q = ensure(questionNumber);

  if (state === "correct") {
    q.selected = optionIndex;
    q.eliminated = q.eliminated.filter((i) => i !== optionIndex);
    return;
  }

  if (state === "eliminated") {
    if (!q.eliminated.includes(optionIndex)) q.eliminated.push(optionIndex);
    if (q.selected === optionIndex) q.selected = null;
    return;
  }

  // neutral
  q.eliminated = q.eliminated.filter((i) => i !== optionIndex);
  if (q.selected === optionIndex) q.selected = null;
}

/**
 * per-question flags. ActiveQuestionButtons previously held ONE global set
 * of four button states, so flagging question 3 left the Flag button lit when
 * the student moved to question 4 - the UI claimed a flag that was not there.
 */
export function toggleFlag(questionNumber: number, flag: QuestionFlag): boolean {
  const q = ensure(questionNumber);
  q[flag] = !q[flag];
  return q[flag];
}

export function getQuestion(questionNumber: number): QuestionState | undefined {
  return questions.get(questionNumber);
}

/** ordered list for the Overview panel. */
export const questionList = computed(() =>
  [...questions.values()].sort((a, b) => a.questionNumber - b.questionNumber),
);

export const answeredCount = computed(
  () => questionList.value.filter((q) => q.selected !== null).length,
);
