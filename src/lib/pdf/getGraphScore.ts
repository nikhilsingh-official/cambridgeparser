import { OPS } from "pdfjs-dist";
import type {
  DocumentText,
  DocumentGraphics,
  PageGraphics
} from "@/lib/pdf/pdfTypes";

type FontStats = {
  pagesWithFont: Set<number>;
  graphEvidence: number;
};

type GraphicsProfile = {
  stroke: number;
  rectangle: number;
};

function getGraphicsProfile(pageGraphics: PageGraphics): GraphicsProfile {
  const profile = { stroke: 0, rectangle: 0 };

  for (const g of pageGraphics) {
    if (g.fnId === OPS.stroke || g.fnId === OPS.fill) {
      profile.stroke++;
    } else if (g.fnId === OPS.rectangle) {
      profile.rectangle++;
    }
  }

  return profile;
}

function graphLikenessScore(profile: GraphicsProfile): number {
  const { stroke, rectangle } = profile;
  console.log("RECTANGLE")
  console.log(rectangle)
  if (stroke + rectangle === 0) return 0;

  const strokeRatio = stroke / (stroke + rectangle + 1);

  const structurePenalty =
    rectangle > 0 ? stroke / (rectangle + 1) : stroke;

  return Math.log1p(stroke) * strokeRatio * structurePenalty;
}

export function getGraphScore(
  text: DocumentText,
  graphics: DocumentGraphics
): Record<string, number> {

  const fontStats: Record<string, FontStats> = {};
  const totalPages = Math.min(text.length, graphics.length);

  for (let p = 1; p < totalPages; p++) {
    const pageText = text[p];
    const pageGraphics = graphics[p];
    if (!pageText || !pageGraphics) continue;

    const pageGraphScore = graphLikenessScore(
      getGraphicsProfile(pageGraphics)
    );

    if (pageGraphScore <= 0) continue;

    const fontCounts = new Map<string, number>();
    for (const t of pageText) {
      fontCounts.set(t.font, (fontCounts.get(t.font) ?? 0) + 1);
    }

    const totalGlyphs = [...fontCounts.values()]
      .reduce((a, b) => a + b, 0);

    for (const [font, count] of fontCounts) {
      if (!fontStats[font]) {
        fontStats[font] = {
          pagesWithFont: new Set(),
          graphEvidence: 0
        };
      }

      fontStats[font].pagesWithFont.add(p);

      const localWeight = count / totalGlyphs;

      fontStats[font].graphEvidence +=
        pageGraphScore * localWeight;
    }
  }

  const scores: Record<string, number> = {};

  for (const [font, stats] of Object.entries(fontStats)) {
    const pf = stats.pagesWithFont.size;
    const ge = stats.graphEvidence;

    if (pf === 0 || ge === 0) continue;

    const pageCoverage = pf / totalPages;
    const idf = Math.log(1 + totalPages / (1 + pf));

    const rarityDamping = Math.sqrt(pf);

    scores[font] =
      (ge / rarityDamping) *
      (1 - pageCoverage) *
      idf;
  }

  return scores;
}
