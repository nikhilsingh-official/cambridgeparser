export function normalizeWeights(weights: number[]) {
  const sum = weights.reduce((a, b) => a + b, 0);
  if (sum === 0) return new Array(weights.length).fill(1 / weights.length);
  return weights.map((w) => w / sum);
}