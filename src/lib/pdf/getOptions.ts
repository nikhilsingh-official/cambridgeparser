import type { DocumentGraphics, DocumentOptionsText, DocumentText, OptionMarker, OptionText, PageOptionsText, PageSegments, QuestionSegment, SegmentedQuestions, SegmentOptionMarkers, SegmentOptionsText, textbox } from "@/lib/pdf/pdfTypes";
import { getGraphFont } from "./getGraphFont";
import { extractGraphics } from "./extractGraphics";
import { detectOptionFonts } from "./detectOptionFont";
// import added for the PDFDocumentProxy parameter type.
import type { PDFDocumentProxy } from "pdfjs-dist";
import { classifySegmentedQuestions } from "./classifyQuestions";
import { OPS } from "pdfjs-dist";

const betaTotalTextHighlight = true;

function detectSegmentOptions(segmentText: textbox[], fontCandidates: string[]) {
  for (const candidateFont of fontCandidates) {

    const detected: SegmentOptionMarkers = [];

    for (let i = 0; i < segmentText.length; i++) {
      const box = segmentText[i];
      if (!box) continue;

      const text = box.text.trim();
      const font = box.font.trim();

      if (["A", "B", "C", "D"].includes(text) && font === candidateFont) {
        detected.push({ text: (text as "A" | "B" | "C" | "D"), index: i });
      }
    }

    if (detected.length > 0) return detected;
  }

  return [];
}

function entropy(angles: number[], bins = 12): number {
  if (angles.length === 0) return 0;

  const hist = new Array(bins).fill(0);

  for (const a of angles) {
    // normalize angle to [0, 2π)
    const norm = (a + Math.PI * 2) % (Math.PI * 2);
    const bin = Math.floor((norm / (Math.PI * 2)) * bins);
    hist[Math.min(bin, bins - 1)]++;
  }

  const total = angles.length;
  let e = 0;

  for (const count of hist) {
    if (count === 0) continue;
    const p = count / total;
    e -= p * Math.log2(p);
  }

  return e;
}

function dominantClusterRatio(
  ys: number[],
  tolerance = 2
): number {
  if (ys.length === 0) return 0;

  const clusters: number[] = [];

  for (const y of ys) {
    let found = false;
    for (let i = 0; i < clusters.length; i++) {
      if (Math.abs(clusters[i] - y) <= tolerance) {
        clusters[i] = (clusters[i] + y) / 2;
        found = true;
        break;
      }
    }
    if (!found) clusters.push(y);
  }

  // Count membership
  const counts = new Map<number, number>();
  for (const y of ys) {
    for (const c of clusters) {
      if (Math.abs(c - y) <= tolerance) {
        counts.set(c, (counts.get(c) ?? 0) + 1);
        break;
      }
    }
  }

  const maxCluster = Math.max(...counts.values());
  return maxCluster / ys.length;
}

import type { PageText } from "@/lib/pdf/pdfTypes";

function avgTextToStrokeDistance(
  pageText: PageText,
  strokeYs: number[]
): number {
  if (pageText.length === 0 || strokeYs.length === 0) return Infinity;

  let totalDist = 0;
  let count = 0;

  for (const t of pageText) {
    let minDist = Infinity;
    for (const y of strokeYs) {
      const d = Math.abs(t.y - y);
      if (d < minDist) minDist = d;
    }
    totalDist += minDist;
    count++;
  }

  return totalDist / count;
}

