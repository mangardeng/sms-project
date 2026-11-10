import { useEffect, useMemo, useState } from "react";

import { termsApi } from "../../api/academic";
import { extractErrorMessage } from "../../api/client";
import { gradeScaleApi, subjectSheetApi } from "../../api/examinations";
import AlertBanner from "../../components/AlertBanner";
import Badge from "../../components/Badge";
import LoadingSpinner from "../../components/LoadingSpinner";
import { useAuth } from "../../context/AuthContext";
import { formatPercent, gradeFor, gradeTone, ordinal } from "../../utils/grading";
import { printReport } from "../../utils/print";

const num = (v) => (v === "" || v === null || v === undefined ? null : Number(v));

/**
 * Subject results sheet. The subject teacher (or an administrator) types each student's midterm and
 * end-of-term marks. The total, percentage, grade, remark and class positions are worked out
 * automatically - the teacher may only add a remark of their own. Mistakes can be fixed here at any
 * time, even after publishing (a reason is then asked for and kept in the audit trail).
 */
export default function SubjectSheetPanel() {
  const { user } = useAuth();
  const [options, setOptions] = useState([]);
  const [terms, setTerms] = useState([]);
  const [scale, setScale] = useState([]);
  const [choice, setChoice] = useState("");
  const [termId, setTermId] = useState("");
  const [sheet, setSheet] = useState(null);
  const [edits, setEdits] = useState({});
  const [outOf, setOutOf] = useState({ mid: "", end: "" });
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [booting, setBooting] = useState(true);

  useEffect(() => {
    Promise.all([subjectSheetApi.options(), termsApi.list({ page_size: 50 }), gradeScaleApi.list({ page_size: 50 })])
      .then(([opts, termData, scaleData]) => {
        setOptions(opts);
        const termList = termData.results || termData;
        setTerms(termList);
        setScale(scaleData.results || scaleData);
        if (opts.length) setChoice(`${opts[0].school_class}:${opts[0].subject}`);
        const current = termList.find((t) => t.is_current) || termList[0];
        if (current) setTermId(String(current.id));
      })
      .catch((err) => setError(extractErrorMessage(err, "Could not load your classes and subjects.")))
      .finally(() => setBooting(false));
  }, []);

  function applySheet(data) {
    setSheet(data);
    const map = {};
    data.rows.forEach((r) => {
      map[r.student] = {
        midterm_marks: r.midterm_marks ?? "",
        endterm_marks: r.endterm_marks ?? "",
        remark: r.teacher_remark ?? "",
      };
    });
    setEdits(map);
    setOutOf({ mid: String(Number(data.midterm.out_of)), end: String(Number(data.endterm.out_of)) });
    setReason("");
  }

  useEffect(() => {
    if (!choice || !termId) return undefined;
    const [school_class, subject] = choice.split(":");
    let cancelled = false;
    setLoading(true);
    setError("");
    setSuccess("");
    subjectSheetApi
      .get({ school_class, subject, term: termId })
      .then((data) => !cancelled && applySheet(data))
      .catch((err) => !cancelled && (setSheet(null), setError(extractErrorMessage(err))))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [choice, termId]);

  const midOut = Number(outOf.mid) || 0;
  const endOut = Number(outOf.end) || 0;
  const published = Boolean(sheet && (sheet.midterm.is_published || sheet.endterm.is_published));

  function change(studentId, field, value) {
    setSuccess("");
    setEdits((prev) => ({ ...prev, [studentId]: { ...prev[studentId], [field]: value } }));
  }

  // Live preview of exactly what the server will calculate.
  const live = useMemo(() => {
    const out = {};
    (sheet?.rows || []).forEach((row) => {
      const e = edits[row.student] || {};
      const mid = num(e.midterm_marks);
      const end = num(e.endterm_marks);
      const midBad = mid !== null && (Number.isNaN(mid) || mid < 0 || mid > midOut);
      const endBad = end !== null && (Number.isNaN(end) || end < 0 || end > endOut);
      let total = null;
      let pct = null;
      if (!midBad && !endBad && (mid !== null || end !== null)) {
        const marks = (mid ?? 0) + (end ?? 0);
        const possible = (mid !== null ? midOut : 0) + (end !== null ? endOut : 0);
        total = marks;
        pct = possible ? (marks / possible) * 100 : null;
      }
      out[row.student] = { midBad, endBad, total, pct, graded: gradeFor(pct, scale), complete: mid !== null && end !== null };
    });
    return out;
  }, [sheet, edits, midOut, endOut, scale]);

  const anyBad = Object.values(live).some((l) => l.midBad || l.endBad);
  const graded = Object.values(live).filter((l) => l.pct !== null);
  const average = graded.length ? graded.reduce((a, l) => a + l.pct, 0) / graded.length : null;

  async function handleSave() {
    if (anyBad) {
      setError("Some marks are above the maximum or negative. Fix the highlighted marks first.");
      return;
    }
    if (published && !reason.trim()) {
      setError("These results are already published. Give a short reason for the correction (for example: typing mistake).");
      return;
    }
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const [school_class, subject] = choice.split(":");
      const data = await subjectSheetApi.save({
        school_class,
        subject,
        term: termId,
        midterm_out_of: outOf.mid,
        endterm_out_of: outOf.end,
        reason,
        entries: sheet.rows.map((r) => ({
          student: r.student,
          midterm_marks: edits[r.student].midterm_marks,
          endterm_marks: edits[r.student].endterm_marks,
          remark: edits[r.student].remark,
        })),
      });
      applySheet(data);
      setSuccess("Saved. Totals, grades, remarks and class positions have been updated automatically.");
    } catch (err) {
      setError(extractErrorMessage(err, "Could not save these results."));
    } finally {
      setSaving(false);
    }
  }

  function handlePrint() {
    printReport({
      title: `Subject Results — ${sheet.subject_name}`,
      subtitle: `${sheet.school_class_name} · ${sheet.term_name}`,
      sections: [
        {
          columns: [
            { label: "Index No.", value: (r) => r.student.student_index_number },
            { label: "Student", value: (r) => r.student.student_name },
            { label: `Midterm /${midOut}`, value: (r) => edits[r.student.student]?.midterm_marks, align: "right" },
            { label: `End of term /${endOut}`, value: (r) => edits[r.student.student]?.endterm_marks, align: "right" },
            { label: `Total /${midOut + endOut}`, value: (r) => (r.live.total !== null ? Number(r.live.total.toFixed(2)) : ""), align: "right" },
            { label: "%", value: (r) => (r.live.pct !== null ? r.live.pct.toFixed(1) : ""), align: "right" },
            { label: "Grade", value: (r) => r.live.graded?.grade || "" },
            { label: "Remark", value: (r) => edits[r.student.student]?.remark || r.live.graded?.remark || "" },
            { label: "Pos.", value: (r) => ordinal(r.student.position) },
          ],
          rows: sheet.rows.map((student) => ({ student, live: live[student.student] })),
        },
      ],
      printedBy: `${user?.first_name || ""} ${user?.last_name || ""}`.trim() || user?.username,
    });
  }

  if (booting) return <LoadingSpinner ink />;

  const canEdit = Boolean(sheet?.can_edit);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Subject results</h1>
          <div className="subtitle">
            Type the midterm and end-of-term marks. The total, percentage, grade, remark and position are worked out for you, and you can
            correct a mistake here at any time.
          </div>
        </div>
      </div>

      {options.length === 0 ? (
        <AlertBanner type="error">
          You are not assigned to teach a subject yet, so there are no subject results to enter. Ask the administrator to assign you to your
          subjects in Class subjects.
        </AlertBanner>
      ) : (
        <div className="toolbar">
          <select value={choice} onChange={(e) => setChoice(e.target.value)}>
            {options.map((o) => (
              <option key={`${o.school_class}:${o.subject}`} value={`${o.school_class}:${o.subject}`}>
                {o.school_class_name} — {o.subject_name}
              </option>
            ))}
          </select>
          <select value={termId} onChange={(e) => setTermId(e.target.value)}>
            {terms.map((t) => (
              <option key={t.id} value={t.id}>
                {t.display_name || `${t.name} — ${t.academic_year_name}`}
              </option>
            ))}
          </select>
          {sheet && (
            <button className="btn btn-secondary btn-sm" type="button" onClick={handlePrint} disabled={loading}>
              🖨 Print
            </button>
          )}
        </div>
      )}

      <AlertBanner type="error">{error}</AlertBanner>
      <AlertBanner type="success">{success}</AlertBanner>

      {loading ? (
        <LoadingSpinner ink />
      ) : sheet ? (
        <>
          {published && (
            <p className="hint" style={{ marginTop: 0 }}>
              Some of these results are published. You can still correct them; the change is recorded with your reason.
            </p>
          )}
          <div className="surface">
            <div className="data-table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Student</th>
                    <th>
                      Midterm / {canEdit ? <input type="number" min="1" style={{ width: 56 }} value={outOf.mid} onChange={(e) => setOutOf({ ...outOf, mid: e.target.value })} /> : midOut}
                    </th>
                    <th>
                      End of term / {canEdit ? <input type="number" min="1" style={{ width: 56 }} value={outOf.end} onChange={(e) => setOutOf({ ...outOf, end: e.target.value })} /> : endOut}
                    </th>
                    <th>Total / {midOut + endOut}</th>
                    <th>%</th>
                    <th>Grade</th>
                    <th>Remark</th>
                    <th>Pos.</th>
                  </tr>
                </thead>
                <tbody>
                  {sheet.rows.map((row) => {
                    const l = live[row.student] || {};
                    const e = edits[row.student] || {};
                    return (
                      <tr key={row.student}>
                        <td>
                          {row.student_name} <span className="hint">({row.student_index_number})</span>
                        </td>
                        <td>
                          <input
                            type="number"
                            step="0.01"
                            min="0"
                            style={{ width: 84, ...(l.midBad ? { borderColor: "#c0392b" } : {}) }}
                            value={e.midterm_marks ?? ""}
                            disabled={!canEdit}
                            onChange={(ev) => change(row.student, "midterm_marks", ev.target.value)}
                          />
                        </td>
                        <td>
                          <input
                            type="number"
                            step="0.01"
                            min="0"
                            style={{ width: 84, ...(l.endBad ? { borderColor: "#c0392b" } : {}) }}
                            value={e.endterm_marks ?? ""}
                            disabled={!canEdit}
                            onChange={(ev) => change(row.student, "endterm_marks", ev.target.value)}
                          />
                        </td>
                        <td>
                          {l.total !== null && l.total !== undefined ? <strong>{Number(l.total.toFixed(2))}</strong> : "—"}
                          {l.total !== null && l.total !== undefined && !l.complete ? "*" : ""}
                        </td>
                        <td>{l.pct !== null && l.pct !== undefined ? formatPercent(l.pct) : "—"}</td>
                        <td>{l.graded ? <Badge tone={gradeTone(l.graded.grade)}>{l.graded.grade}</Badge> : "—"}</td>
                        <td>
                          <input
                            type="text"
                            style={{ minWidth: 130 }}
                            placeholder={l.graded?.remark || ""}
                            value={e.remark ?? ""}
                            disabled={!canEdit}
                            onChange={(ev) => change(row.student, "remark", ev.target.value)}
                          />
                        </td>
                        <td>{ordinal(row.position)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
          <p className="hint">
            * Only one of the two exams has marks so far, so the percentage uses just that exam. Positions update after you save.
            {graded.length ? ` Class average so far: ${formatPercent(average)}.` : ""}
          </p>

          {canEdit && (
            <div className="toolbar" style={{ alignItems: "flex-end" }}>
              {published && (
                <input
                  type="text"
                  style={{ minWidth: 280 }}
                  placeholder="Reason for correcting published results"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
              )}
              <button className="btn btn-primary" type="button" onClick={handleSave} disabled={saving || anyBad}>
                {saving ? "Saving…" : "Save results"}
              </button>
            </div>
          )}
        </>
      ) : null}
    </div>
  );
}
