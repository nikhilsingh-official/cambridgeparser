import type { OptionLetter } from "../processing/processingTypes";

export const letterToIndex = (letter: OptionLetter | undefined) => {
  if (!letter) return null;
  const L: OptionLetter = letter.toString().toUpperCase() as OptionLetter;
  const map: Record<OptionLetter, number> = { A:0, B:1, C:2, D:3 };
  return map[L] ?? null;
};