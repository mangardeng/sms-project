import { useEffect, useMemo, useState } from "react";

import { attendanceApi } from "../../api/attendance";
import { classesApi } from "../../api/classes";
import { extractErrorMessage } from "../../api/client";
import ReportPanel from "../../components/ReportPanel";
import { fetchAll, fetchAllSafe } from "../../utils/fetchAll";
import { formatDate, pct } from "../../utils/format";

const STATUSES = ["present", "absent", "late", "excused"];
const blank = () => ({ present: 0, absent: 0, late: 0, excused: 0, total: 0 });

export default function AttendanceReport({ onBack, studentFilter }) {
  const [records, setRecords] = useState([]);
  const [classes, setClasses] = useState([]);
  const [classId, setClassId] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([fetchAll(attendanceApi, studentFilter ? { student: studentFilter } : {}), fetchAllSafe(classesApi)])
      .then(([r, c]) => {
        setRecords(r);
        setClasses(c);
      })
      .catch((err) => setError(extractErrorMessage(err, "Could not load the attendance report.")))
      .finally(() => setLoading(false));
  }, [studentFilter]);

  const filtered = useMemo(
    () =>
      records.filter(
        (r) => (!classId || String(r.school_class) === classId) && (!from || r.date >= from) && (!to || r.date <= to)
      ),
    [records, classId, from, to]
  );

  const totals = useMemo(() => {
    const t = blank();
    filtered.forEach((r) => {
      if (t[r.status] !== undefined) t[r.status] += 1;
      t.total += 1;
    });
    return t;
  }, [filtered]);

  const byStudent = useMemo(() => {
    const map = new Map();
    filtered.forEach((r) => {
      const row = map.get(r.student) || { ...blank(), name: r.student_name, index: r.student_index_number, className: r.school_class_name };
      if (row[r.status] !== undefined) row[r.status] += 1;
      row.total += 1;
      map.set(r.student, row);
    });
    return [...map.values()].sort((a, b) => (a.className || "").localeCompare(b.className || "", undefined, { numeric: true }) || a.name.localeCompare(b.name));
  }, [filtered]);

  const byDate = useMemo(() => {
    const map = new Map();
    filtered.forEach((r) => {
      const row = map.get(r.date) || { ...blank(), date: r.date };
      if (row[r.status] !== undefined) row[r.status] += 1;
      row.total += 1;
      map.set(r.date, row);
    });
    return [...map.values()].sort((a, b) => b.date.localeCompare(a.date));
  }, [filtered]);

  // "Attended" counts present + late (the child was in school).
  const rate = (r) => pct(r.present + r.late, r.total);
  const className = classes.find((c) => String(c.id) === classId)?.name;
  const filterSummary = `Class: ${className || "All classes"} · Period: ${from ? formatDate(from) : "start"} to ${to ? formatDate(to) : "today"}`;

  const statusCols = STATUSES.map((s) => ({ label: s[0].toUpperCase() + s.slice(1), value: (r) => r[s], align: "right" }));

  return (
    <ReportPanel
      title="Attendance Report"
      subtitle="Attendance rate counts present and late as attended"
      filename="attendance-report"
      onBack={onBack}
      loading={loading}
      error={error}
      filterSummary={filterSummary}
      filters={
        <>
          {!studentFilter && classes.length > 0 && (
            <select value={classId} onChange={(e) => setClassId(e.target.value)}>
              <option value="">All classes</option>
              {classes.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          )}
          <label className="hint">
            From <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
          </label>
          <label className="hint">
            To <input type="date" value={to} onChange={(e) => setTo(e.target.value)} />
          </label>
        </>
      }
      stats={[
        { label: "Records", value: totals.total },
        { label: "Present", value: totals.present },
        { label: "Absent", value: totals.absent },
        { label: "Late", value: totals.late },
        { label: "Attendance rate", value: rate(totals) },
      ]}
      sections={[
        {
          heading: "Summary by student",
          columns: [
            { label: "Index No.", value: (r) => r.index },
            { label: "Student", value: (r) => r.name },
            { label: "Class", value: (r) => r.className },
            ...statusCols,
            { label: "Days", value: (r) => r.total, align: "right" },
            { label: "Rate", value: rate, align: "right" },
          ],
          rows: byStudent,
        },
        {
          heading: "Summary by day",
          columns: [{ label: "Date", value: (r) => formatDate(r.date) }, ...statusCols, { label: "Recorded", value: (r) => r.total, align: "right" }, { label: "Rate", value: rate, align: "right" }],
          rows: byDate,
        },
      ]}
    />
  );
}
