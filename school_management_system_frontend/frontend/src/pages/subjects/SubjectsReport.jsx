import { useEffect, useMemo, useState } from "react";

import { extractErrorMessage } from "../../api/client";
import { classSubjectsApi, subjectsApi } from "../../api/subjects";
import ReportPanel from "../../components/ReportPanel";
import { fetchAll, fetchAllSafe } from "../../utils/fetchAll";

export default function SubjectsReport({ onBack }) {
  const [subjects, setSubjects] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([fetchAll(subjectsApi), fetchAllSafe(classSubjectsApi)])
      .then(([s, a]) => {
        setSubjects(s);
        setAssignments(a);
      })
      .catch((err) => setError(extractErrorMessage(err, "Could not load the subjects report.")))
      .finally(() => setLoading(false));
  }, []);

  const rows = useMemo(
    () =>
      subjects.map((s) => {
        const mine = assignments.filter((a) => a.subject === s.id);
        return { ...s, classes: [...new Set(mine.map((a) => a.school_class_name))].sort(), teachers: [...new Set(mine.map((a) => a.teacher_name).filter(Boolean))] };
      }),
    [subjects, assignments]
  );
  const sortedAssignments = [...assignments].sort((a, b) => (a.school_class_name || "").localeCompare(b.school_class_name || "", undefined, { numeric: true }) || (a.subject_name || "").localeCompare(b.subject_name || ""));

  return (
    <ReportPanel
      title="Subjects Report"
      subtitle="Subject catalogue and class / teacher allocation"
      filename="subjects-report"
      onBack={onBack}
      loading={loading}
      error={error}
      stats={[
        { label: "Subjects", value: subjects.length },
        { label: "Compulsory", value: subjects.filter((s) => s.is_compulsory).length },
        { label: "Class assignments", value: assignments.length },
        { label: "Without teacher", value: assignments.filter((a) => !a.teacher).length },
      ]}
      sections={[
        {
          heading: "Subjects",
          columns: [
            { label: "Code", value: (s) => s.code },
            { label: "Subject", value: (s) => s.name },
            { label: "Compulsory", value: (s) => (s.is_compulsory ? "Yes" : "No") },
            { label: "Classes taught", value: (s) => s.classes.join(", ") },
            { label: "Teachers", value: (s) => s.teachers.join(", ") },
          ],
          rows,
        },
        {
          heading: "Class subject allocation",
          columns: [
            { label: "Class", value: (a) => a.school_class_name },
            { label: "Subject", value: (a) => a.subject_name },
            { label: "Teacher", value: (a) => a.teacher_name || "Unassigned" },
          ],
          rows: sortedAssignments,
        },
      ]}
    />
  );
}
