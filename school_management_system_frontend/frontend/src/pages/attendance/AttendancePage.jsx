import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { attendanceApi } from "../../api/attendance";
import { classesApi } from "../../api/classes";
import { extractErrorMessage } from "../../api/client";
import { studentsApi } from "../../api/students";
import AlertBanner from "../../components/AlertBanner";
import Badge from "../../components/Badge";
import LoadingSpinner from "../../components/LoadingSpinner";
import { useAuth } from "../../context/AuthContext";
import { formatDate, fullName } from "../../utils/format";
import { printReport } from "../../utils/print";
import AttendanceReport from "./AttendanceReport";
import { ROLES } from "../../utils/roles";

const STATUS_OPTIONS = ["present", "absent", "late", "excused"];
const STATUS_TONE = { present: "accent", absent: "alert", late: "gold", excused: "info" };

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

export default function AttendancePage() {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const canRecord = [ROLES.ADMIN, ROLES.TEACHER].includes(user?.role);
  const [view, setView] = useState("records");
  const studentFilter = searchParams.get("student");

  if (view === "report") return <AttendanceReport onBack={() => setView("records")} studentFilter={canRecord ? null : studentFilter} />;

  const reportButton =
    user?.role === ROLES.STUDENT ? null : (
      <button className="btn btn-secondary" type="button" onClick={() => setView("report")}>
        📊 Reports
      </button>
    );
  if (canRecord) return <RecordAttendance reportButton={reportButton} />;
  return <ViewAttendance studentFilter={studentFilter} reportButton={reportButton} />;
}

function printedBy(user) {
  return `${user?.first_name || ""} ${user?.last_name || ""}`.trim() || user?.username;
}

