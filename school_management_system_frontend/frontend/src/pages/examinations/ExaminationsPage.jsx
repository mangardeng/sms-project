import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { academicYearsApi, termsApi } from "../../api/academic";
import { classesApi } from "../../api/classes";
import { extractErrorMessage } from "../../api/client";
import {
  examinationResultsApi,
  examinationsApi,
  examinationTypesApi,
  gradeScaleApi,
  termSummariesApi,
} from "../../api/examinations";
import { studentsApi } from "../../api/students";
import { subjectsApi } from "../../api/subjects";
import AlertBanner from "../../components/AlertBanner";
import Badge from "../../components/Badge";
import LoadingSpinner from "../../components/LoadingSpinner";
import Modal from "../../components/Modal";
import ResourceManager from "../../components/ResourceManager";
import { useAuth } from "../../context/AuthContext";
import { fetchAll } from "../../utils/fetchAll";
import { formatDate } from "../../utils/format";
import { printReport } from "../../utils/print";
import ExaminationsReport from "./ExaminationsReport";
import SubjectSheetPanel from "./SubjectSheetPanel";
import TermResultsPanel from "./TermResultsPanel";
import TermReportCard from "../../components/TermReportCard";
import { formatPercent, gradeFor, gradeTone } from "../../utils/grading";
import { ROLES } from "../../utils/roles";

const CATEGORY_OPTIONS = [
  { value: "midterm", label: "Midterm" },
  { value: "end_term", label: "End of term" },
  { value: "other", label: "Other (not counted in term results)" },
];
const CATEGORY_LABELS = Object.fromEntries(CATEGORY_OPTIONS.map((o) => [o.value, o.label]));

export default function ExaminationsPage() {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const studentFilter = searchParams.get("student");

  const canManage = [ROLES.ADMIN, ROLES.HEAD_TEACHER, ROLES.TEACHER].includes(user?.role);

  if (studentFilter || [ROLES.PARENT, ROLES.STUDENT].includes(user?.role)) {
    return <ResultsView studentFilter={studentFilter} />;
  }
  if (canManage) return <ManageExaminations canEdit={user.role !== ROLES.HEAD_TEACHER} />;
  return <ResultsView studentFilter={null} />;
}

