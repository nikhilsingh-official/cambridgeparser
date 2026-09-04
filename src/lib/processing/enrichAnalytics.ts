import type { ButtonType } from "../buttons";
import { clamp } from "../utils/clamp";
import { findOptimalSteepness } from "../utils/findOptimalSteepness";
import { meanStd } from "../utils/meanStd";
import { normalizeWeights } from "../utils/normalizeWeights";
import { timeToConfidence } from "../utils/timeToConfidence";
import type { EventLogs, HighlightActions, ButtonActions } from "../utils/utilsTypes";
import { partitionLogsByQuestion } from "./partitionLogsByQuestion";
import type { QuestionsAnalytics } from "./processingTypes";

export function enrichAnalytics(baseAnalytics: QuestionsAnalytics, eventLogs: EventLogs): QuestionsAnalytics {

  const enriched: QuestionsAnalytics = baseAnalytics.map((q) => ({ ...q }));

  const logsByQ = partitionLogsByQuestion(eventLogs);

  //Array of response times
  const times = enriched.map((q) => q.time ?? 0).filter((t) => t > 0);
  
  //Compute mean of all response times
  const meanTime = times.length ? times.reduce((a, b) => a + b, 0) / times.length : 1;

  //Normalize response times to real numbers between 0 and 1 with respect to mean time
  const normalizedTimes = enriched.map((q) => {
    const t = q.time ?? 0;
    if (t <= 0) return 1;
    return meanTime / t;
  });

  const { mean: meanNorm, std: stdNorm } = meanStd(normalizedTimes)

  //Programmatically extract the optimal steepness factor for the sigmoid function
  const sigmoidSteepnessFactor = findOptimalSteepness(normalizedTimes);

  //Compute meaningful scores from normalized times
  const timeConfByIndex = normalizedTimes.map((norm) =>
    timeToConfidence(norm, sigmoidSteepnessFactor, meanNorm, stdNorm)
  );

  //Weights for confidence - 0.4 for right/wrong flag, 0.3 for confidence measured from highlights, 0.2 for confidence measured from time spent on question, 0.1 from the number of times the question is revisited.
  const confWeights = normalizeWeights([0.4, 0.3, 0.2, 0.1]);

  //Weights for difficulty - 0.4 for marked as difficult, 0.25 for number of times they switched the correct answer, 0.2 for inverse confidence, 0.1 for hesitation and 0.05 for revisitation
  const diffWeights = normalizeWeights([0.4, 0.25, 0.2, 0.1, 0.05]);

  //Weights for interest - 0.35 for if the question was saved or not, 0.25 for the number of highlight events the user engaged with that question, 0.15 for revisitation, 0.05 for marked for review, 0.05 for difficulty, 0.15 for time spent on question
  const interestWeights = normalizeWeights([0.35, 0.25, 0.15, 0.05, 0.05, 0.15]);

  //Main loop to compute derived quantities per question
  for (let i = 0; i < enriched.length; i++) {
    const q = enriched[i]!;
    const qLogs = logsByQ.get(q.questionNumber) ?? [];

    //Events where the user interacts with a highlight
    const highlightEvents = qLogs.filter((e) => e.elementType === "highlight");

    //Calculate the number of times the user switches the correct answer
    let lastSelectedOption: number | undefined = undefined;
    let optionSwitchCount = 0;

    for (const ev of highlightEvents) {
      if (typeof ev.option !== "number") continue;
      if (ev.actionType === "setCorrect" || ev.actionType == "elimToCorrect") {
        if (lastSelectedOption !== undefined) {
          optionSwitchCount++;
        }
        lastSelectedOption = ev.option;
      } else if (ev.actionType === "deselectedCorrect") {
        lastSelectedOption = undefined;
      }
    }

    const BUTTON_TYPES: ButtonType[] = ["Copy", "Flag", "Star", "Save"];


    // these controls are toggles, so analytics must reflect their final
    // state. Counting Selection events made an on/off cycle look selected and
    // rewarded repeated cycles. Copy remains a one-shot interaction elsewhere.
    const finalButtonState = qLogs.reduce((state, event) => {
      if (!BUTTON_TYPES.includes(event.elementType as ButtonType)) return state;
      const key = event.elementType as ButtonType;
      state[key] = event.actionType === "Selection";
      return state;
    }, {} as Record<ButtonType, boolean>);

    function diminishing(value: number) {
      const first = 0.5;
      const extra = 0.25;
      const maxPenalty = 0.9;

      if (value <= 0) return 1;

      const penalty = Math.min(maxPenalty, first + extra * (value - 1));
      const norm = Math.max(0.1, 1 - penalty);
      return norm;
    }

    // explicit positive intent must start at zero and rise when the user
    // acts. `diminishing()` runs in the opposite direction and is reserved for
    // confidence penalties such as marking a question for review.
    function increasing(value: number) {
      if (value <= 0) return 0;
      return Math.min(0.9, 0.5 + 0.25 * (value - 1));
    }

    const flagCount = finalButtonState.Flag ? 1 : 0;
    const markReviewScore = diminishing(flagCount);

    //Calculate the number of times the user eliminates an option
    let elimCount = 0;
    //Calculate the number of times the user reverses their elimination of an option
    let elimReversalCount = 0;
    for (const ev of highlightEvents) {
      const a = ev.actionType as HighlightActions;
      if (a === "setElim" || a === "correctToElim") elimCount++;
      if (a === "deselectedElim" || a === "elimToCorrect") elimReversalCount++;
    }

    //Calculate the number of times the user revisits a question
    const focusInEvents = qLogs.filter((e) => e.elementType === "focusArea" && e.actionType === "userClick");
    const revisitCount = focusInEvents.length;

    //Get times of meaningful events that mark interaction with a question, after the initial click
    const meaningfulEvents = qLogs
      .filter((e) => {
        return (
          e.elementType !== "focusArea"
        )
      })
      .map((e) => e.performanceTimestamp)
      .filter((t): t is number => typeof t === "number")
      .sort((a, b) => a - b);

    let hesitationTime: number | undefined = undefined;
    if (meaningfulEvents.length) {
      const userClicks = qLogs
        .filter((e) => e.elementType === "focusArea" && e.actionType === "userClick")
        .map((e) => e.performanceTimestamp)
        .filter((t): t is number => typeof t === "number")
        .sort((a, b) => a - b);

      //Initial interaction that marks selection of question
      const baseline = userClicks.length ? userClicks[0] : qLogs.map((e) => e.performanceTimestamp).filter((t): t is number => typeof t === "number")[0];

      if (baseline !== undefined && meaningfulEvents[0] !== undefined) {
        //Time between question selection and first interaction with question
        hesitationTime = Math.max(0, meaningfulEvents[0] - baseline);
      } else {
        hesitationTime = meaningfulEvents[0];
      }
    }

    //Total interactions with a question
    const interactionTypes = new Set<number | string>();
    let interactionCount = 0;

    for (const ev of qLogs) {
      if (ev.elementType === "highlight") {
        //All highlight interactions are significant
        interactionCount++;
        if (typeof ev.option === "number") interactionTypes.add(ev.option);
      } else if (ev.elementType !== "focusArea") {
        //Button interactions
        interactionCount++;
        const a = ev.actionType as ButtonActions;
        interactionTypes.add(a);
      }
    }

    const explorationDepth = interactionCount;

    const explorationBreadth = interactionTypes.size;

    // eliminationStrength: Measures how confidently the user eliminated distractors.
    // It is the ratio of stable eliminations to total elimination actions.
    // 1.0 = all eliminations kept (high confidence)
    // 0.0 = no eliminations or all reversed (low confidence)
    const stableEliminationRatio = elimCount === 0 ? 0 : clamp((elimCount - elimReversalCount) / Math.max(1, elimCount), 0, 1);

    //Confidence signal derived from elimination behaviour
    const highlightConf = clamp(stableEliminationRatio);

    //Confidence signal derived from time behaviour
    const timeConf = clamp(timeConfByIndex[i]!);

    //Confidence signal derived from revisit behaviour
    const revisitConf = clamp(1 / (1 + revisitCount));

    //Compute final confidence score
    const confVals = [markReviewScore, highlightConf, timeConf, revisitConf];
    const confidenceScore = clamp(
      confWeights[0] * confVals[0]! +
        confWeights[1] * confVals[1]! +
        confWeights[2] * confVals[2]! +
        confWeights[3] * confVals[3]!,
      0,
      1
    );

    //Difficulty signal (boolean) from marked as difficult
    const difficultCount = finalButtonState.Star ? 1 : 0;
    // Star is evidence for difficulty, so its signal rises from zero.
    const markDifficultScore = increasing(difficultCount);

    //Difficulty signal derived from number of times the user switches options
    const switchScore = clamp(optionSwitchCount / Math.max(1, 5));

    //Difficulty signal derived from the difference in time between question selection and users first interaction
    const hesitationScore = clamp((hesitationTime ?? 0) / Math.max(1, q.time || 1));

    //Difficulty signal derived from the revisit behaviour
    const revisitScore = clamp(revisitCount / Math.max(1, 5));

    //Difficulty signal derived from confidence
    const inverseConfidence = clamp(1 - confidenceScore);

    const difficulty =
      diffWeights[0] * markDifficultScore +
      diffWeights[1] * switchScore +
      diffWeights[2] * inverseConfidence +
      diffWeights[3] * hesitationScore +
      diffWeights[4] * revisitScore;
    const difficultyScore = clamp(difficulty);

    //Interest signal derived from saving question
    const saveCount = finalButtonState.Save ? 1 : 0;
    // Save is evidence for interest, so its signal rises from zero.
    const markSaveScore = increasing(saveCount);

    // review intent contributes positively to interest even though the
    // same Flag event contributes inversely to confidence.
    const markReviewInterestScore = increasing(flagCount);

    //Interest signal derived from number of highlight events
    const highlightSignal = clamp(highlightEvents.length / Math.max(1, 6));

    //Interest signal derived from time spent on question
    const timeSignal = clamp((q.time ?? 0) / Math.max(1, meanTime));

    //Compute final confidence score
    const interestRaw =
      interestWeights[0] * markSaveScore +
      interestWeights[1] * highlightSignal +
      interestWeights[2] * clamp(revisitCount / Math.max(1, 3)) +
      interestWeights[3] * markReviewInterestScore +
      interestWeights[4] * difficultyScore +
      interestWeights[5] * timeSignal;
    const interestScore = clamp(interestRaw);

    enriched[i] = {
      ...q,
      markedForReview: flagCount,
      markedAsDifficult: difficultCount,
      markedForSave: saveCount,
      hesitationTime,
      optionSwitchCount,
      eliminationReversalCount: elimReversalCount,
      revisitCount,
      stableEliminationRatio,
      explorationDepth,
      explorationBreadth,
      confidenceScore,
      difficultyScore,
      interestScore,
    };
  }

  return enriched;
}
