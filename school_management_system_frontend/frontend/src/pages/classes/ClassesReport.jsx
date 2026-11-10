import { useEffect, useMemo, useState } from "react";

import { classesApi } from "../../api/classes";
import { extractErrorMessage } from "../../api/client";
import ReportPanel from "../../components/ReportPanel";
import { fetchAll } from "../../utils/fetchAll";

export default function ClassesReport({ onBack }) {
  const [classes, setClasses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchAll(classesApi)
      .then(setClasses)
      .catch((err) => setError(extractErrorMessage(err, "Could not load the classes report.")))
      .finally(() => setLoading(false));
  }, []);

  const streams = useMemo(() => classes.flatMap((c) => (c.streams || []).map((s) => ({ ...s, className: c.name }))), [classes]);
  const totalStudents = classes.reduce((a, c) => a + (c.student_count || 0), 0);

  return (
    <ReportPanel
      title="Classes Report"
      subtitle="Class sizes, class teachers and stream capacity"
      filename="classes-report"
      onBack={onBack}
      loading={loading}
      error={error}
      stats={[
        { label: "Classes", value: classes.length },
        { label: "Active classes", value: classes.filter((c) => c.is_active).length },
        { label: "Streams", value: streams.length },
        { label: "Active students", value: totalStudents },
      ]}
      sections={[
        {
          heading: "Classes",
          columns: [
            { label: "Class", value: (c) => c.name },
            { label: "Class teacher", value: (c) => c.class_teacher_name },
            { label: "Streams", value: (c) => (c.streams || []).map((s) => s.name).join(", ") },
            { label: "Students", value: (c) => c.student_count ?? 0, align: "right" },
            { label: "Status", value: (c) => (c.is_active ? "Active" : "Inactive") },
          ],
          rows: classes,
          footer: classes.length ? ["Total", "", "", totalStudents, ""] : undefined,
        },
        {
          heading: "Stream capacity",
          columns: [
            { label: "Class", value: (s) => s.className },
            { label: "Stream", value: (s) => s.name },
            { label: "Capacity", value: (s) => s.capacity, align: "right" },
            { label: "Students", value: (s) => s.student_count ?? 0, align: "right" },
            { label: "Free seats", value: (s) => (s.capacity != null ? Math.max(0, s.capacity - (s.student_count || 0)) : ""), align: "right" },
          ],
          rows: streams,
        },
      ]}
    />
  );
}
