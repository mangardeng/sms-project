import { useEffect, useMemo, useState } from "react";

import { extractErrorMessage } from "../../api/client";
import { parentsApi } from "../../api/parents";
import ReportPanel from "../../components/ReportPanel";
import { fetchAll } from "../../utils/fetchAll";
import { fullName, titleCase } from "../../utils/format";

export default function ParentsReport({ onBack }) {
  const [parents, setParents] = useState([]);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchAll(parentsApi)
      .then(setParents)
      .catch((err) => setError(extractErrorMessage(err, "Could not load the parents report.")))
      .finally(() => setLoading(false));
  }, []);

  const rows = useMemo(
    () => parents.filter((p) => !filter || (filter === "unlinked" ? !(p.linked_students || []).length : (p.linked_students || []).length > 0)),
    [parents, filter]
  );
  const links = rows.reduce((a, p) => a + (p.linked_students?.length || 0), 0);

  return (
    <ReportPanel
      title="Parents Report"
      subtitle="Parent / guardian contacts and linked children"
      filename="parents-report"
      onBack={onBack}
      loading={loading}
      error={error}
      filterSummary={`Showing: ${filter === "unlinked" ? "Parents with no linked child" : filter === "linked" ? "Parents with linked children" : "All parents"}`}
      filters={
        <select value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="">All parents</option>
          <option value="linked">With linked children</option>
          <option value="unlinked">No linked child</option>
        </select>
      }
      stats={[
        { label: "Parents", value: rows.length },
        { label: "Linked children", value: links },
        { label: "No linked child", value: rows.filter((p) => !(p.linked_students || []).length).length },
      ]}
      sections={[
        {
          heading: "Parents and guardians",
          columns: [
            { label: "Name", value: (p) => fullName(p) },
            { label: "Phone", value: (p) => p.user?.phone_number },
            { label: "Alt. phone", value: (p) => p.alternate_phone },
            { label: "Occupation", value: (p) => p.occupation },
            { label: "Address", value: (p) => p.address },
            {
              label: "Children",
              value: (p) =>
                (p.linked_students || []).map((l) => `${l.student_name} (${l.student_index_number}${l.relationship ? `, ${titleCase(l.relationship)}` : ""})`).join("; "),
            },
          ],
          rows,
        },
      ]}
    />
  );
}
