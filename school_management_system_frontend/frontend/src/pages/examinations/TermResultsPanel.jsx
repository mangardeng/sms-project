import { useEffect, useMemo, useState } from "react";

import { termsApi } from "../../api/academic";
import { classesApi } from "../../api/classes";
import { extractErrorMessage } from "../../api/client";
import { examinationsApi, termResultsApi, termSummariesApi } from "../../api/examinations";
import AlertBanner from "../../components/AlertBanner";
import Badge from "../../components/Badge";
import LoadingSpinner from "../../components/LoadingSpinner";
import Modal from "../../components/Modal";
import TermReportCard from "../../components/TermReportCard";
import { useAuth } from "../../context/AuthContext";
import { fetchAll } from "../../utils/fetchAll";
import { formatPercent, gradeTone, ordinal, scoreText } from "../../utils/grading";
import { printReport } from "../../utils/print";

/**
 * Staff view of the automatically computed results: every student's grade in each subject
 * (midterm + end of term combined) and their overall grade and class position.
 */
export default function TermResultsPanel({ canRecalculate }) {
  const { user } = useAuth();
  const [classes, setClasses] = useState([]);
  const [terms, setTerms] = useState([]);
  const [classId, setClassId] = useState("");
  const [termId, setTermId] = useState("");
  const [summaries, setSummaries] = useState([]);
  const [subjectRows, setSubjectRows] = useState([]);
  const [exams, setExams] = useState([]);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [card, setCard] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  const printedBy = `${user?.first_name || ""} ${user?.last_name || ""}`.trim() || user?.username;

  useEffect(() => {
    classesApi.list({ page_size: 200 }).then((d) => {
      const list = d.results || d;
      setClasses(list);
      if (list.length) setClassId((current) => current || String(list[0].id));
    });
    termsApi.list({ page_size: 50 }).then((d) => {
      const list = d.results || d;
      setTerms(list);
      const current = list.find((t) => t.is_current) || list[0];
      if (current) setTermId((value) => value || String(current.id));
    });
  }, []);

  useEffect(() => {
    if (!classId || !termId) return undefined;
    let cancelled = false;
    setLoading(true);
    setError("");
    Promise.all([
      fetchAll(termSummariesApi, { school_class: classId, term: termId }),
      fetchAll(termResultsApi, { school_class: classId, term: termId }),
      fetchAll(examinationsApi, { school_class: classId, term: termId }),
    ])
      .then(([sums, rows, examList]) => {
        if (cancelled) return;
        setExams(examList);
        setSummaries([...sums].sort((a, b) => (a.position || 9999) - (b.position || 9999)));
        setSubjectRows(rows);
      })
      .catch((err) => !cancelled && setError(extractErrorMessage(err)))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [classId, termId, reloadKey]);

  const subjects = useMemo(() => {
    const map = new Map();
    subjectRows.forEach((r) => map.set(r.subject, r.subject_name));
    return [...map.entries()].map(([id, name]) => ({ id, name })).sort((a, b) => a.name.localeCompare(b.name));
  }, [subjectRows]);

  const cellFor = useMemo(() => {
    const lookup = {};
    subjectRows.forEach((r) => {
      lookup[`${r.student}:${r.subject}`] = r;
    });
    return (studentId, subjectId) => lookup[`${studentId}:${subjectId}`];
  }, [subjectRows]);

  // Explain anything that stops marks from being combined into the term result.
  const problems = useMemo(() => {
    const list = [];
    const reportedTypes = new Set();
    exams
      .filter((e) => e.examination_type_category === "other")
      .forEach((e) => {
        if (reportedTypes.has(e.examination_type_name)) return;
        reportedTypes.add(e.examination_type_name);
        list.push(
          `The exam type "${e.examination_type_name}" is not set to count as Midterm or End of term, so its marks are left out. Open Examination types and set "Counts as".`
        );
      });
    const bySubject = new Map();
    exams.forEach((e) => {
      const entry = bySubject.get(e.subject_name) || {};
      if (e.examination_type_category === "midterm") entry.mid = true;
      if (e.examination_type_category === "end_term") entry.end = true;
      bySubject.set(e.subject_name, entry);
    });
    const totals = new Map();
    exams.forEach((e) => {
      if (!["midterm", "end_term"].includes(e.examination_type_category)) return;
      const entry = totals.get(e.subject_name) || { sum: 0, parts: [] };
      entry.sum += Number(e.max_marks);
      entry.parts.push(`${e.examination_type_name} out of ${Number(e.max_marks)}`);
      totals.set(e.subject_name, entry);
    });
    totals.forEach((entry, subject) => {
      if (entry.parts.length > 1 && entry.sum !== 100) {
        list.push(`${subject}: ${entry.parts.join(" + ")} adds up to ${entry.sum}, not 100. Edit the exam so Midterm is out of 40 and End of term out of 60.`);
      }
    });
    bySubject.forEach((entry, subject) => {
      if (entry.mid && !entry.end) list.push(`${subject}: no End of term exam has been created for this class and term yet, so results stay provisional.`);
      if (entry.end && !entry.mid) list.push(`${subject}: no Midterm exam has been created for this class and term, so only the end-of-term marks are used.`);
    });
    return list;
  }, [exams]);

  const selectedClass = classes.find((c) => String(c.id) === String(classId));
  const selectedTerm = terms.find((t) => String(t.id) === String(termId));
  const termLabel = (t) => t.display_name || `${t.name} — ${t.academic_year_name}`;

  async function handleRecalculate() {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const res = await termSummariesApi.recompute({ school_class: Number(classId), term: Number(termId) });
      setNotice(res.detail || "Results recalculated.");
      setReloadKey((k) => k + 1);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function openCard(summary) {
    setError("");
    try {
      setCard(await termSummariesApi.reportCard(summary.id));
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  function handlePrint() {
    printReport({
      title: "Class Term Results",
      subtitle: `${selectedClass?.name || ""} · ${selectedTerm ? termLabel(selectedTerm) : ""}`,
      sections: [
        {
          heading: "Overall results and class positions",
          columns: [
            { label: "Pos", value: (r) => ordinal(r.position) },
            { label: "Index No.", value: (r) => r.student_index_number },
            { label: "Student", value: (r) => r.student_name },
            { label: "Subjects", value: (r) => r.subjects_count, align: "right" },
            { label: "Total", value: (r) => r.total_score, align: "right" },
            { label: "Average %", value: (r) => r.average_percentage, align: "right" },
            { label: "Grade", value: (r) => r.grade },
            { label: "Status", value: (r) => (r.is_complete ? "Complete" : "Provisional") },
          ],
          rows: summaries,
        },
        {
          heading: "Subject grades (final % and grade)",
          columns: [
            { label: "Student", value: (r) => r.student_name },
            ...subjects.map((s) => ({
              label: s.name,
              value: (r) => {
                const cell = cellFor(r.student, s.id);
                return cell ? `${cell.final_percentage} ${cell.grade}` : "—";
              },
              align: "right",
            })),
          ],
          rows: summaries,
        },
      ],
      printedBy,
    });
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Term results</h1>
          <div className="subtitle">
            Calculated automatically from Midterm and End-of-term marks. Each subject gets a final grade, and every student gets an
            overall grade and class position.
          </div>
        </div>
      </div>

      <div className="toolbar">
        <select value={classId} onChange={(e) => setClassId(e.target.value)}>
          {classes.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <select value={termId} onChange={(e) => setTermId(e.target.value)}>
          {terms.map((t) => (
            <option key={t.id} value={t.id}>
              {termLabel(t)}
            </option>
          ))}
        </select>
        {canRecalculate && (
          <button className="btn btn-secondary btn-sm" type="button" onClick={handleRecalculate} disabled={busy || !classId || !termId}>
            {busy ? "Recalculating…" : "↻ Recalculate"}
          </button>
        )}
        <button className="btn btn-secondary btn-sm" type="button" onClick={handlePrint} disabled={loading || !summaries.length}>
          🖨 Print
        </button>
      </div>

      <AlertBanner type="error">{error}</AlertBanner>
      <AlertBanner type="success">{notice}</AlertBanner>
      {!loading && problems.length > 0 && (
        <AlertBanner type="error">
          <strong>Check these before expecting a full result:</strong>
          <ul style={{ margin: "6px 0 0 18px", padding: 0 }}>
            {problems.map((message) => (
              <li key={message}>{message}</li>
            ))}
          </ul>
        </AlertBanner>
      )}

      {loading ? (
        <LoadingSpinner ink />
      ) : summaries.length === 0 ? (
        <p className="hint">
          No term results yet for this class and term. They appear automatically as soon as midterm or end-of-term marks are entered
          {canRecalculate ? " (use Recalculate if marks were entered before this feature was added)." : "."}
        </p>
      ) : (
        <>
          <div className="surface" style={{ marginBottom: 16 }}>
            <div className="data-table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Pos</th>
                    <th>Student</th>
                    <th>Subjects</th>
                    <th>Total</th>
                    <th>Average</th>
                    <th>Overall grade</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {summaries.map((s) => (
                    <tr key={s.id}>
                      <td>
                        <strong>{ordinal(s.position)}</strong>
                      </td>
                      <td>
                        <button className="btn-link" type="button" onClick={() => openCard(s)} style={{ background: "none", border: 0, padding: 0, cursor: "pointer", color: "inherit", textDecoration: "underline" }}>
                          {s.student_name}
                        </button>{" "}
                        <span className="hint">({s.student_index_number})</span>
                      </td>
                      <td>{s.subjects_count}</td>
                      <td>
                        {s.total_score} / {s.subjects_count * 100}
                      </td>
                      <td>{formatPercent(s.average_percentage)}</td>
                      <td>
                        <Badge tone={gradeTone(s.grade)}>{s.grade}</Badge> <span className="hint">{s.remark}</span>
                      </td>
                      <td>
                        <Badge tone={s.is_complete ? "accent" : "gold"}>{s.is_complete ? "Complete" : "Provisional"}</Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <h3 style={{ margin: "8px 0" }}>Grades by subject</h3>
          <p className="hint" style={{ marginTop: 0 }}>
            Each cell shows the subject total % and grade, with the midterm (M) and end-of-term (E) scores underneath, e.g. 36 / 40 and 56 / 60.
          </p>
          <div className="surface">
            <div className="data-table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Student</th>
                    {subjects.map((subject) => (
                      <th key={subject.id}>{subject.name}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {summaries.map((s) => (
                    <tr key={s.id}>
                      <td>{s.student_name}</td>
                      {subjects.map((subject) => {
                        const cell = cellFor(s.student, subject.id);
                        if (!cell) return <td key={subject.id}>—</td>;
                        return (
                          <td key={subject.id}>
                            <strong>{formatPercent(cell.final_percentage, 0)}</strong> <Badge tone={gradeTone(cell.grade)}>{cell.grade}</Badge>
                            <div className="hint" style={{ fontSize: 12 }}>
                              M {cell.midterm_points != null ? scoreText(cell.midterm_points, cell.midterm_out_of) : "–"} · E{" "}
                              {cell.endterm_points != null ? scoreText(cell.endterm_points, cell.endterm_out_of) : "–"}
                            </div>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {card && (
        <Modal title={`${card.student_name} — ${card.term_name}`} onClose={() => setCard(null)} width={780}>
          <TermReportCard card={card} canPrint printedBy={printedBy} />
        </Modal>
      )}
    </div>
  );
}
