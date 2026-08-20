export function findOptimalSteepness(values: number[]) {
  if (!values.length) return 1;
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  const variance = values.reduce((s, v) => s + (v - mean) ** 2, 0) / values.length;
  const std = Math.sqrt(variance);
  if (std < 1e-6) return 1;
  const scaleFactor = 2.5;
  return 1 / (scaleFactor * std);
}