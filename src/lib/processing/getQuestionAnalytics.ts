import type { DocumentFocusAreas } from "../focusAreas";
import type { DocumentHighlights } from "../highlights/highlightTypes";
import { computeGlobalIndex } from "../utils/computeGlobalIndex";
import type { OptionLetter, QuestionAnalytics, QuestionsAnalytics, TableRow } from "./processingTypes";



export function getQuestionsAnalytics(highlights: DocumentHighlights, focusAreas: DocumentFocusAreas, answers: TableRow[] ): QuestionsAnalytics {

  const questionsData: QuestionsAnalytics = []

  for(let pageIndex = 0; pageIndex < highlights.length; pageIndex++) {

    const pageHighlights = highlights[pageIndex]!;
    const pageFocusAreas = focusAreas[pageIndex]!;

    for(let segmentIndex = 0; segmentIndex < pageHighlights.length; segmentIndex++) {

      const OPTIONS_LETTER_MAP: OptionLetter[] = ["A", "B", "C", "D"];

      const segmentHighlights = pageHighlights[segmentIndex]!;
      const segmentFocusArea = pageFocusAreas[segmentIndex]!;

      const questionNumber = computeGlobalIndex(highlights, pageIndex, segmentIndex)

      const answerRow = answers.find(x => x.question == questionNumber);

      const questionData: QuestionAnalytics = {
        questionNumber: questionNumber,
        time: segmentFocusArea.time,
        qCorrect: false
      }

      for(let optionIndex = 0; optionIndex < segmentHighlights.length; optionIndex++) {

        const optionHighlights = segmentHighlights[optionIndex]!;
        const state = optionHighlights[0]?.state;

        const option = OPTIONS_LETTER_MAP[optionIndex]!;

        if(state == "correct") {
          questionData.selectedOption = option;
          if(answerRow && answerRow.answer == option) questionData.qCorrect = true;
        } else if(state == "eliminated") {
          if(!questionData.eliminatedOptions) questionData.eliminatedOptions = [];
          questionData.eliminatedOptions.push(option);
        }

      }

      questionsData.push(questionData);

    }
  }

  return questionsData
}