function RecordAttendance({ reportButton }) {
  const { user } = useAuth();
  const [classes, setClasses] = useState([]);
  const [schoolClass, setSchoolClass] = useState("");
  const [date, setDate] = useState(todayISO());
  const [students, setStudents] = useState([]);
  const [entries, setEntries] = useState({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    classesApi.list({ page_size: 200 }).then((data) => {
      const list = data.results || data;
      setClasses(list);
      if (list.length && !schoolClass) setSchoolClass(String(list[0].id));
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!schoolClass) return;
    let cancelled = false;
    setLoading(true);
    setError("");

    Promise.all([
      studentsApi.list({ school_class: schoolClass, status: "active", page_size: 200 }),
      attendanceApi.list({ school_class: schoolClass, date, page_size: 200 }),
    ])
      .then(([studentData, attendanceData]) => {
        if (cancelled) return;
        const studentList = studentData.results || studentData;
        setStudents(studentList);
        const existing = attendanceData.results || attendanceData;
        const map = {};
        studentList.forEach((s) => {
          const found = existing.find((a) => a.student === s.id);
          map[s.id] = { status: found?.status || "present", remarks: found?.remarks || "" };
        });
        setEntries(map);
      })
      .catch((err) => !cancelled && setError(extractErrorMessage(err)))
      .finally(() => !cancelled && setLoading(false));

    return () => {
      cancelled = true;
    };
  }, [schoolClass, date]);

  function updateEntry(studentId, field, value) {
    setEntries((prev) => ({ ...prev, [studentId]: { ...prev[studentId], [field]: value } }));
  }

  async function handleSave() {
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      await attendanceApi.bulkRecord({
        school_class: schoolClass,
        date,
        entries: students.map((s) => ({
          student: s.id,
          status: entries[s.id]?.status || "present",
          remarks: entries[s.id]?.remarks || "",
        })),
      });
      setSuccess("Attendance saved for the class.");
    } catch (err) {
      setError(extractErrorMessage(err, "Could not save attendance."));
    } finally {
      setSaving(false);
    }
  }

  function handlePrintRegister() {
    const className = classes.find((c) => String(c.id) === String(schoolClass))?.name;
    printReport({
      title: `Class Attendance Register${className ? ` — ${className}` : ""}`,
      subtitle: formatDate(date),
      stats: STATUS_OPTIONS.map((s) => ({
        label: s[0].toUpperCase() + s.slice(1),
        value: students.filter((st) => (entries[st.id]?.status || "present") === s).length,
      })),
      sections: [
        {
          columns: [
            { label: "#", value: (r) => r.n, align: "right" },
            { label: "Index No.", value: (r) => r.s.index_number },
            { label: "Name", value: (r) => fullName(r.s) },
            { label: "Status", value: (r) => (entries[r.s.id]?.status || "present").toUpperCase() },
            { label: "Remarks", value: (r) => entries[r.s.id]?.remarks },
          ],
          rows: students.map((s, i) => ({ s, n: i + 1 })),
        },
      ],
      printedBy: printedBy(user),
    });
  }

  return (
    <div>
      <div className="page-header">
        <h1>Attendance</h1>
        <div style={{ display: "flex", gap: 8 }}>
          {reportButton}
          <button className="btn btn-secondary" type="button" onClick={handlePrintRegister} disabled={loading || !students.length}>
            🖨 Print register
          </button>
        </div>
      </div>

      <div className="toolbar">
        <select value={schoolClass} onChange={(e) => setSchoolClass(e.target.value)}>
          {classes.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        <button className="btn btn-primary" type="button" onClick={handleSave} disabled={saving || loading || !students.length}>
          {saving ? "Saving…" : "Save attendance"}
        </button>
      </div>

      <AlertBanner type="error">{error}</AlertBanner>
      <AlertBanner type="success">{success}</AlertBanner>

      {loading ? (
        <LoadingSpinner ink />
      ) : students.length === 0 ? (
        <p className="hint">No active students in this class.</p>
      ) : (
        <div className="surface">
          <div className="data-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Index No.</th>
                  <th>Name</th>
                  <th>Status</th>
                  <th>Remarks</th>
                </tr>
              </thead>
              <tbody>
                {students.map((s) => (
                  <tr key={s.id}>
                    <td>{s.index_number}</td>
                    <td>{`${s.user?.first_name || ""} ${s.user?.last_name || ""}`.trim()}</td>
                    <td>
                      <select
                        value={entries[s.id]?.status || "present"}
                        onChange={(e) => updateEntry(s.id, "status", e.target.value)}
                      >
                        {STATUS_OPTIONS.map((opt) => (
                          <option key={opt} value={opt}>
                            {opt}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <input
                        type="text"
                        value={entries[s.id]?.remarks || ""}
                        onChange={(e) => updateEntry(s.id, "remarks", e.target.value)}
                        placeholder="Optional"
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function ViewAttendance({ studentFilter, reportButton }) {
  const { user } = useAuth();
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const params = useMemo(() => (studentFilter ? { student: studentFilter, page_size: 100 } : { page_size: 100 }), [studentFilter]);

  useEffect(() => {
    setLoading(true);
    attendanceApi
      .list(params)
      .then((data) => setRecords(data.results || data))
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [params]);

  return (
    <div>
      <div className="page-header">
        <h1>Attendance</h1>
        <div style={{ display: "flex", gap: 8 }}>
          {reportButton}
          {user?.role !== ROLES.STUDENT && (
          <button
            className="btn btn-secondary"
            type="button"
            disabled={loading || !records.length}
            onClick={() =>
              printReport({
                title: "Attendance Records",
                subtitle: records[0] && studentFilter ? `${records[0].student_name} (${records[0].student_index_number})` : undefined,
                sections: [
                  {
                    columns: [
                      { label: "Date", value: (r) => formatDate(r.date) },
                      { label: "Student", value: (r) => `${r.student_name} (${r.student_index_number})` },
                      { label: "Class", value: (r) => r.school_class_name },
                      { label: "Status", value: (r) => r.status },
                      { label: "Remarks", value: (r) => r.remarks },
                    ],
                    rows: records,
                  },
                ],
                printedBy: printedBy(user),
              })
            }
          >
            🖨 Print
          </button>
          )}
        </div>
      </div>
      <AlertBanner type="error">{error}</AlertBanner>
      {loading ? (
        <LoadingSpinner ink />
      ) : records.length === 0 ? (
        <p className="hint">No attendance records found.</p>
      ) : (
        <div className="surface">
          <div className="data-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Student</th>
                  <th>Class</th>
                  <th>Status</th>
                  <th>Remarks</th>
                </tr>
              </thead>
              <tbody>
                {records.map((r) => (
                  <tr key={r.id}>
                    <td>{formatDate(r.date)}</td>
                    <td>
                      {r.student_name} <span className="hint">({r.student_index_number})</span>
                    </td>
                    <td>{r.school_class_name}</td>
                    <td>
                      <Badge tone={STATUS_TONE[r.status] || "neutral"}>{r.status}</Badge>
                    </td>
                    <td>{r.remarks || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
