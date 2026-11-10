export function formatDate(value) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

export function formatDateTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString(undefined, {
    year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

export function formatCurrency(value) {
  const n = Number(value);
  if (Number.isNaN(n)) return value;
  return new Intl.NumberFormat(undefined, { style: "currency", currency: "USD" }).format(n);
}

export function titleCase(value) {
  if (!value) return "";
  return String(value)
    .replace(/_/g, " ")
    .replace(/\w\S*/g, (t) => t.charAt(0).toUpperCase() + t.slice(1).toLowerCase());
}

export function fullName(person) {
  const u = person?.user || person;
  return `${u?.first_name || ""} ${u?.last_name || ""}`.trim();
}

export function pct(part, whole, digits = 1) {
  if (!whole) return "—";
  return `${((part / whole) * 100).toFixed(digits)}%`;
}

export function countBy(list, keyFn) {
  const map = new Map();
  list.forEach((item) => {
    const k = keyFn(item);
    map.set(k, (map.get(k) || 0) + 1);
  });
  return map;
}
