import type { DocumentOptionsText, DocumentText, OptionMarker, OptionText, PageOptionsText, PageSegments, QuestionSegment, SegmentedQuestions, SegmentOptionMarkers, SegmentOptionsText, textbox } from "@/lib/pdf/pdfTypes";
import { getGraphFont } from "./getGraphFont";
import { extractGraphics } from "./extractGraphics";
import { detectOptionFonts } from "./detectOptionFont";
// import added for the PDFDocumentProxy parameter type.
import type { PDFDocumentProxy } from "pdfjs-dist";

const betaTotalTextHighlight = true;

// centralise the supported option alphabet and measured geometry tolerances
// so the quartet-selection rules below do not drift across code paths.
const optionLabels = ['A', 'B', 'C', 'D'] as const;
const duplicateCoordinateTolerance = 0.1;
const visualLineTolerance = 2;
const alignedMarkerTolerance = 3;
const verticalGroupBaseScore = 1000;
const horizontalGroupBaseScore = 500;
const spatialGroupBaseScore = 100;

// preserve OptionMarker's narrow label type after trimming PDF text.
function isOptionLabel(text: string): text is OptionMarker['text'] {
  return (optionLabels as readonly string[]).includes(text);
}

// reduce repeated inline/table lettering to the A-B-C-D quartet that has
// option-like geometry. Complete vertical groups beat prose; complete
// horizontal groups are ranked by column spread, so a real four-column answer
// table beats the compact "A, B, C and D" phrase in its stem.
function selectPlausibleOptionQuartet(
  detected: SegmentOptionMarkers,
  segmentText: textbox[],
): SegmentOptionMarkers {
  if (detected.length <= optionLabels.length) return detected;

  const groups: SegmentOptionMarkers[] = [];
  let current: SegmentOptionMarkers = [];

  for (const marker of detected) {
    if (marker.text === 'A') {
      current = [marker];
      continue;
    }
    if (current.length > 0 && marker.text === optionLabels[current.length]) {
      current.push(marker);
      if (current.length === optionLabels.length) {
        groups.push(current);
        current = [];
      }
    }
  }

  if (groups.length === 0) return detected;

  function alignmentScore(group: SegmentOptionMarkers): number {
    const boxes = group.map(marker => segmentText[marker.index]!);
    const xs = boxes.map(box => box.x);
    const ys = boxes.map(box => box.y);
    const xRange = Math.max(...xs) - Math.min(...xs);
    const yRange = Math.max(...ys) - Math.min(...ys);
    if (xRange <= alignedMarkerTolerance) return verticalGroupBaseScore + yRange;
    if (yRange <= alignedMarkerTolerance) return horizontalGroupBaseScore + xRange;
    return spatialGroupBaseScore;
  }

  return groups.sort((a, b) => alignmentScore(b) - alignmentScore(a))[0]!;
}

function detectSegmentOptions(segmentText: textbox[], fontCandidates: string[]) {
  // inspect every candidate font and keep the one representing the most
  // distinct option letters. Returning on the first single A-D glyph let a
  // diagram/fraction font hide the real four-label option font.
  let bestDetected: SegmentOptionMarkers = [];
  let bestDistinctCount = 0;

  for (const candidateFont of fontCandidates) {

    const detected: SegmentOptionMarkers = [];

    for (let i = 0; i < segmentText.length; i++) {
      const box = segmentText[i];
      if (!box) continue;

      const text = box.text.trim();
      const font = box.font.trim();

      if (isOptionLabel(text) && font === candidateFont) {
        // some PDFs expose the same drawn glyph twice at identical
        // coordinates. It is one clickable label, not a fifth option.
        const duplicate = detected.some((option) => {
          const previous = segmentText[option.index];
          return previous?.text.trim() === text
            && Math.abs(previous.x - box.x) < duplicateCoordinateTolerance
            && Math.abs(previous.y - box.y) < duplicateCoordinateTolerance;
        });
        if (!duplicate) {
          detected.push({ text, index: i });
        }
      }
    }

    const selected = selectPlausibleOptionQuartet(detected, segmentText);
    const distinctCount = new Set(selected.map(option => option.text)).size;
    if (distinctCount > bestDistinctCount) {
      bestDetected = selected;
      bestDistinctCount = distinctCount;
    }
  }

  return bestDetected;
}

