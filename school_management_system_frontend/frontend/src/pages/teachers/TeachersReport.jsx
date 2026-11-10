import { useEffect, useMemo, useState } from "react";

import { extractErrorMessage } from "../../api/client";
import { teachersApi } from "../../api/teachers";
import ReportPanel from "../../components/ReportPanel";
import { fetchAll } from "../../utils/fetchAll";
import { formatDate, fullName, titleCase } from "../../utils/format";

export default function TeachersReport({ onBack }) {
  const [teachers, setTeachers] = useState([]);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchAll(teachersApi)
      .then(setTeachers)
      .catch((err) => setError(extractErrorMessage(err, "Could not load the teacher report.")))
      .finally(() => setLoading(false));
  }, []);

  const rows = useMemo(
    () => teachers.filter((t) => !filter || (filter === "active" ? t.is_active_staff : !t.is_active_staff)),
    [teachers, filter]
  );

  return (
    <ReportPanel
      title="Teachers Report"
      subtitle="Staff register and class allocation"
      filename="teachers-report"
      onBack={onBack}
      loading={loading}
      error={error}
      filterSummary={`Status: ${filter ? titleCase(filter) : "All staff"}`}
      filters={
        <select value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="">All staff</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
      }
      stats={[
        { label: "Teachers", value: rows.length },
        { label: "Active", value: rows.filter((t) => t.is_active_staff).length },
        { label: "Inactive", value: rows.filter((t) => !t.is_active_staff).length },
        { label: "Class assignments", value: rows.reduce((a, t) => a + (t.assigned_class_count || 0), 0) },
      ]}
      sections={[
        {
          heading: "Teaching staff",
          columns: [
            { label: "Staff ID", value: (t) => t.staff_id },
            { label: "Name", value: (t) => fullName(t) },
            { label: "Gender", value: (t) => titleCase(t.gender) },
            { label: "Qualification", value: (t) => t.qualification },
            { label: "Date employed", value: (t) => (t.date_employed ? formatDate(t.date_employed) : "") },
            { label: "Phone", value: (t) => t.user?.phone_number },
            { label: "Classes", value: (t) => t.assigned_class_count ?? 0, align: "right" },
            { label: "Status", value: (t) => (t.is_active_staff ? "Active" : "Inactive") },
          ],
          rows,
        },
      ]}
    />
  );
}
