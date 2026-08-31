import type { Rect, Vec2 } from "./schema";

export function distance(a: Vec2, b: Vec2): number {
  return Math.hypot(a[0] - b[0], a[1] - b[1]);
}

export function distanceToSegment(point: Vec2, a: Vec2, b: Vec2): number {
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  const lengthSquared = dx * dx + dy * dy;
  if (lengthSquared === 0) return distance(point, a);
  const t = Math.max(0, Math.min(1, ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / lengthSquared));
  return distance(point, [a[0] + t * dx, a[1] + t * dy]);
}

export function distanceToPolyline(point: Vec2, points: Vec2[]): number {
  let closest = Number.POSITIVE_INFINITY;
  for (let index = 0; index < points.length - 1; index += 1) {
    const start = points[index];
    const end = points[index + 1];
    if (start && end) closest = Math.min(closest, distanceToSegment(point, start, end));
  }
  return closest;
}

export function pointInPolygon(point: Vec2, polygon: Vec2[]): boolean {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i, i += 1) {
    const a = polygon[i];
    const b = polygon[j];
    if (!a || !b) continue;
    const intersects = (a[1] > point[1]) !== (b[1] > point[1])
      && point[0] < ((b[0] - a[0]) * (point[1] - a[1])) / (b[1] - a[1]) + a[0];
    if (intersects) inside = !inside;
  }
  return inside;
}

export function polygonBounds(polygon: Vec2[]): { min: Vec2; max: Vec2 } {
  return polygon.reduce(
    (bounds, point) => ({
      min: [Math.min(bounds.min[0], point[0]), Math.min(bounds.min[1], point[1])],
      max: [Math.max(bounds.max[0], point[0]), Math.max(bounds.max[1], point[1])],
    }),
    { min: [Number.POSITIVE_INFINITY, Number.POSITIVE_INFINITY] as Vec2, max: [Number.NEGATIVE_INFINITY, Number.NEGATIVE_INFINITY] as Vec2 },
  );
}

export function pointInRotatedRect(point: Vec2, rect: Rect, padding = 0): boolean {
  const cosine = Math.cos(-rect.rotation);
  const sine = Math.sin(-rect.rotation);
  const dx = point[0] - rect.center[0];
  const dy = point[1] - rect.center[1];
  const localX = dx * cosine - dy * sine;
  const localY = dx * sine + dy * cosine;
  return Math.abs(localX) <= rect.size[0] / 2 + padding && Math.abs(localY) <= rect.size[1] / 2 + padding;
}