function ManageExaminations({ canEdit }) {
  const { user } = useAuth();
  const [classOptions, setClassOptions] = useState([]);
  const [subjectOptions, setSubjectOptions] = useState([]);
  const [typeOptions, setTypeOptions] = useState([]);
  const [yearOptions, setYearOptions] = useState([]);
  const [termOptions, setTermOptions] = useState([]);
  const [marksFor, setMarksFor] = useState(null);
  const [view, setView] = useState(user?.role === ROLES.TEACHER ? "sheet" : "exams");
  const isAdmin = user?.role === ROLES.ADMIN;
  const canPublish = [ROLES.ADMIN, ROLES.HEAD_TEACHER].includes(user?.role);

  useEffect(() => {
    classesApi.list({ page_size: 200 }).then((d) => setClassOptions((d.results || d).map((c) => ({ value: c.id, label: c.name }))));
    subjectsApi.list({ page_size: 200 }).then((d) => setSubjectOptions((d.results || d).map((s) => ({ value: s.id, label: s.name }))));
    examinationTypesApi.list({ page_size: 200 }).then((d) => setTypeOptions((d.results || d).map((t) => ({ value: t.id, label: t.name }))));
    academicYearsApi.list({ page_size: 50 }).then((d) => setYearOptions((d.results || d).map((y) => ({ value: y.id, label: `${y.name}${y.is_current ? " (current)" : ""}` }))));
    termsApi.list({ page_size: 50 }).then((d) => setTermOptions((d.results || d).map((t) => ({ value: t.id, label: t.display_name || `${t.name} — ${t.academic_year_name}` }))));
  }, []);

  const formFields = [
    { name: "name", label: "Examination name", type: "text", required: true, placeholder: "e.g. Term 1 Midterm - Mathematics" },
    { name: "examination_type", label: "Examination type", type: "select", options: typeOptions, required: true },
    { name: "school_class", label: "Class", type: "select", options: classOptions, required: true },
    { name: "subject", label: "Subject", type: "select", options: subjectOptions, required: true },
    { name: "academic_year", label: "Academic year", type: "select", options: yearOptions, required: true },
    { name: "term", label: "Term", type: "select", options: termOptions, required: true },
    { name: "date", label: "Date", type: "date", required: true },
    {
      name: "max_marks",
      label: "Out of (maximum marks)",
      type: "number",
      hint: "What this exam is marked out of. Leave blank to use the type's default: Midterm 40, End of term 60 (they add up to 100).",
    },
  ];

  const columns = [
    { key: "name", label: "Examination" },
    { key: "subject_name", label: "Subject" },
    { key: "school_class_name", label: "Class" },
    { key: "date", label: "Date", render: (row) => formatDate(row.date) },
    { key: "max_marks", label: "Out of", render: (row) => Number(row.max_marks) },
    {
      key: "is_published",
      label: "Status",
      render: (row) => <Badge tone={row.is_published ? "accent" : "gold"}>{row.is_published ? "Published" : "Draft"}</Badge>,
    },
  ];

  const gradeFields = [
    { name: "grade", label: "Grade", type: "text", required: true, placeholder: "e.g. A" },
    { name: "min_percentage", label: "From (%)", type: "number", step: "0.01", required: true, hint: "Lowest percentage that earns this grade." },
    { name: "remark", label: "Remark", type: "text", placeholder: "e.g. Excellent" },
  ];

  const typeFields = [
    { name: "name", label: "Type name", type: "text", required: true, placeholder: "e.g. Midterm" },
    {
      name: "category",
      label: "Counts as",
      type: "select",
      options: CATEGORY_OPTIONS,
      required: true,
      hint: "Midterm and End of term marks are combined automatically into each student's term result.",
    },
    {
      name: "default_max_marks",
      label: "Usually marked out of",
      type: "number",
      step: "0.01",
      hint: "Midterm: 40, End of term: 60. New exams of this type use this unless you change it. Marks from both are added together.",
    },
  ];

  return (
    <div>
      <div className="toolbar">
        <button className={`btn btn-sm ${view === "exams" ? "btn-primary" : "btn-secondary"}`} type="button" onClick={() => setView("exams")}>
          Examinations
        </button>
        <button className={`btn btn-sm ${view === "types" ? "btn-primary" : "btn-secondary"}`} type="button" onClick={() => setView("types")}>
          Examination types
        </button>
        <button className={`btn btn-sm ${view === "sheet" ? "btn-primary" : "btn-secondary"}`} type="button" onClick={() => setView("sheet")}>
          ✏️ Subject results
        </button>
        <button className={`btn btn-sm ${view === "results" ? "btn-primary" : "btn-secondary"}`} type="button" onClick={() => setView("results")}>
          🏆 Term results
        </button>
        <button className={`btn btn-sm ${view === "grades" ? "btn-primary" : "btn-secondary"}`} type="button" onClick={() => setView("grades")}>
          Grade scale
        </button>
        <button className={`btn btn-sm ${view === "report" ? "btn-primary" : "btn-secondary"}`} type="button" onClick={() => setView("report")}>
          📊 Report
        </button>
      </div>

      {view === "report" ? (
        <ExaminationsReport />
      ) : view === "sheet" ? (
        <SubjectSheetPanel />
      ) : view === "results" ? (
        <TermResultsPanel canRecalculate={canEdit} />
      ) : view === "grades" ? (
        <ResourceManager
          key="grades"
          title="Grade scale"
          subtitle={
            isAdmin
              ? "Set the lowest percentage for each grade. Saving a change re-grades every mark and term result."
              : "The grading scale used for every examination, set by the administrator."
          }
          api={gradeScaleApi}
          columns={[
            { key: "grade", label: "Grade" },
            { key: "min_percentage", label: "From (%)" },
            { key: "remark", label: "Remark" },
          ]}
          formFields={isAdmin ? gradeFields : null}
          canCreate={isAdmin}
          canEdit={isAdmin}
          canDelete={isAdmin}
          canPrint={false}
          createLabel="Add grade"
          emptyTitle="No grades defined"
        />
      ) : view === "types" ? (
        <ResourceManager
          key="types"
          title="Examination types"
          subtitle={isAdmin ? "Define exam types such as Midterm or End of Term." : "Exam types defined by the administrator."}
          api={examinationTypesApi}
          columns={[
            { key: "name", label: "Type" },
            { key: "category", label: "Counts as", render: (row) => CATEGORY_LABELS[row.category] || row.category },
            { key: "default_max_marks", label: "Marked out of" },
          ]}
          formFields={isAdmin ? typeFields : null}
          canCreate={isAdmin}
          canEdit={isAdmin}
          canDelete={isAdmin}
          createLabel="Add type"
          emptyTitle="No examination types yet"
          emptyDescription={isAdmin ? "Add a type (e.g. Midterm) before creating examinations." : undefined}
        />
      ) : (
      <ResourceManager
        key="exams"
        title="Examinations"
        subtitle="Create exams, enter marks, and publish results to students and parents."
        api={examinationsApi}
        columns={columns}
        formFields={formFields}
        canCreate={canEdit}
        canEdit={canEdit}
        canDelete={canEdit}
        createLabel="Add examination"
        rowActions={(row) => (
          <>
            <button className="btn btn-secondary btn-sm" type="button" onClick={() => setMarksFor(row)}>
              {canEdit ? "Enter marks" : "View marks"}
            </button>
            {canPublish && !row.is_published && <PublishButton examination={row} />}
          </>
        )}
        emptyTitle="No examinations created yet"
      />
      )}

      {marksFor && <MarksEntryModal examination={marksFor} onClose={() => setMarksFor(null)} readOnly={!canEdit} />}
    </div>
  );
}

