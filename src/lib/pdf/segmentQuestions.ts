import type { DocumentText, DocumentQuestionMarkers, SegmentedQuestions, PageText, PageSegments } from "@/lib/pdf/pdfTypes";

export function segmentQuestions(totalText: DocumentText, question_numbers: DocumentQuestionMarkers): SegmentedQuestions {

  let segmentedQuestions: SegmentedQuestions = [];

  for (let pageIndex = 0; pageIndex < totalText.length; pageIndex++) {

    const textSet = totalText[pageIndex]
    if(!textSet) continue;
    const pageText: PageText = textSet;

    const questionNumsOnPage = question_numbers[pageIndex];
    if (!questionNumsOnPage) continue;

    let pageSegments: PageSegments = [];

    for (let i = 0; i < questionNumsOnPage.length; i++) {
        const current = questionNumsOnPage[i];
        const next = questionNumsOnPage[i + 1];

        if (!current) continue;      
        let startIndex = current.index;
        let endIndex = next ? next.index : pageText.length;

        let questionSegment = pageText.slice(startIndex, endIndex);
        if (questionSegment.length === 0) continue;

        const startY: number = questionSegment[0]!.y;
        const endY: number = next ? (next.y - current.y2 ) / 2 : questionSegment
          .sort((a, b) => a.y2 - b.y2)
          [questionSegment.length - 1]!.y2; + 5

        const averageY: number = (startY + endY) / 2;

        pageSegments.push({ segmentText: questionSegment, averageY });      
    }

    segmentedQuestions.push(pageSegments);
  }

  return segmentedQuestions

}