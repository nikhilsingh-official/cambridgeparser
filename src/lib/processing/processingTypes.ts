export type OptionLetter = "A" | "B" | "C" | "D";

export interface QuestionAnalytics {
  questionNumber: number;
  qCorrect: boolean;

  // Raw User Input Data
  selectedOption?: OptionLetter;        // Final selected answer
  eliminatedOptions?: OptionLetter[];   // Options the user ruled out
  time: number;                         // Total time spent on the question
  markedForReview?: number;             // Whether user marked it for review
  markedAsDifficult?: number;           // Explicit difficulty mark
  markedForSave?: number;               // Explicit "favourite"/save mark

  // ===== Enriched Interaction Metrics =====

  hesitationTime?: number;              // Time before first meaningful action (first elim or first selection)
  optionSwitchCount?: number;           // Number of times user changed selected options (A→C→B)
  eliminationReversalCount?: number;    // Number of times the user re-added an eliminated option ("undo elim")
  revisitCount?: number;                // How many times the question was reopened

  // ===== Derived Cognitive Signals =====

  stableEliminationRatio?: number;         // How strongly user eliminated distractors (ratio & stability)
  explorationDepth?: number;
  explorationBreadth?: number;

  // ===== Final Computed Scores =====

  confidenceScore?: number;             // Confidence (based on speed, switches, elimination strength, reversals)
  difficultyScore?: number;             // Perceived difficulty (switches, hesitation, explicit mark, revisits)
  interestScore?: number;               // User engagement (revisits, time, interaction, save flag)
}

export type QuestionsAnalytics = QuestionAnalytics[];

export interface TableRow {
  question: number;
  answer: string;
  marks: string;
  page: number;
  y: number;
}