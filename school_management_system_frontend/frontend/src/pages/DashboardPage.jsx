import { useEffect, useState } from "react";

import { fetchDashboard } from "../api/dashboard";
import { extractErrorMessage } from "../api/client";
import AlertBanner from "../components/AlertBanner";
import LoadingSpinner from "../components/LoadingSpinner";
import { useAuth } from "../context/AuthContext";
import { ROLES } from "../utils/roles";
import {
  AccountantDashboard,
  AdminDashboard,
  HeadTeacherDashboard,
  LibrarianDashboard,
  ParentDashboard,
  RegistrarDashboard,
  StudentDashboard,
  TeacherDashboard,
} from "./dashboards/RoleDashboards";

const VIEWS = {
  [ROLES.ADMIN]: AdminDashboard,
  [ROLES.HEAD_TEACHER]: HeadTeacherDashboard,
  [ROLES.REGISTRAR]: RegistrarDashboard,
  [ROLES.TEACHER]: TeacherDashboard,
  [ROLES.ACCOUNTANT]: AccountantDashboard,
  [ROLES.LIBRARIAN]: LibrarianDashboard,
  [ROLES.PARENT]: ParentDashboard,
  [ROLES.STUDENT]: StudentDashboard,
};

export default function DashboardPage() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchDashboard()
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch((err) => {
        if (!cancelled) setError(extractErrorMessage(err, "Could not load your dashboard."));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const fullName = `${user?.first_name || ""} ${user?.last_name || ""}`.trim() || user?.username;
  const View = VIEWS[user?.role];

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Welcome, {fullName}</h1>
          <div className="subtitle">Here's what's happening today.</div>
        </div>
      </div>

      <AlertBanner type="error">{error}</AlertBanner>

      {loading ? <LoadingSpinner ink /> : View && data ? <View data={data} /> : null}
    </div>
  );
}
