import type { SegmentedQuestions } from "../pdf";
import { computeGlobalIndex } from "../utils/computeGlobalIndex";
import type { DocumentButtonTracks, ButtonTrack } from "./buttonTypes";
import { createTrackButtons } from "./createTrackButtons";

export function createTracks(segmentedQuestions: SegmentedQuestions): DocumentButtonTracks {

  let buttonTracks: DocumentButtonTracks = [];

  for(let pageIndex = 0; pageIndex < segmentedQuestions.length; pageIndex++) {
    
    const pageSegments = segmentedQuestions[pageIndex]!;

    for(let segmentIndex = 0; segmentIndex < pageSegments.length; segmentIndex++) {

      const segment = pageSegments[segmentIndex]!

      const questionNum = computeGlobalIndex(segmentedQuestions, pageIndex, segmentIndex);

      const buttons = createTrackButtons();

      const track: ButtonTrack = {
        y: segment.averageY,
        questionNum,
        el: undefined,
        buttons
      }

      for (const btn of buttons) {
        btn.parent = track;
      }

      if(!buttonTracks[pageIndex]) buttonTracks[pageIndex] = []
      buttonTracks[pageIndex]!.push(track)

    }
  };

  return buttonTracks;

}