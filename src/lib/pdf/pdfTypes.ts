export interface textbox {
  text: string;
  font: string;
  rawFontName: string;
  x: number;
  y: number;
  x2: number;
  y2: number;
  width: number;
  height: number;
  fontSize: number;
  transform: number[];
}

export interface indexed_textbox extends textbox {
  index: number;
}

export type PageText = textbox[]
export type DocumentText = PageText[]

export type PageQuestionMarkers = indexed_textbox[]
export type DocumentQuestionMarkers = PageQuestionMarkers[];

export type QuestionSegment = {
  segmentText: textbox[];
  averageY: number;
  // the question's true vertical extent, in page coordinates.
  //
  // Consumers used to derive this from segmentText[0] and segmentText[last],
  // which assumes the array is in top-to-bottom order. It is in PDF
  // content-stream order - the order the typesetter drew the items - and a
  // diagram's labels are routinely drawn after the text below them. Computed
  // once in segmentQuestions.ts so every consumer gets the same answer.
  contentY: number;
  contentY2: number;
};

export type PageSegments = QuestionSegment[];
export type SegmentedQuestions = PageSegments[];

export type OptionMarker = {
  text: "A" | "B" | "C" | "D";
  index: number;
};
export type SegmentOptionMarkers = OptionMarker[];

export type OptionText = textbox[];
export type SegmentOptionsText = OptionText[];
export type PageOptionsText = SegmentOptionsText[];
export type DocumentOptionsText = PageOptionsText[];
export interface GraphicsItem {
  fnId: number;
  // was `any[]`. pdf.js operator arguments are a positional, op-specific
  // tuple of numbers, strings, typed arrays or nested arrays - `unknown[]`
  // states that honestly and forces a cast at each use site, where the op is
  // known. Consumers index it as args[0], args[1] after checking fnId.
  args: unknown[];
  name?: string;
}
export interface BoundingBox {
  x: number;
  y: number;
  x2: number;
  y2: number;
}
export type PageGraphics = GraphicsItem[]
export type DocumentGraphics = PageGraphics[];
export type PageBoundingBoxes = BoundingBox[]
export type DocumentBoundingBoxes = PageBoundingBoxes[]

export type ClassifiedQuestion = QuestionSegment & {
  type: "text" | "table" | "graph";
  confidence: number;
  scores: {
    text: number;
    table: number;
    graph: number;
  };
};

export type ClassifiedSegments = ClassifiedQuestion[][];