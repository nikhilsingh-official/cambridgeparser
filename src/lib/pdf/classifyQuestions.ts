import { OPS } from "pdfjs-dist";
import type {
  SegmentedQuestions,
  DocumentGraphics,
  QuestionSegment
} from "@/lib/pdf/pdfTypes";

export type QuestionType = "text" | "table" | "graph";

export type ClassifiedQuestion = QuestionSegment & {
  type: QuestionType;
  confidence: number;
  scores: {
    text: number;
    table: number;
    graph: number;
  };
};

export type ClassifiedSegments = ClassifiedQuestion[][];

/* -----------------------------
   Graphics profiling (page-level)
-------------------------------- */

type GraphicsProfile = {
  stroke: number;
  rectangle: number;
};

function getPageGraphicsProfile(
  pageGraphics: DocumentGraphics[number]
): GraphicsProfile {
  let stroke = 0;
  let rectangle = 0;

  for (const g of pageGraphics) {
    if (g.fnId === OPS.stroke || g.fnId === OPS.fill) {
      stroke++;
    } else if (g.fnId === OPS.rectangle) {
      rectangle++;
    }
  }

  return { stroke, rectangle };
}

function graphScore(profile: GraphicsProfile): number {
  const { stroke, rectangle } = profile;
  if (stroke + rectangle === 0) return 0;

  const strokeRatio = stroke / (stroke + rectangle + 1);
  return Math.log1p(stroke) * strokeRatio;
}

function tableScore(profile: GraphicsProfile): number {
  const { stroke, rectangle } = profile;

  if (stroke + rectangle === 0) return 0;

  const rectRatio = rectangle / (stroke + rectangle + 1);
  return Math.log1p(rectangle) * rectRatio;
}

function textScore(profile: GraphicsProfile): number {
  const { stroke, rectangle } = profile;
  return 1 / (1 + stroke + rectangle);
}

/* -----------------------------
   Question-level classifier
-------------------------------- */

function classifyQuestion(
  segment: QuestionSegment,
  pageGraphics: DocumentGraphics[number],
  graphFont?: string
): {
  type: QuestionType;
  confidence: number;
  scores: {
    text: number;
    table: number;
    graph: number;
  };
} {

  const profile = getPageGraphicsProfile(pageGraphics);

  const scores = {
    graph: graphScore(profile),
    table: tableScore(profile),
    text: textScore(profile)
  };

  // --- Structure decision ---
  const ordered = Object.entries(scores)
    .sort((a, b) => b[1] - a[1]);

  let type = ordered[0][0] as QuestionType;
  let confidence =
    ordered[0][1] /
    (ordered[0][1] + ordered[1][1] + 1e-6);

  // --- Graph-font fusion (secondary signal) ---
  if (graphFont) {
    const fontsUsed = new Set(
      segment.segmentText.map(t => t.font)
    );

    const usesGraphFont = fontsUsed.has(graphFont);

    // Strong structure → boost
    if (usesGraphFont && type === "graph" && confidence >= 0.65) {
      confidence = Math.min(1, confidence * 1.25);
    }

    // Weak structure → rescue
    if (
      usesGraphFont &&
      confidence < 0.6 &&
      scores.graph >= scores.table
    ) {
      type = "graph";
      confidence = Math.max(confidence, 0.7);
    }
  }

  return {
    type,
    confidence,
    scores
  };
}

/* -----------------------------
   Document-level batch classifier
-------------------------------- */

export function classifySegmentedQuestions(
  segments: SegmentedQuestions,
  graphics: DocumentGraphics,
  graphFont?: string
): ClassifiedSegments {

  const classified: ClassifiedSegments = [];
  const totalPages = Math.min(segments.length, graphics.length);

  for (let pageIndex = 0; pageIndex < totalPages; pageIndex++) {
    const pageSegments = segments[pageIndex];
    const pageGraphics = graphics[pageIndex];

    if (!pageSegments || !pageGraphics) {
      classified.push([]);
      continue;
    }

    const pageResults: ClassifiedQuestion[] = [];

    for (const segment of pageSegments) {
      const result = classifyQuestion(
        segment,
        pageGraphics,
        graphFont
      );

      pageResults.push({
        ...segment,
        type: result.type,
        confidence: result.confidence,
        scores: result.scores
      });
    }

    classified.push(pageResults);
  }

  return classified;
}