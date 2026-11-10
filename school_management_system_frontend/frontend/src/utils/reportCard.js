import { escapeHtml, SCHOOL_NAME } from "./print";

const num = (value) => (value === null || value === undefined || value === "" ? "–" : String(Number(value)));

const ordinalOf = (n) => {
  if (!n) return "–";
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return `${n}${s[(v - 20) % 10] || s[v] || s[0]}`;
};

const formatDate = (value) => (value ? new Date(value).toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" }) : "");

export const REPORT_CARD_CSS = `
  .rc { font-family: Georgia, "Times New Roman", serif; color: #111; background: #fff; border: 3px double #16223b; padding: 16px 18px; max-width: 760px; margin: 0 auto; font-size: 12.5px; line-height: 1.4; }
  .rc * { box-sizing: border-box; }
  .rc-head { display: flex; align-items: center; gap: 14px; border-bottom: 3px solid #16223b; padding-bottom: 10px; }
  .rc-logo { width: 62px; height: 62px; border: 2px solid #16223b; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 30px; color: #16223b; flex: none; }
  .rc-title { flex: 1; text-align: center; }
  .rc-title h1 { margin: 0; font-size: 24px; letter-spacing: .06em; text-transform: uppercase; color: #16223b; }
  .rc-title .rc-sub { font-weight: 700; font-size: 13.5px; letter-spacing: .04em; margin-top: 3px; text-transform: uppercase; }
  .rc-title .rc-term { font-size: 12px; margin-top: 2px; }
  .rc-photo { width: 64px; height: 76px; border: 1px solid #555; display: flex; align-items: center; justify-content: center; font-size: 9px; color: #777; text-align: center; flex: none; }
  .rc table { width: 100%; border-collapse: collapse; }
  .rc th, .rc td { border: 1px solid #333; padding: 4px 7px; vertical-align: middle; }
  .rc-info { margin-top: 10px; }
  .rc-info td { width: 25%; }
  .rc-info b { text-transform: uppercase; font-size: 10.5px; letter-spacing: .03em; color: #444; display: block; font-weight: 600; }
  .rc-info span { font-size: 13px; font-weight: 700; }
  .rc-marks { margin-top: 12px; text-align: center; font-variant-numeric: tabular-nums; }
  .rc-marks th { background: #e9edf5; font-size: 11.5px; text-transform: uppercase; letter-spacing: .02em; }
  .rc-marks td.l, .rc-marks th.l { text-align: left; }
  .rc-marks td.subject { font-weight: 700; }
  .rc-marks tfoot td { background: #f1f3f8; font-weight: 700; }
  .rc-summary { display: flex; margin-top: 12px; border: 1px solid #333; }
  .rc-summary div { flex: 1; text-align: center; padding: 6px 4px; border-right: 1px solid #333; }
  .rc-summary div:last-child { border-right: 0; }
  .rc-summary b { display: block; font-size: 18px; color: #16223b; }
  .rc-summary span { font-size: 10px; text-transform: uppercase; letter-spacing: .03em; color: #444; }
  .rc-key { margin-top: 12px; font-size: 11px; text-align: center; }
  .rc-key th, .rc-key td { padding: 3px 6px; }
  .rc-key caption { text-align: left; font-weight: 700; padding-bottom: 3px; text-transform: uppercase; font-size: 11px; letter-spacing: .03em; }
  .rc-comments { margin-top: 14px; }
  .rc-line { margin-top: 12px; display: flex; align-items: flex-end; gap: 8px; }
  .rc-line label { font-weight: 700; white-space: nowrap; }
  .rc-line .fill { flex: 1; border-bottom: 1px solid #333; min-height: 18px; }
  .rc-foot { display: flex; gap: 22px; margin-top: 18px; align-items: flex-end; }
  .rc-foot .sig { flex: 1; border-top: 1px solid #333; padding-top: 3px; font-size: 11px; }
  .rc-stamp { width: 84px; height: 64px; border: 1px dashed #777; text-align: center; font-size: 9px; color: #777; display: flex; align-items: center; justify-content: center; flex: none; }
  .rc-note { margin-top: 8px; font-size: 10.5px; color: #555; font-style: italic; }
`;

/** Builds the school examination card (HTML) for one student and one term. */
export function buildReportCardHtml(card, scale = []) {
  const subjects = card.subjects || [];
  const midOut = subjects.find((s) => s.midterm_out_of != null)?.midterm_out_of ?? 40;
  const endOut = subjects.find((s) => s.endterm_out_of != null)?.endterm_out_of ?? 60;
  const totalOut = Number(midOut) + Number(endOut);
  const provisional = !card.is_complete;

  const sum = (key) => subjects.reduce((acc, s) => acc + (s[key] != null ? Number(s[key]) : 0), 0);

  const rows = subjects
    .map(
      (s, i) => `<tr>
        <td>${i + 1}</td>
        <td class="l subject">${escapeHtml(s.subject_name)}</td>
        <td>${num(s.midterm_points)}</td>
        <td>${num(s.endterm_points)}</td>
        <td><b>${num(s.final_percentage)}${s.is_complete ? "" : "*"}</b></td>
        <td><b>${escapeHtml(s.grade)}</b></td>
        <td class="l">${escapeHtml(s.remark || "")}</td>
        <td>${ordinalOf(s.position)}</td>
      </tr>`
    )
    .join("");

  const sorted = [...scale].sort((a, b) => Number(b.min_percentage) - Number(a.min_percentage));
  const keyCells = sorted.map((row, i) => {
    const upper = i === 0 ? 100 : Number(sorted[i - 1].min_percentage) - 0.01;
    const range = i === 0 ? `${Number(row.min_percentage)} – 100` : `${Number(row.min_percentage)} – ${upper.toFixed(0) === String(upper) ? upper : Math.floor(upper)}`;
    return { grade: row.grade, range, remark: row.remark };
  });
  const keyHtml = keyCells.length
    ? `<table class="rc-key"><caption>Grading key</caption>
        <tr><th>Grade</th>${keyCells.map((k) => `<td><b>${escapeHtml(k.grade)}</b></td>`).join("")}</tr>
        <tr><th>Marks (%)</th>${keyCells.map((k) => `<td>${escapeHtml(k.range)}</td>`).join("")}</tr>
        <tr><th>Remark</th>${keyCells.map((k) => `<td>${escapeHtml(k.remark || "")}</td>`).join("")}</tr>
      </table>`
    : "";

  const termLabel = card.term_name ? card.term_name.split(" - ")[0] : "";

  return `<div class="rc">
    <div class="rc-head">
      <div class="rc-logo">★</div>
      <div class="rc-title">
        <h1>${escapeHtml(SCHOOL_NAME)}</h1>
        <div class="rc-sub">End of Term Examination Report Card</div>
        <div class="rc-term">${escapeHtml(termLabel)}${card.academic_year_name ? ` · Academic Year ${escapeHtml(card.academic_year_name)}` : ""}</div>
      </div>
      <div class="rc-photo">Student<br/>photo</div>
    </div>

    <table class="rc-info">
      <tr>
        <td colspan="2"><b>Name of student</b><span>${escapeHtml(card.student_name)}</span></td>
        <td><b>Index / Admission no.</b><span>${escapeHtml(card.student_index_number)}</span></td>
        <td><b>Class</b><span>${escapeHtml(card.school_class_name)}</span></td>
      </tr>
      <tr>
        <td><b>Gender</b><span>${escapeHtml(card.gender || "")}&nbsp;</span></td>
        <td><b>Number in class</b><span>${escapeHtml(card.class_size)}</span></td>
        <td><b>Position in class</b><span>${ordinalOf(card.position)} of ${escapeHtml(card.class_size)}</span></td>
        <td><b>Class teacher</b><span>${escapeHtml(card.class_teacher_name || "")}&nbsp;</span></td>
      </tr>
    </table>

    <table class="rc-marks">
      <thead>
        <tr><th rowspan="2">No.</th><th rowspan="2" class="l">Subject</th><th>Mid-Term</th><th>End of Term</th><th>Total</th><th rowspan="2">Grade</th><th rowspan="2" class="l">Remarks</th><th rowspan="2">Pos.</th></tr>
        <tr><th>/ ${num(midOut)}</th><th>/ ${num(endOut)}</th><th>/ ${totalOut}</th></tr>
      </thead>
      <tbody>${rows}</tbody>
      <tfoot>
        <tr><td colspan="2" class="l">TOTAL</td><td>${num(sum("midterm_points"))}</td><td>${num(sum("endterm_points"))}</td><td>${num(card.total_score)}</td><td colspan="3" class="l">out of ${card.subjects_count * 100}</td></tr>
      </tfoot>
    </table>

    <div class="rc-summary">
      <div><b>${num(card.total_score)} / ${card.subjects_count * 100}</b><span>Total marks</span></div>
      <div><b>${num(card.average_percentage)}%</b><span>Average</span></div>
      <div><b>${escapeHtml(card.grade)}</b><span>Overall grade${card.remark ? ` — ${escapeHtml(card.remark)}` : ""}</span></div>
      <div><b>${ordinalOf(card.position)} / ${escapeHtml(card.class_size)}</b><span>Class position</span></div>
    </div>
    ${provisional ? `<div class="rc-note">* Provisional: end-of-term marks are not all entered yet, so these results may still change.</div>` : ""}

    ${keyHtml}

    <div class="rc-comments">
      <div class="rc-line"><label>Class teacher's comment:</label><span class="fill"></span></div>
      <div class="rc-line"><span class="fill"></span></div>
      <div class="rc-line"><label>Head teacher's comment:</label><span class="fill"></span></div>
      <div class="rc-line"><span class="fill"></span></div>
      <div class="rc-line"><label>Next term begins on:</label><span class="fill"></span><label>Date issued:</label><span class="fill"></span></div>
    </div>

    <div class="rc-foot">
      <div class="sig">Class teacher's signature</div>
      <div class="sig">Head teacher's signature</div>
      <div class="sig">Parent / guardian's signature</div>
      <div class="rc-stamp">School<br/>stamp</div>
    </div>
  </div>`;
}

/** A complete printable A4 document for the card. */
export function buildReportCardDocument(card, scale) {
  return `<!doctype html><html><head><meta charset="utf-8"/><title>Report card - ${escapeHtml(card.student_name)}</title>
    <style>@page { size: A4; margin: 10mm; } body { margin: 0; } ${REPORT_CARD_CSS} .rc { border-width: 3px; max-width: none; }</style>
    </head><body>${buildReportCardHtml(card, scale)}</body></html>`;
}
