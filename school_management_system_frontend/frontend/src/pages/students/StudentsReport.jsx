import { useEffect, useMemo, useState } from "react";

import { classesApi } from "../../api/classes";
import { extractErrorMessage } from "../../api/client";
import { studentsApi } from "../../api/students";
import ReportPanel from "../../components/ReportPanel";
import { fetchAll } from "../../utils/fetchAll";
import { formatDate, fullName, titleCase } from "../../utils/format";

export default function StudentsReport({ onBack }) {
  const [students, setStudents] = useState([]);
  const [classes, setClasses] = useState([]);
  const [classId, setClassId] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([fetchAll(studentsApi), fetchAll(classesApi)])
      .then(([s, c]) => {
        setStudents(s);
        setClasses(c);
      })
      .catch((err) => setError(extractErrorMessage(err, "Could not load the student report.")))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(
    () => students.filter((s) => (!classId || String(s.school_class) === classId) && (!status || s.status === status)),
    [students, classId, status]
  );

  const count = (fn) => filtered.filter(fn).length;
  const byClass = useMemo(() => {
    const map = new Map();
    filtered.forEach((s) => {
      const key = s.school_class_name || "No class";
      const row = map.get(key) || { name: key, male: 0, female: 0, other: 0, total: 0 };
      if (s.gender === "male") row.male += 1;
      else if (s.gender === "female") row.female += 1;
      else row.other += 1;
      row.total += 1;
      map.set(key, row);
    });
    return [...map.values()].sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }));
  }, [filtered]);

  const sorted = [...filtered].sort(
    (a, b) => (a.school_class_name || "").localeCompare(b.school_class_name || "", undefined, { numeric: true }) || fullName(a).localeCompare(fullName(b))
  );

  const className = classes.find((c) => String(c.id) === classId)?.name;
  const filterSummary = `Class: ${className || "All classes"} · Status: ${status ? titleCase(status) : "All statuses"}`;

  return (
    <ReportPanel
      title="Students Report"
      subtitle="Enrolment summary and student register"
      filename="students-report"
      onBack={onBack}
      loading={loading}
      error={error}
      filterSummary={filterSummary}
      filters={
        <>
          <select value={classId} onChange={(e) => setClassId(e.target.value)}>
            <option value="">All classes</option>
            {classes.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All statuses</option>
            {["active", "transferred", "graduated", "suspended", "withdrawn"].map((s) => (
              <option key={s} value={s}>
                {titleCase(s)}
              </option>
            ))}
          </select>
        </>
      }
      stats={[
        { label: "Students", value: filtered.length },
        { label: "Boys", value: count((s) => s.gender === "male") },
        { label: "Girls", value: count((s) => s.gender === "female") },
        { label: "Active", value: count((s) => s.status === "active") },
      ]}
      sections={[
        {
          heading: "Enrolment by class",
          columns: [
            { label: "Class", value: (r) => r.name },
            { label: "Boys", value: (r) => r.male, align: "right" },
            { label: "Girls", value: (r) => r.female, align: "right" },
            { label: "Other", value: (r) => r.other, align: "right" },
            { label: "Total", value: (r) => r.total, align: "right" },
          ],
          rows: byClass,
          footer: byClass.length ? ["Total", byClass.reduce((a, r) => a + r.male, 0), byClass.reduce((a, r) => a + r.female, 0), byClass.reduce((a, r) => a + r.other, 0), filtered.length] : undefined,
        },
        {
          heading: "Student register",
          columns: [
            { label: "Index No.", value: (s) => s.index_number },
            { label: "Name", value: (s) => fullName(s) },
            { label: "Gender", value: (s) => titleCase(s.gender) },
            { label: "Date of birth", value: (s) => (s.date_of_birth ? formatDate(s.date_of_birth) : "") },
            { label: "Class", value: (s) => s.school_class_name },
            { label: "Stream", value: (s) => s.stream_name },
            { label: "Status", value: (s) => titleCase(s.status) },
            { label: "Emergency contact", value: (s) => [s.emergency_contact_name, s.emergency_contact_phone].filter(Boolean).join(" · ") },
          ],
          rows: sorted,
        },
      ]}
    />
  );
}
