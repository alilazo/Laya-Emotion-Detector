import type { Node, Scores } from "./types";

export const VERTICES = {
  anxiety: { x: 450, y: 50 },
  sadness: { x: 105, y: 440 },
  fear: { x: 795, y: 440 },
};

export function position(weights: Scores) {
  return {
    x:
      weights.anxiety * VERTICES.anxiety.x +
      weights.sadness * VERTICES.sadness.x +
      weights.fear * VERTICES.fear.x,
    y:
      weights.anxiety * VERTICES.anxiety.y +
      weights.sadness * VERTICES.sadness.y +
      weights.fear * VERTICES.fear.y,
  };
}

export function radius(intensity: number) {
  return Math.max(6, Math.min(18, 6 + intensity * 0.12));
}

export function stableOffset(id: string): { x: number; y: number } {
  let hash = 0;
  for (const char of id) hash = (hash * 31 + char.charCodeAt(0)) | 0;
  const angle = (((hash >>> 0) % 360) * Math.PI) / 180;
  const distance = 2 + ((hash >>> 8) % 3);
  return { x: Math.cos(angle) * distance, y: Math.sin(angle) * distance };
}

export function nodePoint(node: Node) {
  const base = position(node.position);
  const jitter = stableOffset(node.chatId);
  return { x: base.x + jitter.x, y: base.y + jitter.y };
}
