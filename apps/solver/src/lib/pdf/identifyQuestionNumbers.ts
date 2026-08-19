import type { DocumentText, DocumentQuestionMarkers, textbox, PageText, indexed_textbox } from "@/lib/pdf/pdfTypes";

export function identifyQuestionNumbers(totalText: DocumentText): DocumentQuestionMarkers {
  const hashmap = new Map<number, textbox[]>();
  const leeway = 0.5;

  totalText.forEach((pageText: PageText) => {
    const filteredPgTxt: textbox[] = pageText.filter((item: textbox) => !isNaN(Number(item.text)));

    filteredPgTxt.forEach((obj: textbox) => {
      let matchedKey: number | null = null;

      for (let [key, _] of hashmap) {
        if (Math.abs(key - obj.x) <= leeway) {
          matchedKey = key;
          break;
        }
      }

      if (matchedKey !== null) {
        hashmap.get(matchedKey)!.push(obj);
      } else {
        hashmap.set(Math.round(obj.x), [obj]);
      }
    });
  });

  let maxLenKey: number = -1;
  let maxLenVal: number = -1;

  hashmap.forEach((value, key) => {
    if (value.length > maxLenVal) {
      maxLenVal = value.length;
      maxLenKey = key;
    }
  });

  const question_numbers: DocumentQuestionMarkers = totalText.map(page => {
    return page
      // this listed seven fields by hand, so the result was missing
      // rawFontName/width/height/fontSize/transform and did NOT satisfy
      // indexed_textbox - which is what the declared DocumentQuestionMarkers
      // return type claims. The filter below then re-annotated its parameter as
      // indexed_textbox, papering over the gap. Spreading the source textbox
      // makes the value genuinely match the declared type.
      .map((item: textbox, index: number): indexed_textbox => ({
        ...item,
        index,
      }))
      .filter((item: indexed_textbox) =>
        !isNaN(Number(item.text)) &&
        item.x > maxLenKey - leeway &&
        item.x < maxLenKey + leeway
      );
  });

  return question_numbers;
}