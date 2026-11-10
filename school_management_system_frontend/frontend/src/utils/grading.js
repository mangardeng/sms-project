/** Helpers for showing grades; the server is the source of truth, this mirrors it for live feedback. */

/** scale: [{ min_percentage, grade, remark }] (any order). Returns { grade, remark } or null. */
export function gradeFor(percentage, scale) {
  if (percentage == null || Number.isNaN(Number(percentage)) || !scale?.length) return null;
  const sorted = [...scale].sort((a, b) => Number(b.min_percentage) - Number(a.min_percentage));
  const hit = sorted.find((row) => Number(percentage) >= Number(row.min_percentage)) || sorted[sorted.length - 1];
  return { grade: hit.grade, remark: hit.remark };
}

export function gradeTone(grade) {
  if (!grade) return "neutral";
  if (grade === "A" || grade === "B") return "accent";
  if (grade === "C" || grade === "D") return "gold";
  if (grade === "E") return "info";
  return "alert";
}

export function formatPercent(value, digits = 1) {
  if (value === null || value === undefined || value === "") return "—";
  const n = Number(value);
  return Number.isNaN(n) ? "—" : `${n.toFixed(digits)}%`;
}

export function ordinal(n) {
  if (!n) return "—";
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return `${n}${s[(v - 20) % 10] || s[v] || s[0]}`;
}

/** "36 / 40" style text for a score and what it was out of; falls back to a percentage. */
export function scoreText(points, outOf, percentage) {
  if (points === null || points === undefined || outOf === null || outOf === undefined) {
    return formatPercent(percentage);
  }
  return `${Number(points)} / ${Number(outOf)}`;
}
