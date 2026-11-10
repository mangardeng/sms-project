export const SCHOOL_NAME = "Bright Star Academy";

export function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

const PRINT_CSS = `
  @page { size: A4; margin: 14mm; }
  * { box-sizing: border-box; }
  body { font-family: "Inter", -apple-system, "Segoe UI", Arial, sans-serif; color: #1b2333; font-size: 11.5px; line-height: 1.45; margin: 0; }
  .doc-head { display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 2px solid #16223b; padding-bottom: 8px; margin-bottom: 14px; }
  .school { font-family: Georgia, "Times New Roman", serif; font-size: 20px; font-weight: 700; color: #16223b; }
  .doc-title { font-family: Georgia, "Times New Roman", serif; font-size: 15px; margin-top: 2px; }
  .doc-sub { color: #5c6577; font-size: 11px; }
  .meta { text-align: right; color: #5c6577; font-size: 10.5px; }
  .stats { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 14px; }
  .stat { border: 1px solid #c3c9bd; border-radius: 4px; padding: 6px 12px; min-width: 110px; }
  .stat b { display: block; font-size: 16px; color: #16223b; }
  .stat span { color: #5c6577; font-size: 10px; text-transform: uppercase; letter-spacing: .03em; }
  h2 { font-family: Georgia, "Times New Roman", serif; font-size: 13.5px; margin: 16px 0 6px; color: #16223b; }
  table { width: 100%; border-collapse: collapse; margin-bottom: 8px; font-variant-numeric: tabular-nums; }
  th, td { border: 1px solid #c3c9bd; padding: 4px 7px; text-align: left; vertical-align: top; }
  th { background: #eef1f6; font-size: 10.5px; text-transform: uppercase; letter-spacing: .02em; }
  tr { page-break-inside: avoid; }
  thead { display: table-header-group; }
  td.num, th.num { text-align: right; }
  tfoot td { font-weight: 700; background: #f6f7f4; }
  .empty { color: #5c6577; font-style: italic; margin: 4px 0 10px; }
  .filters { color: #5c6577; font-size: 10.5px; margin-bottom: 10px; }
  .foot { margin-top: 18px; border-top: 1px solid #c3c9bd; padding-top: 6px; color: #5c6577; font-size: 10px; display: flex; justify-content: space-between; }
  .sign { display: flex; gap: 40px; margin-top: 38px; }
  .sign div { flex: 1; border-top: 1px solid #1b2333; padding-top: 4px; font-size: 10.5px; color: #5c6577; }
  .receipt { max-width: 520px; margin: 0 auto; }
  .receipt dl { margin: 0; }
  .receipt .row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px dashed #c3c9bd; }
  .receipt .row span:first-child { color: #5c6577; }
  .receipt .amount { font-size: 22px; font-weight: 700; text-align: center; margin: 14px 0; border: 2px solid #16223b; padding: 8px; border-radius: 4px; }
  .photo { width: 84px; height: 84px; object-fit: cover; border-radius: 4px; border: 1px solid #c3c9bd; }
`;

