import type { DocumentGraphics, DocumentText } from "@/lib/pdf/pdfTypes";
import { getGraphScore } from "@/lib/pdf/getGraphScore";

export function getGraphFont(
  totalText: DocumentText,
  graphics: DocumentGraphics
) {
  const filteredText = totalText.slice(1);
  const filteredGraphics = graphics.slice(1);

  const fontScores = getGraphScore(filteredText, filteredGraphics);

  console.log("Fonts with probability of being graph font");
  console.log(fontScores);

  const entries = Object.entries(fontScores);
  if (entries.length === 0) return;

  return entries.reduce((best, curr) =>
    curr[1] > best[1] ? curr : best
  )[0];
}