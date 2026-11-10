import { Link } from "react-router-dom";

import Badge from "../../components/Badge";
import EmptyState from "../../components/EmptyState";
import StatCard from "../../components/StatCard";
import { formatCurrency, formatDate, formatDateTime, titleCase } from "../../utils/format";

function AttendanceBreakdown({ data }) {
  if (!data || data.total === 0) {
    return <p className="hint">No attendance recorded yet.</p>;
  }
  return (
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
      <Badge tone="accent">{data.present} present</Badge>
      <Badge tone="alert">{data.absent} absent</Badge>
      <Badge tone="gold">{data.late} late</Badge>
      <Badge tone="info">{data.excused} excused</Badge>
    </div>
  );
}

export function AdminDashboard({ data }) {
  return (
    <>
      <div className="stat-grid">
        <StatCard label="Active students" value={data.total_students} />
        <StatCard label="Active teachers" value={data.total_teachers} />
        <StatCard label="Parents" value={data.total_parents} />
        <StatCard label="Classes" value={data.total_classes} />
        <StatCard label="Fees collected this month" value={formatCurrency(data.fee_collection_this_month)} />
      </div>

      <div className="form-grid" style={{ alignItems: "start" }}>
        <div className="surface surface-pad">
          <h3>Attendance today</h3>
          <AttendanceBreakdown data={data.attendance_today} />
        </div>
        <div className="surface surface-pad">
          <h3>Examinations</h3>
          <p>
            {data.examinations_pending_publish?.published || 0} published ·{" "}
            {data.examinations_pending_publish?.unpublished || 0} awaiting publication of{" "}
            {data.examinations_pending_publish?.total || 0} total.
          </p>
        </div>
      </div>

      <div className="surface surface-pad" style={{ marginTop: 20 }}>
        <h3>Recent activity</h3>
        {data.recent_activities?.length ? (
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {data.recent_activities.map((a, i) => (
              <li key={i} style={{ marginBottom: 6, fontSize: "0.85rem" }}>
                <strong>{a.user}</strong> — {titleCase(a.action)} {a.model_name}
                {a.description ? `: ${a.description}` : ""}{" "}
                <span className="hint">({formatDateTime(a.timestamp)})</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="hint">No recent activity logged.</p>
        )}
      </div>
    </>
  );
}

export function HeadTeacherDashboard({ data }) {
  return (
    <>
      <div className="stat-grid">
        <StatCard label="Active students" value={data.total_students} />
        <StatCard label="Active teachers" value={data.total_teachers} />
        <StatCard
          label="Average exam performance"
          value={data.average_exam_percentage != null ? `${data.average_exam_percentage}%` : "—"}
        />
        <StatCard label="Fees collected this month" value={formatCurrency(data.fee_collection_this_month)} />
      </div>
      <div className="surface surface-pad">
        <h3>Attendance today</h3>
        <AttendanceBreakdown data={data.attendance_today} />
      </div>
    </>
  );
}

export function RegistrarDashboard({ data }) {
  const byClass = Object.entries(data.students_by_class || {});
  return (
    <>
      <div className="stat-grid">
        <StatCard label="Active students" value={data.total_active_students} />
        <StatCard label="Registrations (last 30 days)" value={data.recent_registrations} />
      </div>
      <div className="surface surface-pad">
        <h3>Students by class</h3>
        {byClass.length ? (
          <div className="form-grid">
            {byClass.map(([name, count]) => (
              <div key={name} style={{ display: "flex", justifyContent: "space-between" }}>
                <span>{name}</span>
                <strong>{count}</strong>
              </div>
            ))}
          </div>
        ) : (
          <p className="hint">No students registered yet.</p>
        )}
      </div>
    </>
  );
}

export function TeacherDashboard({ data }) {
  if (data.detail) return <EmptyState title={data.detail} />;
  return (
    <>
      <div className="stat-grid">
        <StatCard label="Assigned classes" value={data.assigned_classes?.length || 0} />
        <StatCard label="Students taught" value={data.total_students_taught} />
        <StatCard label="Subject assignments" value={data.assigned_subjects?.length || 0} />
      </div>

      <div className="form-grid" style={{ alignItems: "start" }}>
        <div className="surface surface-pad">
          <h3>Your classes</h3>
          {data.assigned_classes?.length ? (
            <ul style={{ margin: 0, paddingLeft: 18 }}>
              {data.assigned_classes.map((c) => (
                <li key={c.id}>{c.name}</li>
              ))}
            </ul>
          ) : (
            <p className="hint">No classes assigned yet.</p>
          )}
        </div>
        <div className="surface surface-pad">
          <h3>Attendance today (your classes)</h3>
          <AttendanceBreakdown data={data.attendance_today} />
        </div>
      </div>
    </>
  );
}

export function AccountantDashboard({ data }) {
  return (
    <>
      <div className="stat-grid">
        <StatCard label="Collected this month" value={formatCurrency(data.total_collected_this_month)} />
        <StatCard label="Collected all time" value={formatCurrency(data.total_collected_all_time)} />
      </div>
      <div className="surface surface-pad">
        <h3>Recent payments</h3>
        {data.recent_payments?.length ? (
          <table className="data-table">
            <thead>
              <tr>
                <th>Receipt</th>
                <th>Student</th>
                <th>Amount</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {data.recent_payments.map((p) => (
                <tr key={p.receipt_number}>
                  <td>{p.receipt_number}</td>
                  <td>{p.student}</td>
                  <td>{formatCurrency(p.amount)}</td>
                  <td>{formatDate(p.date)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="hint">No payments recorded yet.</p>
        )}
      </div>
    </>
  );
}

export function LibrarianDashboard({ data }) {
  return (
    <div className="stat-grid">
      <StatCard label="Total books" value={data.total_books} />
      <StatCard label="Available copies" value={data.available_books} />
      <StatCard label="Currently borrowed" value={data.borrowed_books} />
      <StatCard label="Overdue" value={data.overdue_books} />
      <StatCard label="Outstanding fines" value={formatCurrency(data.outstanding_fines)} />
    </div>
  );
}

export function ParentDashboard({ data }) {
  if (!data.children?.length) {
    return <EmptyState title="No linked children found" description="Contact the school office if this seems wrong." />;
  }
  return (
    <div className="form-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))" }}>
      {data.children.map((child) => (
        <div key={child.id} className="surface surface-pad">
          <h3>{child.name}</h3>
          <p className="hint" style={{ marginBottom: 10 }}>
            {child.index_number} · {child.school_class || "No class assigned"}
          </p>
          <div style={{ marginBottom: 10 }}>
            <AttendanceBreakdown data={child.attendance_summary} />
          </div>
          <p style={{ margin: "4px 0" }}>
            Average exam score:{" "}
            <strong>{child.average_exam_percentage != null ? `${child.average_exam_percentage}%` : "—"}</strong>
          </p>
          <p style={{ margin: "4px 0" }}>
            Fee balance: <strong>{formatCurrency(child.fee_balance)}</strong>
          </p>
          <Link to={`/students/${child.id}`} className="btn btn-secondary btn-sm" style={{ marginTop: 8 }}>
            View full profile
          </Link>
        </div>
      ))}
    </div>
  );
}

export function StudentDashboard({ data }) {
  if (data.detail) return <EmptyState title={data.detail} />;
  return (
    <>
      <div className="surface surface-pad" style={{ marginBottom: 20 }}>
        <h3>{data.profile.name}</h3>
        <p className="hint">
          {data.profile.index_number} · {data.profile.school_class || "No class"}{" "}
          {data.profile.stream ? `(${data.profile.stream})` : ""}
        </p>
      </div>

      <div className="stat-grid">
        <StatCard label="Fee balance" value={formatCurrency(data.fee_balance)} />
      </div>

      <div className="form-grid" style={{ alignItems: "start" }}>
        <div className="surface surface-pad">
          <h3>Attendance</h3>
          <AttendanceBreakdown data={data.attendance_summary} />
        </div>
        <div className="surface surface-pad">
          <h3>Recent results</h3>
          {data.recent_results?.length ? (
            <ul style={{ margin: 0, paddingLeft: 18 }}>
              {data.recent_results.map((r, i) => (
                <li key={i}>
                  {r.subject} — {r.examination}: <strong>{r.marks_obtained}</strong>{" "}
                  {r.grade && <Badge tone="gold">{r.grade}</Badge>}
                </li>
              ))}
            </ul>
          ) : (
            <p className="hint">No published results yet.</p>
          )}
        </div>
      </div>
    </>
  );
}