// was `pdf: any`. PDFDocumentProxy is pdfjs-dist's own type for a loaded
// document and is what extractGraphics() already expects downstream.
export async function getOptions(pdf: PDFDocumentProxy, totalText: DocumentText, segmentedQuestions: SegmentedQuestions): Promise<DocumentOptionsText> {
  let options: DocumentOptionsText = []

  const graphics = await extractGraphics(pdf);

  const graphFont = getGraphFont(totalText, graphics);

  const optionFonts = detectOptionFonts(totalText);
  const fontCandidates = optionFonts
    .filter(f => f.proportion > 0.1)
    .map(f => f.font);

  if (fontCandidates.length === 0) {
    fontCandidates.push(optionFonts[0]!.font);
  }

  for(let pageIndex = 0; pageIndex < segmentedQuestions.length; pageIndex++) {
    let pageOptions: PageOptionsText = []

    const pageSegments: PageSegments | undefined = segmentedQuestions[pageIndex];
    if(!pageSegments) continue;

    for(let segmentIndex = 0; segmentIndex < pageSegments.length; segmentIndex++) {

      const segment: QuestionSegment | undefined = pageSegments[segmentIndex];
      if(!segment) continue;
      // option association follows visual reading order. PDF stream order
      // can draw the text before its A-D label; sorting by line then x keeps
      // vertical, horizontal and tabular choices paired with the visible label.
      const segmentText: textbox[] = [...segment.segmentText].sort((a, b) => {
        if (Math.abs(a.y - b.y) > visualLineTolerance) return a.y - b.y;
        return a.x - b.x;
      });

      let segmentOptions: SegmentOptionMarkers = detectSegmentOptions(segmentText, fontCandidates);

      let segmentTotalOptionsText: SegmentOptionsText = []

      // diagram choices can be drawn in spatial/content-stream order such
      // as A,C,B,D. Those labels are the complete choices, so preserve their
      // boxes but expose them in semantic A-D order instead of slicing between
      // non-monotonic stream indices.
      const markerOrder = segmentOptions.map(option => option.text).join('');
      if (segmentOptions.length === optionLabels.length
          && markerOrder !== optionLabels.join('')) {
        segmentOptions = [...segmentOptions]
          .sort((a, b) => a.text.localeCompare(b.text));
        segmentTotalOptionsText = segmentOptions
          .map(option => [segmentText[option.index]!]);
      } else segmentOptions.forEach((option: OptionMarker, index) => {
        
        let totalOptionText: OptionText = segmentOptions[index + 1]
          ? segmentText.slice(option.index, segmentOptions[index + 1]!.index)
          : segmentText.slice(option.index);
      
        for(let l = 0; l < totalOptionText.length; l++) {
          if(totalOptionText[l]!.font === graphFont) {
            totalOptionText = [totalOptionText[0]!];
            break;
          }
        }
      
        segmentTotalOptionsText.push(totalOptionText);

      });

      // non-linear layouts cannot safely make formula fragments or table
      // cells select an answer. Horizontal/spatial labels and vertical labels
      // without same-line prose therefore expose only the four unambiguous
      // A-D glyphs as click targets. Ordinary vertical rows keep their text.
      const markerBoxes = segmentOptions.map(option => segmentText[option.index]!);
      const markerYs = markerBoxes.map(box => box.y);
      const markersAreHorizontal = markerYs.length === optionLabels.length
        && Math.max(...markerYs) - Math.min(...markerYs) <= alignedMarkerTolerance;
      const everyMarkerHasInlineText = markerBoxes.every(marker =>
        segmentText.some(item =>
          item.x > marker.x
          && Math.abs(item.y - marker.y) <= visualLineTolerance
          && !isOptionLabel(item.text.trim())));
      const markerFont = markerBoxes[0]?.font;
      const sameFontLetterCount = segmentText.filter(item =>
        item.font === markerFont && isOptionLabel(item.text.trim())).length;
      const ambiguousHorizontalTable = markersAreHorizontal
        && sameFontLetterCount > optionLabels.length;

      if (segmentOptions.length === optionLabels.length
          && (ambiguousHorizontalTable || !everyMarkerHasInlineText)) {
        segmentTotalOptionsText = segmentOptions.map(option => [segmentText[option.index]!]);
      }

      const anySingle = segmentTotalOptionsText.some(opt => opt.length === 1);

      if (anySingle || !betaTotalTextHighlight) {
        segmentTotalOptionsText = segmentTotalOptionsText.map(opt => [opt[0]!]);
      }

      pageOptions.push(segmentTotalOptionsText)
    }

    options.push(pageOptions);
  }

  return options

}

//TODO: Fix graph font detection
