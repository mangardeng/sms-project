import { useEffect, useMemo, useState } from "react";

import { usersApi } from "../../api/auth";
import { extractErrorMessage } from "../../api/client";
import ReportPanel from "../../components/ReportPanel";
import { fetchAll } from "../../utils/fetchAll";

export default function UsersReport({ onBack }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchAll(usersApi)
      .then(setUsers)
      .catch((err) => setError(extractErrorMessage(err, "Could not load the accounts report.")))
      .finally(() => setLoading(false));
  }, []);

  const byRole = useMemo(() => {
    const map = new Map();
    users.forEach((u) => {
      const k = u.role_display || u.role;
      const row = map.get(k) || { role: k, active: 0, inactive: 0 };
      if (u.is_active) row.active += 1;
      else row.inactive += 1;
      map.set(k, row);
    });
    return [...map.values()].sort((a, b) => a.role.localeCompare(b.role));
  }, [users]);

  return (
    <ReportPanel
      title="User Accounts Report"
      subtitle="Accounts by role and status"
      filename="user-accounts-report"
      onBack={onBack}
      loading={loading}
      error={error}
      stats={[
        { label: "Accounts", value: users.length },
        { label: "Active", value: users.filter((u) => u.is_active).length },
        { label: "Inactive", value: users.filter((u) => !u.is_active).length },
        { label: "Must change password", value: users.filter((u) => u.must_change_password).length },
      ]}
      sections={[
        {
          heading: "Accounts by role",
          columns: [
            { label: "Role", value: (r) => r.role },
            { label: "Active", value: (r) => r.active, align: "right" },
            { label: "Inactive", value: (r) => r.inactive, align: "right" },
            { label: "Total", value: (r) => r.active + r.inactive, align: "right" },
          ],
          rows: byRole,
        },
        {
          heading: "All accounts",
          columns: [
            { label: "Username", value: (u) => u.username },
            { label: "Name", value: (u) => `${u.first_name} ${u.last_name}`.trim() },
            { label: "Role", value: (u) => u.role_display },
            { label: "Email", value: (u) => u.email },
            { label: "Status", value: (u) => (u.is_active ? "Active" : "Inactive") },
          ],
          rows: users,
        },
      ]}
    />
  );
}
