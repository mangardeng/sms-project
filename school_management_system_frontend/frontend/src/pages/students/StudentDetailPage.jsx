import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { classesApi } from "../../api/classes";
import { extractErrorMessage } from "../../api/client";
import { studentsApi } from "../../api/students";
import AlertBanner from "../../components/AlertBanner";
import Avatar from "../../components/Avatar";
import Badge from "../../components/Badge";
import LoadingSpinner from "../../components/LoadingSpinner";
import Modal from "../../components/Modal";
import ResourceForm from "../../components/ResourceForm";
import { useAuth } from "../../context/AuthContext";
import { formatDate } from "../../utils/format";
import { mediaUrl } from "../../utils/media";
import { buildReportHtml, printHtml, escapeHtml } from "../../utils/print";
import { ROLES } from "../../utils/roles";

export default function StudentDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [student, setStudent] = useState(null);
  const [history, setHistory] = useState([]);
  const [classOptions, setClassOptions] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [transferOpen, setTransferOpen] = useState(false);

  const canManage = [ROLES.ADMIN, ROLES.REGISTRAR].includes(user?.role);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [studentData, historyData] = await Promise.all([
        studentsApi.get(id),
        studentsApi.transferHistory(id).catch(() => []),
      ]);
      setStudent(studentData);
      setHistory(historyData);
    } catch (err) {
      setError(extractErrorMessage(err, "Could not load this student. You may not have access to this record."));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (canManage) {
      classesApi.list({ page_size: 200 }).then((data) => {
        const list = data.results || data;
        setClassOptions(list.map((c) => ({ value: c.id, label: c.name })));
      });
    }
  }, [canManage]);

  async function handleTransfer(values) {
    await studentsApi.transfer(id, values);
    setTransferOpen(false);
    await load();
  }

  if (loading) return <LoadingSpinner ink />;
  if (error) return <AlertBanner type="error">{error}</AlertBanner>;
  if (!student) return null;

  const fullName = `${student.user?.first_name || ""} ${student.user?.last_name || ""}`.trim();

  function handlePrintProfile() {
    const cap = (v) => (v ? v[0].toUpperCase() + v.slice(1) : "");
    const profile = [
      ["Index number", student.index_number],
      ["Class", student.school_class_name],
      ["Stream", student.stream_name],
      ["Gender", cap(student.gender)],
      ["Date of birth", student.date_of_birth ? formatDate(student.date_of_birth) : ""],
      ["Admission date", student.admission_date ? formatDate(student.admission_date) : ""],
      ["Status", cap(student.status)],
      ["Email", student.user?.email],
      ["Phone", student.user?.phone_number],
      ["Address", student.address],
      ["Emergency contact", [student.emergency_contact_name, student.emergency_contact_phone].filter(Boolean).join(" · ")],
    ];
    // Reuse the standard report layout, then prepend the photo.
    let html = buildReportHtml({
      title: "Student Profile",
      subtitle: `${fullName} (${student.index_number})`,
      printedBy: `${user?.first_name || ""} ${user?.last_name || ""}`.trim() || user?.username,
      sections: [
        { heading: "Profile", columns: [{ label: "Item", value: (r) => r[0] }, { label: "Details", value: (r) => r[1] }], rows: profile },
        {
          heading: "Transfer history",
          columns: [
            { label: "From", value: (h) => h.from_class_name },
            { label: "To", value: (h) => h.to_class_name },
            { label: "Reason", value: (h) => h.reason },
            { label: "Date", value: (h) => formatDate(h.created_at) },
          ],
          rows: history,
        },
      ],
    });
    if (student.photo) {
      html = html.replace('<div class="doc-head">', `<div class="doc-head"><img class="photo" src="${escapeHtml(mediaUrl(student.photo))}" alt=""/>`);
    }
    printHtml(html);
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <button className="btn-ghost" type="button" onClick={() => navigate(-1)} style={{ marginBottom: 8 }}>
            ← Back
          </button>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <Avatar src={student.photo} name={fullName} size={72} />
            <div>
              <h1 style={{ margin: 0 }}>{fullName}</h1>
              <div className="subtitle">{student.index_number}</div>
            </div>
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          {user?.role !== ROLES.STUDENT && (
            <button className="btn btn-secondary" type="button" onClick={handlePrintProfile}>
              🖨 Print profile
            </button>
          )}
          {canManage && (
            <button className="btn btn-primary" type="button" onClick={() => setTransferOpen(true)}>
              Transfer to new class
            </button>
          )}
        </div>
      </div>

      <div className="form-grid" style={{ alignItems: "start", marginBottom: 20 }}>
        <div className="surface surface-pad">
          <h3>Profile</h3>
          <dl style={{ margin: 0 }}>
            <Row label="Email" value={student.user?.email || "—"} />
            <Row label="Phone" value={student.user?.phone_number || "—"} />
            <Row label="Class" value={student.school_class_name || "—"} />
            <Row label="Stream" value={student.stream_name || "—"} />
            <Row label="Gender" value={student.gender ? student.gender[0].toUpperCase() + student.gender.slice(1) : "—"} />
            <Row label="Date of birth" value={formatDate(student.date_of_birth)} />
            <Row label="Admission date" value={formatDate(student.admission_date)} />
            <Row label="Address" value={student.address || "—"} />
            <Row label="Status" value={<Badge tone="accent">{student.status}</Badge>} />
          </dl>
        </div>
        <div className="surface surface-pad">
          <h3>Emergency contact</h3>
          <Row label="Name" value={student.emergency_contact_name || "—"} />
          <Row label="Phone" value={student.emergency_contact_phone || "—"} />

          <h3 style={{ marginTop: 20 }}>Quick links</h3>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Link className="btn btn-secondary btn-sm" to={`/attendance?student=${id}`}>
              Attendance
            </Link>
            <Link className="btn btn-secondary btn-sm" to={`/examinations?student=${id}`}>
              Results
            </Link>
            <Link className="btn btn-secondary btn-sm" to={`/fees?student=${id}`}>
              Fees
            </Link>
          </div>
        </div>
      </div>

      <div className="surface surface-pad">
        <h3>Transfer history</h3>
        {history.length ? (
          <table className="data-table">
            <thead>
              <tr>
                <th>From</th>
                <th>To</th>
                <th>Reason</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {history.map((h) => (
                <tr key={h.id}>
                  <td>{h.from_class_name || "—"}</td>
                  <td>{h.to_class_name || "—"}</td>
                  <td>{h.reason || "—"}</td>
                  <td>{formatDate(h.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="hint">No transfers recorded.</p>
        )}
      </div>

      {transferOpen && (
        <Modal title="Transfer student" onClose={() => setTransferOpen(false)}>
          <ResourceForm
            fields={[
              { name: "to_class", label: "New class", type: "select", options: classOptions, required: true },
              { name: "reason", label: "Reason", type: "textarea" },
            ]}
            onSubmit={handleTransfer}
            onCancel={() => setTransferOpen(false)}
            submitLabel="Confirm transfer"
          />
        </Modal>
      )}
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", borderBottom: "1px solid var(--border)" }}>
      <span className="hint">{label}</span>
      <span>{value}</span>
    </div>
  );
}
