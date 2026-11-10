import { useEffect, useState } from "react";

import { academicYearsApi, termsApi } from "../../api/academic";
import { extractErrorMessage } from "../../api/client";
import ReportPanel from "../../components/ReportPanel";
import { fetchAll } from "../../utils/fetchAll";
import { formatDate } from "../../utils/format";

function daysBetween(a, b) {
  const d = Math.round((new Date(b) - new Date(a)) / 86400000) + 1;
  return Number.isNaN(d) ? "" : d;
}

export default function AcademicReport({ onBack }) {
  const [years, setYears] = useState([]);
  const [terms, setTerms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([fetchAll(academicYearsApi), fetchAll(termsApi)])
      .then(([y, t]) => {
        setYears(y);
        setTerms(t);
      })
      .catch((err) => setError(extractErrorMessage(err, "Could not load the calendar report.")))
      .finally(() => setLoading(false));
  }, []);

  const sortedTerms = [...terms].sort((a, b) => new Date(a.start_date) - new Date(b.start_date));
  const currentYear = years.find((y) => y.is_current);
  const currentTerm = terms.find((t) => t.is_current);

  return (
    <ReportPanel
      title="Academic Calendar Report"
      subtitle="Academic years and term dates"
      filename="academic-calendar"
      onBack={onBack}
      loading={loading}
      error={error}
      stats={[
        { label: "Academic years", value: years.length },
        { label: "Terms", value: terms.length },
        { label: "Current year", value: currentYear?.name || "—" },
        { label: "Current term", value: currentTerm?.display_name?.split(" - ")[0] || currentTerm?.name || "—" },
      ]}
      sections={[
        {
          heading: "Academic years",
          columns: [
            { label: "Academic year", value: (y) => y.name },
            { label: "Starts", value: (y) => formatDate(y.start_date) },
            { label: "Ends", value: (y) => formatDate(y.end_date) },
            { label: "Days", value: (y) => daysBetween(y.start_date, y.end_date), align: "right" },
            { label: "Current", value: (y) => (y.is_current ? "Yes" : "") },
          ],
          rows: years,
        },
        {
          heading: "Terms",
          columns: [
            { label: "Academic year", value: (t) => t.academic_year_name },
            { label: "Term", value: (t) => t.display_name?.split(" - ")[0] || t.name },
            { label: "Starts", value: (t) => formatDate(t.start_date) },
            { label: "Ends", value: (t) => formatDate(t.end_date) },
            { label: "Days", value: (t) => daysBetween(t.start_date, t.end_date), align: "right" },
            { label: "Current", value: (t) => (t.is_current ? "Yes" : "") },
          ],
          rows: sortedTerms,
        },
      ]}
    />
  );
}
