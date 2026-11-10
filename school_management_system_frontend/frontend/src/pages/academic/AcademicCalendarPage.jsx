import { useEffect, useState } from "react";

import { academicYearsApi, termsApi } from "../../api/academic";
import Badge from "../../components/Badge";
import ResourceManager from "../../components/ResourceManager";
import AcademicReport from "./AcademicReport";
import { useAuth } from "../../context/AuthContext";
import { formatDate } from "../../utils/format";
import { ROLES } from "../../utils/roles";

const TERM_OPTIONS = [
  { value: "term_1", label: "Term 1" },
  { value: "term_2", label: "Term 2" },
  { value: "term_3", label: "Term 3" },
];

const CurrentBadge = ({ value }) => (value ? <Badge tone="accent">Current</Badge> : <span>—</span>);

export default function AcademicCalendarPage() {
  const { user } = useAuth();
  const canManage = user?.role === ROLES.ADMIN;
  const [tab, setTab] = useState("years");
  const [yearOptions, setYearOptions] = useState([]);

  // Reload the year dropdown whenever the Terms tab is opened so a newly added year is available.
  useEffect(() => {
    if (tab === "terms") {
      academicYearsApi.list({ page_size: 100 }).then((d) => setYearOptions((d.results || d).map((y) => ({ value: y.id, label: y.name }))));
    }
  }, [tab]);

  const yearFields = [
    { name: "name", label: "Academic year", type: "text", required: true, placeholder: "e.g. 2026/2027" },
    { name: "start_date", label: "Start date", type: "date", required: true },
    { name: "end_date", label: "End date", type: "date", required: true },
    { name: "is_current", label: "Current year", type: "checkbox", checkboxLabel: "This is the current academic year" },
  ];

  const termFields = [
    { name: "academic_year", label: "Academic year", type: "select", options: yearOptions, required: true },
    { name: "name", label: "Term", type: "select", options: TERM_OPTIONS, required: true },
    { name: "start_date", label: "Start date", type: "date", required: true },
    { name: "end_date", label: "End date", type: "date", required: true },
    { name: "is_current", label: "Current term", type: "checkbox", checkboxLabel: "This is the current term" },
  ];

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Academic Calendar</h1>
          <div className="subtitle">
            {canManage ? "Configure academic years and their terms." : "The school's academic years and terms."}
          </div>
        </div>
      </div>

      <div className="toolbar">
        <button className={`btn btn-sm ${tab === "years" ? "btn-primary" : "btn-secondary"}`} type="button" onClick={() => setTab("years")}>
          Academic years
        </button>
        <button className={`btn btn-sm ${tab === "terms" ? "btn-primary" : "btn-secondary"}`} type="button" onClick={() => setTab("terms")}>
          Terms
        </button>
        <button className={`btn btn-sm ${tab === "report" ? "btn-primary" : "btn-secondary"}`} type="button" onClick={() => setTab("report")}>
          📊 Report
        </button>
      </div>

      {tab === "report" ? (
        <AcademicReport />
      ) : tab === "years" ? (
        <ResourceManager
          key="years"
          title=""
          api={academicYearsApi}
          columns={[
            { key: "name", label: "Academic year" },
            { key: "start_date", label: "Starts", render: (row) => formatDate(row.start_date) },
            { key: "end_date", label: "Ends", render: (row) => formatDate(row.end_date) },
            { key: "is_current", label: "Current", render: (row) => <CurrentBadge value={row.is_current} /> },
          ]}
          formFields={canManage ? yearFields : null}
          canCreate={canManage}
          canEdit={canManage}
          canDelete={canManage}
          createLabel="Add academic year"
          emptyTitle="No academic years yet"
          emptyDescription={canManage ? "Add the first academic year, then its terms." : undefined}
        />
      ) : (
        <ResourceManager
          key="terms"
          title=""
          api={termsApi}
          columns={[
            { key: "academic_year_name", label: "Academic year" },
            { key: "name", label: "Term", render: (row) => row.display_name?.split(" - ")[0] || row.name },
            { key: "start_date", label: "Starts", render: (row) => formatDate(row.start_date) },
            { key: "end_date", label: "Ends", render: (row) => formatDate(row.end_date) },
            { key: "is_current", label: "Current", render: (row) => <CurrentBadge value={row.is_current} /> },
          ]}
          formFields={canManage ? termFields : null}
          canCreate={canManage}
          canEdit={canManage}
          canDelete={canManage}
          createLabel="Add term"
          emptyTitle="No terms yet"
        />
      )}
    </div>
  );
}
