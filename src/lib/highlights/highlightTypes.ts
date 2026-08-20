export type OptionState = "correct" | "eliminated" | "neutral";
export type Highlight = { x: number; y: number; x2: number; y2: number; state: OptionState; el?: HTMLElement }
export type OptionHighlights = Highlight[]
export type SegmentHighlights = OptionHighlights[]
export type PageHighlights = SegmentHighlights[]
export type DocumentHighlights = PageHighlights[]