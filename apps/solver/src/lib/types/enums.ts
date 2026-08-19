// ==========================================================================
//
// Central enumerations for SmartSolver.
//
// WHY NOT `enum`: tsconfig.app.json sets "erasableSyntaxOnly": true, which
// forbids TypeScript `enum` because it emits runtime code. The pattern used
// throughout this file is the erasable equivalent:
//
//     export const Thing = { A: 'a', B: 'b' } as const;
//     export type  Thing = typeof Thing[keyof typeof Thing];
//
// This gives you both halves an `enum` would: a named runtime map you can
// reference as `Thing.A` instead of writing the bare literal, and a union type
// that accepts only those values. The declaration-merged name means
// `Thing` reads as a type in type position and a value in value position,
// exactly like an enum, with no runtime cost.
//
// Every list here is closed - if a value is not in the map, it is not valid.
// ==========================================================================

// --------------------------------------------------------------------------
// Interaction events
// --------------------------------------------------------------------------

/** Which kind of UI element produced an event. Discriminant for AttemptEvent. */
export const EventElement = {
  Highlight: 'highlight',
  FocusArea: 'focusArea',
  Copy: 'Copy',
  Flag: 'Flag',
  Star: 'Star',
  Save: 'Save',
} as const;
export type EventElement = typeof EventElement[keyof typeof EventElement];

/** The four per-question flag buttons. Subset of EventElement. */
export const ButtonKind = {
  Copy: 'Copy',
  Flag: 'Flag',
  Star: 'Star',
  Save: 'Save',
} as const;
export type ButtonKind = typeof ButtonKind[keyof typeof ButtonKind];

/**
 * State transitions on an answer option.
 * Named from -> to: `elimToCorrect` means it was eliminated and is now selected.
 * These are the values selectOption() derives from (mode, previousState).
 */
export const HighlightAction = {
  SetCorrect: 'setCorrect',
  DeselectedCorrect: 'deselectedCorrect',
  SetElim: 'setElim',
  DeselectedElim: 'deselectedElim',
  ElimToCorrect: 'elimToCorrect',
  CorrectToElim: 'correctToElim',
} as const;
export type HighlightAction = typeof HighlightAction[keyof typeof HighlightAction];

/** Attention events on a question's focus area. */
export const FocusAreaAction = {
  UserClick: 'userClick',
  UserHoveredIn: 'userHoveredIn',
  UserHoveredOutPage: 'userHoveredOutPage',
} as const;
export type FocusAreaAction = typeof FocusAreaAction[keyof typeof FocusAreaAction];

/** Toggling a flag button on or off. */
export const ButtonAction = {
  Selection: 'Selection',
  Deselection: 'Deselection',
} as const;
export type ButtonAction = typeof ButtonAction[keyof typeof ButtonAction];

/** Any action value, whatever produced it. */
export type AnyEventAction = HighlightAction | FocusAreaAction | ButtonAction;

// --------------------------------------------------------------------------
// Answering
// --------------------------------------------------------------------------

/** What clicking an option does, toggled with the C / E keys. */
export const HighlightMode = {
  Correct: 'correct',
  Eliminated: 'eliminated',
} as const;
export type HighlightMode = typeof HighlightMode[keyof typeof HighlightMode];

/** Current state of a single option. `neutral` = untouched. */
export const OptionState = {
  Correct: 'correct',
  Eliminated: 'eliminated',
  Neutral: 'neutral',
} as const;
export type OptionState = typeof OptionState[keyof typeof OptionState];

/** MCQ option labels, in paper order. Index in this array == stored option index. */
export const OPTION_LETTERS = ['A', 'B', 'C', 'D'] as const;
export type OptionLetter = typeof OPTION_LETTERS[number];

/** How a question's content is laid out - drives extraction strategy. */
export const QuestionType = {
  Text: 'text',
  Table: 'table',
  Graph: 'graph',
} as const;
export type QuestionType = typeof QuestionType[keyof typeof QuestionType];

// --------------------------------------------------------------------------
// Papers
// --------------------------------------------------------------------------

/**
 * Cambridge exam series, as it appears in a paper schema string:
 * '0625_s25_22' -> series 's'.
 */
export const ExamSeries = {
  FebruaryMarch: 'm',
  MayJune: 's',
  OctoberNovember: 'w',
} as const;
export type ExamSeries = typeof ExamSeries[keyof typeof ExamSeries];

/** Human labels for the above, for display. */
export const EXAM_SERIES_LABEL: Record<ExamSeries, string> = {
  m: 'Feb/Mar',
  s: 'May/Jun',
  w: 'Oct/Nov',
};

/** Qualification a syllabus belongs to. Mirrors subjects.qualification. */
export const Qualification = {
  IGCSE: 'IGCSE',
  OLevel: 'O Level',
  ASALevel: 'AS/A Level',
} as const;
export type Qualification = typeof Qualification[keyof typeof Qualification];

// --------------------------------------------------------------------------
// Persistence - these mirror Postgres enums in schema.sql. Keep in step.
// --------------------------------------------------------------------------

/** Lifecycle of an attempt. Mirrors the SQL `attempt_status` enum. */
export const AttemptStatus = {
  InProgress: 'in_progress',
  Completed: 'completed',
  Abandoned: 'abandoned',
} as const;
export type AttemptStatus = typeof AttemptStatus[keyof typeof AttemptStatus];

/** Kinds of study goal. Mirrors the SQL `goal_kind` enum. */
export const GoalKind = {
  PapersPerWeek: 'papers_per_week',
  AccuracyTarget: 'accuracy_target',
  SubjectFocus: 'subject_focus',
  StreakDays: 'streak_days',
} as const;
export type GoalKind = typeof GoalKind[keyof typeof GoalKind];

// --------------------------------------------------------------------------
// Stats page
// --------------------------------------------------------------------------

/**
 * The statistics a stat card can display.
 *
 * These were bare numbers 0-16 indexed into three parallel Records in
 * codeMaps.ts, so `categoryToText[13]` told a reader nothing. The numeric
 * values are unchanged, so existing data and props keep working - only the
 * spelling at the call site improves: StatCategory.PeakSolvingHour instead of 13.
 */
export const StatCategory = {
  TopSubject: 0,
  TotalPapersSolved: 1,
  TotalTimeSolving: 2,
  OverallAccuracy: 3,
  PracticeStreak: 4,
  StrongestSubject: 5,
  MostImprovedSubject: 6,
  MostAttemptedSubject: 7,
  ThisWeeksAccuracy: 8,
  ThisWeeksSolvingTime: 9,
  TimeSinceLastPaper: 10,
  FastestCompletionTime: 11,
  LongestSession: 12,
  PeakSolvingHour: 13,
  NextGoal: 14,
  ImprovementRate: 15,
  PerformanceOverview: 16,
} as const;
export type StatCategory = typeof StatCategory[keyof typeof StatCategory];

/** Every StatCategory value, for iteration (CardStrip cycles through these). */
export const ALL_STAT_CATEGORIES = Object.values(StatCategory) as StatCategory[];