export function formatStamp(date = new Date()) {
  return date.toLocaleString(undefined, { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function cellHtml(value) {
  if (value === null || value === undefined || value === "") return "—";
  return escapeHtml(value);
}

/** columns: [{ label, value: (row) => string|number, align?: "right" }] */
export function tableHtml(columns, rows, footer) {
  if (!rows || !rows.length) return `<p class="empty">No records for this selection.</p>`;
  const head = columns.map((c) => `<th class="${c.align === "right" ? "num" : ""}">${escapeHtml(c.label)}</th>`).join("");
  const body = rows
    .map(
      (row) =>
        `<tr>${columns.map((c) => `<td class="${c.align === "right" ? "num" : ""}">${cellHtml(c.value(row))}</td>`).join("")}</tr>`
    )
    .join("");
  const foot = footer
    ? `<tfoot><tr>${columns.map((c, i) => `<td class="${c.align === "right" ? "num" : ""}">${escapeHtml(footer[i] ?? "")}</td>`).join("")}</tr></tfoot>`
    : "";
  return `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody>${foot}</table>`;
}

export function buildReportHtml({ title, subtitle, filterSummary, stats = [], sections = [], printedBy }) {
  const statsHtml = stats.length
    ? `<div class="stats">${stats.map((s) => `<div class="stat"><b>${escapeHtml(s.value ?? "—")}</b><span>${escapeHtml(s.label)}</span></div>`).join("")}</div>`
    : "";
  const sectionsHtml = sections
    .map((s) => `${s.heading ? `<h2>${escapeHtml(s.heading)}</h2>` : ""}${tableHtml(s.columns, s.rows, s.footer)}`)
    .join("");
  return documentShell({
    title,
    body: `
      <div class="doc-head">
        <div>
          <div class="school">${escapeHtml(SCHOOL_NAME)}</div>
          <div class="doc-title">${escapeHtml(title)}</div>
          ${subtitle ? `<div class="doc-sub">${escapeHtml(subtitle)}</div>` : ""}
        </div>
        <div class="meta">Generated ${escapeHtml(formatStamp())}${printedBy ? `<br/>by ${escapeHtml(printedBy)}` : ""}</div>
      </div>
      ${filterSummary ? `<div class="filters">${escapeHtml(filterSummary)}</div>` : ""}
      ${statsHtml}
      ${sectionsHtml}
      <div class="foot"><span>${escapeHtml(SCHOOL_NAME)} — School Management System</span><span>Confidential: for school use</span></div>
    `,
  });
}

export function documentShell({ title, body }) {
  return `<!doctype html><html><head><meta charset="utf-8"/><title>${escapeHtml(title)}</title><style>${PRINT_CSS}</style></head><body>${body}</body></html>`;
}

/**
 * Prints an HTML document through a hidden iframe (no popup, so popup blockers can't stop it).
 */
export function printHtml(html) {
  document.querySelectorAll("iframe[data-print-frame]").forEach((old) => old.remove());
  const iframe = document.createElement("iframe");
  iframe.setAttribute("data-print-frame", "true");
  iframe.setAttribute("aria-hidden", "true");
  iframe.style.cssText = "position:fixed;right:0;bottom:0;width:0;height:0;border:0;visibility:hidden;";
  document.body.appendChild(iframe);
  const doc = iframe.contentWindow.document;
  doc.open();
  doc.write(html);
  doc.close();

  const cleanup = () => setTimeout(() => iframe.parentNode && iframe.parentNode.removeChild(iframe), 500);
  const run = () => {
    try {
      iframe.contentWindow.focus();
      iframe.contentWindow.addEventListener("afterprint", cleanup);
      iframe.contentWindow.print();
    } finally {
      setTimeout(cleanup, 60000);
    }
  };
  // Give images (e.g. a student photo) a moment to load, then print.
  const imgs = Array.from(doc.images || []);
  if (!imgs.length) setTimeout(run, 50);
  else {
    let pending = imgs.length;
    const done = () => {
      pending -= 1;
      if (pending <= 0) run();
    };
    imgs.forEach((img) => (img.complete ? done() : ((img.onload = done), (img.onerror = done))));
    setTimeout(() => pending > 0 && run(), 2500);
  }
}

export function printReport(config) {
  printHtml(buildReportHtml(config));
}

function csvCell(v) {
  const s = v === null || v === undefined ? "" : String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

/** sections: [{ heading, columns, rows }] -> downloads a UTF-8 CSV that Excel opens correctly. */
export function downloadCsv(filename, sections) {
  const lines = [];
  sections.forEach((s, i) => {
    if (i > 0) lines.push("");
    if (s.heading) lines.push(csvCell(s.heading));
    lines.push(s.columns.map((c) => csvCell(c.label)).join(","));
    s.rows.forEach((r) => lines.push(s.columns.map((c) => csvCell(c.value(r))).join(",")));
  });
  const blob = new Blob(["\ufeff" + lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename.endsWith(".csv") ? filename : `${filename}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
