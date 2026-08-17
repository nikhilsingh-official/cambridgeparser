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
  args: any[];
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