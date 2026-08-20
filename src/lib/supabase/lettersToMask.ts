import type { OptionLetter } from "../processing/processingTypes";
import { letterToIndex } from "./letterToIndex";

export const lettersToMask = (letters: OptionLetter[] | undefined) => {
  if (!Array.isArray(letters) || letters.length === 0) return 0;
  return letters.reduce((mask, l) => {
    const i = letterToIndex(l);
    if (i === null) return mask;
    return mask | (1 << i);
  }, 0);
};