function PublishButton({ examination }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function handlePublish() {
    if (!window.confirm(`Publish results for "${examination.name}"? This will lock marks and make them visible to students/parents.`)) return;
    setBusy(true);
    setError("");
    try {
      await examinationsApi.publish(examination.id);
      window.location.reload();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <button className="btn btn-primary btn-sm" type="button" onClick={handlePublish} disabled={busy}>
        {busy ? "Publishing…" : "Publish"}
      </button>
      {error && <span className="field-error">{error}</span>}
    </>
  );
}

function MarksEntryModal({ examination, onClose, readOnly }) {
  const { user } = useAuth();
  const [students, setStudents] = useState([]);
  const [marks, setMarks] = useState({});
  const [scale, setScale] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [reason, setReason] = useState("");

  const max = Number(examination.max_marks);
  const countsTowardTerm = ["midterm", "end_term"].includes(examination.examination_type_category);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      studentsApi.list({ school_class: examination.school_class, status: "active", page_size: 200 }),
      examinationResultsApi.list({ examination: examination.id, page_size: 200 }),
      gradeScaleApi.list({ page_size: 50 }),
    ]).then(([studentData, resultData, scaleData]) => {
      if (cancelled) return;
      const studentList = studentData.results || studentData;
      setStudents(studentList);
      setScale(scaleData.results || scaleData);
      const existing = resultData.results || resultData;
      const map = {};
      studentList.forEach((s) => {
        const found = existing.find((r) => r.student === s.id);
        map[s.id] = { marks_obtained: found?.marks_obtained ?? "", remarks: found?.remarks ?? "" };
      });
      setMarks(map);
      setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [examination]);

  function update(studentId, field, value) {
    setSuccess("");
    setMarks((prev) => ({ ...prev, [studentId]: { ...prev[studentId], [field]: value } }));
  }

  // Live percentage + grade for every row, using the school's grade scale.
  function infoFor(studentId) {
    const raw = marks[studentId]?.marks_obtained;
    if (raw === "" || raw == null) return { empty: true };
    const n = Number(raw);
    const invalid = Number.isNaN(n) || n < 0 || n > max;
    const pct = invalid ? null : (n / max) * 100;
    return { invalid, pct, graded: gradeFor(pct, scale) };
  }

  const infos = students.map((s) => infoFor(s.id));
  const valid = infos.filter((i) => !i.empty && !i.invalid);
  const hasInvalid = infos.some((i) => i.invalid);
  const average = valid.length ? valid.reduce((a, i) => a + i.pct, 0) / valid.length : null;
  const highest = valid.length ? Math.max(...valid.map((i) => i.pct)) : null;
  const lowest = valid.length ? Math.min(...valid.map((i) => i.pct)) : null;

  async function handleSave() {
    if (hasInvalid) {
      setError(`Marks must be between 0 and ${examination.max_marks}. Fix the highlighted rows first.`);
      return;
    }
    if (examination.is_published && !reason.trim()) {
      setError("These results are already published. Give a short reason for the correction.");
      return;
    }
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      await examinationResultsApi.bulkEntry({
        examination: examination.id,
        reason,
        entries: students
          .filter((s) => marks[s.id]?.marks_obtained !== "")
          .map((s) => ({
            student: s.id,
            marks_obtained: marks[s.id].marks_obtained,
            remarks: marks[s.id].remarks || "",
          })),
      });
      setSuccess(
        countsTowardTerm
          ? "Marks saved and graded. Subject results, overall grades and class positions were updated automatically — see the Term results tab."
          : "Marks saved and graded."
      );
    } catch (err) {
      setError(extractErrorMessage(err, "Could not save marks. Only the subject teacher or an administrator can enter marks for this subject."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal title={`${readOnly ? "Marks" : "Enter marks"} — ${examination.name}`} onClose={onClose} width={760}>
      <p className="hint" style={{ marginTop: 0 }}>
        {examination.examination_type_name} · {examination.subject_name} · {examination.school_class_name}
        {countsTowardTerm ? " · added to the term result" : ""}
      </p>
      <div className="alert-banner success" style={{ fontSize: "0.95rem" }}>
        This examination is marked <strong>out of {Number(examination.max_marks)}</strong>. Enter each student's mark from 0 to {Number(examination.max_marks)}.
        {countsTowardTerm ? " When both the midterm and end-of-term marks are in, they are added together and graded automatically." : ""}
      </div>
      {examination.examination_type_category === "other" && (
        <AlertBanner type="error">
          This exam type is not set to count as Midterm or End of term, so these marks will NOT be added to the term result. Go to
          Examination types and set "Counts as".
        </AlertBanner>
      )}
      <AlertBanner type="error">{error}</AlertBanner>
      <AlertBanner type="success">{success}</AlertBanner>
      {loading ? (
        <LoadingSpinner ink />
      ) : (
        <>
          <table className="data-table">
            <thead>
              <tr>
                <th>Student</th>
                <th>Marks (/{examination.max_marks})</th>
                <th>%</th>
                <th>Grade</th>
                <th>Remarks</th>
              </tr>
            </thead>
            <tbody>
              {students.map((s, i) => {
                const info = infos[i];
                return (
                  <tr key={s.id}>
                    <td>{`${s.user?.first_name || ""} ${s.user?.last_name || ""}`.trim()}</td>
                    <td>
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        max={examination.max_marks}
                        style={{ width: 90, ...(info.invalid ? { borderColor: "#c0392b" } : {}) }}
                        value={marks[s.id]?.marks_obtained ?? ""}
                        onChange={(e) => update(s.id, "marks_obtained", e.target.value)}
                        disabled={readOnly}
                      />
                      {info.invalid && <div className="field-error">0 – {examination.max_marks} only</div>}
                    </td>
                    <td>{info.pct != null ? formatPercent(info.pct) : "—"}</td>
                    <td>{info.graded ? <Badge tone={gradeTone(info.graded.grade)}>{info.graded.grade}</Badge> : "—"}</td>
                    <td>
                      <input
                        type="text"
                        placeholder={info.graded?.remark || ""}
                        value={marks[s.id]?.remarks ?? ""}
                        onChange={(e) => update(s.id, "remarks", e.target.value)}
                        disabled={readOnly}
                      />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          <p className="hint" style={{ margin: "10px 0 0" }}>
            {valid.length} of {students.length} entered
            {valid.length ? ` · Average ${formatPercent(average)} · Highest ${formatPercent(highest)} · Lowest ${formatPercent(lowest)}` : ""}
          </p>

          {examination.is_published && !readOnly && (
            <input
              type="text"
              style={{ width: "100%", marginTop: 10 }}
              placeholder="Reason for correcting published marks (required)"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          )}

          <div className="modal-footer">
            <button className="btn btn-secondary" type="button" onClick={onClose}>
              Close
            </button>
            <button
              className="btn btn-secondary"
              type="button"
              onClick={() =>
                printReport({
                  title: `Mark Sheet — ${examination.name}`,
                  subtitle: `${examination.subject_name || ""} · ${examination.school_class_name || ""} · ${formatDate(examination.date)} · Out of ${examination.max_marks}`,
                  sections: [
                    {
                      columns: [
                        { label: "#", value: (r) => r.n, align: "right" },
                        { label: "Index No.", value: (r) => r.s.index_number },
                        { label: "Student", value: (r) => `${r.s.user?.first_name || ""} ${r.s.user?.last_name || ""}`.trim() },
                        { label: `Marks (/${examination.max_marks})`, value: (r) => marks[r.s.id]?.marks_obtained, align: "right" },
                        { label: "%", value: (r) => (r.info.pct != null ? r.info.pct.toFixed(1) : ""), align: "right" },
                        { label: "Grade", value: (r) => r.info.graded?.grade || "" },
                        { label: "Remarks", value: (r) => marks[r.s.id]?.remarks },
                      ],
                      rows: students.map((s, i) => ({ s, n: i + 1, info: infos[i] })),
                    },
                  ],
                  printedBy: `${user?.first_name || ""} ${user?.last_name || ""}`.trim() || user?.username,
                })
              }
            >
              🖨 Print mark sheet
            </button>
            {!readOnly && (
              <button className="btn btn-primary" type="button" onClick={handleSave} disabled={saving || hasInvalid}>
                {saving ? "Saving…" : "Save marks"}
              </button>
            )}
          </div>
        </>
      )}
    </Modal>
  );
}

function ResultsView({ studentFilter }) {
  const { user } = useAuth();
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchAll(examinationResultsApi, studentFilter ? { student: studentFilter } : {})
      .then(setResults)
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [studentFilter]);

  return (
    <div>
      <div className="page-header">
        <h1>Examination Results</h1>
        {user?.role !== ROLES.STUDENT && (
        <button
          className="btn btn-primary"
          type="button"
          disabled={loading || !results.length}
          onClick={() => {
            const names = [...new Set(results.map((r) => `${r.student_name} (${r.student_index_number})`))];
            const percents = results.map((r) => Number(r.percentage)).filter((n) => !Number.isNaN(n));
            printReport({
              title: "Student Report Card",
              subtitle: names.length === 1 ? names[0] : undefined,
              stats: percents.length
                ? [
                    { label: "Subjects / exams", value: results.length },
                    { label: "Average", value: `${(percents.reduce((a, b) => a + b, 0) / percents.length).toFixed(1)}%` },
                  ]
                : [],
              sections: [
                {
                  columns: [
                    { label: "Examination", value: (r) => r.examination_name },
                    ...(names.length > 1 ? [{ label: "Student", value: (r) => `${r.student_name} (${r.student_index_number})` }] : []),
                    { label: "Marks", value: (r) => r.marks_obtained, align: "right" },
                    { label: "%", value: (r) => (r.percentage != null ? `${r.percentage}%` : ""), align: "right" },
                    { label: "Grade", value: (r) => r.grade },
                    { label: "Remarks", value: (r) => r.remarks || r.grade_remark },
                  ],
                  rows: results,
                },
              ],
              printedBy: `${user?.first_name || ""} ${user?.last_name || ""}`.trim() || user?.username,
            });
          }}
        >
          🖨 Print report card
        </button>
        )}
      </div>
      <AlertBanner type="error">{error}</AlertBanner>
      {loading ? (
        <LoadingSpinner ink />
      ) : results.length === 0 ? (
        <p className="hint">No published results yet.</p>
      ) : (
        <div className="surface">
          <div className="data-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Examination</th>
                  <th>Student</th>
                  <th>Marks</th>
                  <th>Percentage</th>
                  <th>Grade</th>
                  <th>Remarks</th>
                </tr>
              </thead>
              <tbody>
                {results.map((r) => (
                  <tr key={r.id}>
                    <td>{r.examination_name}</td>
                    <td>
                      {r.student_name} <span className="hint">({r.student_index_number})</span>
                    </td>
                    <td>{r.marks_obtained}</td>
                    <td>{r.percentage != null ? `${r.percentage}%` : "—"}</td>
                    <td>
                      <Badge tone="gold">{r.grade || "—"}</Badge>
                    </td>
                    <td>{r.remarks || r.grade_remark || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <TermReportsSection studentFilter={studentFilter} />
    </div>
  );
}

/** Term report cards (midterm + end of term combined, overall grade and position) for students and parents. */
function TermReportsSection({ studentFilter }) {
  const { user } = useAuth();
  const [cards, setCards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    fetchAll(termSummariesApi, studentFilter ? { student: studentFilter } : {})
      .then((summaries) => Promise.all(summaries.map((summary) => termSummariesApi.reportCard(summary.id))))
      .then((list) => !cancelled && setCards(list))
      .catch((err) => !cancelled && setError(extractErrorMessage(err)))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [studentFilter]);

  const printedBy = `${user?.first_name || ""} ${user?.last_name || ""}`.trim() || user?.username;

  return (
    <div style={{ marginTop: 28 }}>
      <h2>Term results</h2>
      <AlertBanner type="error">{error}</AlertBanner>
      {loading ? (
        <LoadingSpinner ink />
      ) : cards.length === 0 ? (
        <p className="hint">Term results appear here once the midterm and end-of-term results are published.</p>
      ) : (
        cards.map((card) => (
          <div key={card.id} className="surface surface-pad" style={{ marginBottom: 16 }}>
            <h3 style={{ marginTop: 0 }}>
              {card.student_name} — {card.term_name}
            </h3>
            <TermReportCard card={card} canPrint={user?.role !== ROLES.STUDENT} printedBy={printedBy} />
          </div>
        ))
      )}
    </div>
  );
}
