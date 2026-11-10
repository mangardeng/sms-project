import { useEffect, useMemo, useState } from "react";

import { classesApi } from "../../api/classes";
import { extractErrorMessage } from "../../api/client";
import { examinationResultsApi, examinationsApi } from "../../api/examinations";
import ReportPanel from "../../components/ReportPanel";
import { fetchAll, fetchAllSafe } from "../../utils/fetchAll";
import { formatDate, pct } from "../../utils/format";

const PASS_MARK = 50;
const avg = (list) => (list.length ? list.reduce((a, b) => a + b, 0) / list.length : null);
const fmt = (n) => (n === null || n === undefined ? "" : `${n.toFixed(1)}%`);

export default function ExaminationsReport({ onBack }) {
  const [exams, setExams] = useState([]);
  const [results, setResults] = useState([]);
  const [classes, setClasses] = useState([]);
  const [classId, setClassId] = useState("");
  const [examId, setExamId] = useState("");
  const [studentId, setStudentId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([fetchAll(examinationsApi), fetchAll(examinationResultsApi), fetchAllSafe(classesApi)])
      .then(([e, r, c]) => {
        setExams(e);
        setResults(r);
        setClasses(c);
      })
      .catch((err) => setError(extractErrorMessage(err, "Could not load the examinations report.")))
      .finally(() => setLoading(false));
  }, []);

  const examById = useMemo(() => new Map(exams.map((e) => [e.id, e])), [exams]);
  const classExams = exams.filter((e) => !classId || String(e.school_class) === classId);
  const students = useMemo(() => {
    const map = new Map();
    results.forEach((r) => map.set(r.student, `${r.student_name} (${r.student_index_number})`));
    return [...map.entries()].sort((a, b) => a[1].localeCompare(b[1]));
  }, [results]);

  const shownExams = classExams.filter((e) => !examId || String(e.id) === examId);
  const shownResults = results.filter((r) => {
    const e = examById.get(r.examination);
    return e && (!classId || String(e.school_class) === classId) && (!examId || String(r.examination) === examId) && (!studentId || String(r.student) === studentId);
  });

  const percents = shownResults.map((r) => Number(r.percentage)).filter((n) => !Number.isNaN(n));
  const passed = percents.filter((n) => n >= PASS_MARK).length;

  const examRows = shownExams.map((e) => {
    const rs = results.filter((r) => r.examination === e.id);
    const ps = rs.map((r) => Number(r.percentage)).filter((n) => !Number.isNaN(n));
    return { e, count: rs.length, avg: avg(ps), high: ps.length ? Math.max(...ps) : null, low: ps.length ? Math.min(...ps) : null, pass: ps.filter((n) => n >= PASS_MARK).length, n: ps.length };
  });

  const gradeRows = useMemo(() => {
    const map = new Map();
    shownResults.forEach((r) => map.set(r.grade || "—", (map.get(r.grade || "—") || 0) + 1));
    return [...map.entries()].sort((a, b) => a[0].localeCompare(b[0])).map(([grade, n]) => ({ grade, n }));
  }, [shownResults]);

  const sortedResults = [...shownResults].sort(
    (a, b) => (a.examination_name || "").localeCompare(b.examination_name || "") || (Number(b.percentage) || 0) - (Number(a.percentage) || 0)
  );

  const filterSummary = [
    `Class: ${classes.find((c) => String(c.id) === classId)?.name || "All"}`,
    `Examination: ${examById.get(Number(examId))?.name || "All"}`,
    studentId ? `Student: ${students.find(([id]) => String(id) === studentId)?.[1]}` : null,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <ReportPanel
      title="Examinations Report"
      subtitle={`Pass mark ${PASS_MARK}%`}
      filename="examinations-report"
      onBack={onBack}
      loading={loading}
      error={error}
      filterSummary={filterSummary}
      filters={
        <>
          {classes.length > 0 && (
            <select
              value={classId}
              onChange={(e) => {
                setClassId(e.target.value);
                setExamId("");
              }}
            >
              <option value="">All classes</option>
              {classes.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          )}
          <select value={examId} onChange={(e) => setExamId(e.target.value)}>
            <option value="">All examinations</option>
            {classExams.map((e) => (
              <option key={e.id} value={e.id}>
                {e.name}
              </option>
            ))}
          </select>
          <select value={studentId} onChange={(e) => setStudentId(e.target.value)}>
            <option value="">All students</option>
            {students.map(([id, label]) => (
              <option key={id} value={id}>
                {label}
              </option>
            ))}
          </select>
        </>
      }
      stats={[
        { label: "Examinations", value: shownExams.length },
        { label: "Results", value: shownResults.length },
        { label: "Average", value: fmt(avg(percents)) || "—" },
        { label: "Pass rate", value: pct(passed, percents.length) },
      ]}
      sections={[
        {
          heading: "Examination summary",
          columns: [
            { label: "Examination", value: (r) => r.e.name },
            { label: "Subject", value: (r) => r.e.subject_name },
            { label: "Class", value: (r) => r.e.school_class_name },
            { label: "Date", value: (r) => formatDate(r.e.date) },
            { label: "Out of", value: (r) => r.e.max_marks, align: "right" },
            { label: "Entries", value: (r) => r.count, align: "right" },
            { label: "Average", value: (r) => fmt(r.avg), align: "right" },
            { label: "Highest", value: (r) => fmt(r.high), align: "right" },
            { label: "Lowest", value: (r) => fmt(r.low), align: "right" },
            { label: "Pass rate", value: (r) => pct(r.pass, r.n), align: "right" },
          ],
          rows: examRows,
        },
        {
          heading: "Grade distribution",
          columns: [
            { label: "Grade", value: (r) => r.grade },
            { label: "Students", value: (r) => r.n, align: "right" },
            { label: "Share", value: (r) => pct(r.n, shownResults.length), align: "right" },
          ],
          rows: gradeRows,
        },
        {
          heading: "Results",
          columns: [
            { label: "Examination", value: (r) => r.examination_name },
            { label: "Index No.", value: (r) => r.student_index_number },
            { label: "Student", value: (r) => r.student_name },
            { label: "Marks", value: (r) => r.marks_obtained, align: "right" },
            { label: "%", value: (r) => (r.percentage != null ? `${r.percentage}%` : ""), align: "right" },
            { label: "Grade", value: (r) => r.grade },
            { label: "Remarks", value: (r) => r.remarks },
          ],
          rows: sortedResults,
        },
      ]}
    />
  );
}