function summarizeOps(
  documentGraphics: DocumentGraphics,
  documentText: DocumentText
) {
  const summaries = [];

  const totalPages = Math.min(
    documentGraphics.length,
    documentText.length
  );

  for (let i = 0; i < totalPages; i++) {
    const pageText = documentText[i];
    const pageGraphics = documentGraphics[i];

    if (!pageText || !pageGraphics) {
      summaries.push(null);
      continue;
    }

    let strokeCount = 0;
    let lineToCount = 0;
    let moveToCount = 0;

    const angles: number[] = [];
    const strokeYs: number[] = [];

    let currentPoint: { x: number; y: number } | null = null;

    for (const g of pageGraphics) {
      if (g.fnId === OPS.moveTo) {
        moveToCount++;
        // GraphicsItem.args is `unknown[]` (op-specific positional tuple).
        // moveTo/lineTo carry [x, y] as numbers; narrowed here where fnId is known.
        const [mx, my] = g.args as [number, number];
        currentPoint = { x: mx, y: my };
      }

      else if (g.fnId === OPS.lineTo && currentPoint) {
        lineToCount++;
        // see the moveTo note above.
        const [x, y] = g.args as [number, number];
        angles.push(Math.atan2(y - currentPoint.y, x - currentPoint.x));
        currentPoint = { x, y };
      }

      else if (g.fnId === OPS.stroke || g.fnId === OPS.fill) {
        strokeCount++;
        if (currentPoint) strokeYs.push(currentPoint.y);
        currentPoint = null;
      }
    }

    summaries.push({
      pageIndex: i,
      strokeCount,
      lineToCount,
      moveToCount,
      avgSegmentsPerStroke:
        strokeCount > 0 ? lineToCount / strokeCount : 0,
      angleEntropy: entropy(angles),
      yClusterStrength: dominantClusterRatio(strokeYs),
      textStrokeDistance: avgTextToStrokeDistance(pageText, strokeYs)
    });
  }

  return summaries;
}

// was `pdf: any`. PDFDocumentProxy is pdfjs-dist's own type for a loaded
// document and is what extractGraphics() already expects downstream.
export async function getOptions(pdf: PDFDocumentProxy, totalText: DocumentText, segmentedQuestions: SegmentedQuestions): Promise<DocumentOptionsText> {
  let options: DocumentOptionsText = []

  const graphics = await extractGraphics(pdf);

  console.log("Graphics")
  console.log(graphics)

  console.log("SUMMARY")
  console.log(summarizeOps(graphics, totalText))

  const graphFont = getGraphFont(totalText, graphics);

  const classified = classifySegmentedQuestions(segmentedQuestions, graphics, graphFont)
  console.log("Classified")
  console.log(classified)

  const optionFonts = detectOptionFonts(totalText);
  const fontCandidates = optionFonts
    .filter(f => f.proportion > 0.1)
    .map(f => f.font);

  if (fontCandidates.length === 0) {
    fontCandidates.push(optionFonts[0]!.font);
  }

  console.log("Detected Option Fonts: ", fontCandidates);
  console.log("Detected Graph Font: ", graphFont);

  for(let pageIndex = 0; pageIndex < segmentedQuestions.length; pageIndex++) {
    let pageOptions: PageOptionsText = []

    const pageSegments: PageSegments | undefined = segmentedQuestions[pageIndex];
    if(!pageSegments) continue;

    for(let segmentIndex = 0; segmentIndex < pageSegments.length; segmentIndex++) {

      const segment: QuestionSegment | undefined = pageSegments[segmentIndex];
      if(!segment) continue;
      const segmentText: textbox[] = segment.segmentText;

      let segmentOptions: SegmentOptionMarkers = detectSegmentOptions(segmentText, fontCandidates);

      let segmentTotalOptionsText: SegmentOptionsText = []

      segmentOptions.forEach((option: OptionMarker, index) => {
        
        let totalOptionText: OptionText = segmentOptions[index + 1]
          ? segmentText.slice(option.index, segmentOptions[index + 1]!.index)
          : segmentText.slice(option.index);
      
        for(let l = 0; l < totalOptionText.length; l++) {
          if(totalOptionText[l]!.font === graphFont) {
            console.log("Graph Question Found")
            totalOptionText = [totalOptionText[0]!];
            break;
          }
        }
      
        segmentTotalOptionsText.push(totalOptionText);

      });

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
