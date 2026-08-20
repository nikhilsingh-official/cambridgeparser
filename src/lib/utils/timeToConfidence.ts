import { sigmoid } from "./sigmoid";

export function timeToConfidence(norm: number, k: number, meanNorm: number, stdNorm: number) {
  if (stdNorm < 1e-6) return sigmoid(k * (norm - meanNorm));
  const z = (norm - meanNorm) / stdNorm;
  return sigmoid(-z * k);
}