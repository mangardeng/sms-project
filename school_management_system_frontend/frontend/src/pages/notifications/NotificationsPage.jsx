import { useCallback, useEffect, useState } from "react";

import { extractErrorMessage } from "../../api/client";
import { notificationsApi } from "../../api/notifications";
import AlertBanner from "../../components/AlertBanner";
import Badge from "../../components/Badge";
import LoadingSpinner from "../../components/LoadingSpinner";
import Modal from "../../components/Modal";
import ResourceForm from "../../components/ResourceForm";
import { useAuth } from "../../context/AuthContext";
import { formatDateTime, titleCase } from "../../utils/format";
import { ROLES } from "../../utils/roles";

const CATEGORY_TONE = {
  announcement: "info",
  exam_result: "gold",
  fee_reminder: "alert",
  attendance_alert: "alert",
  library: "neutral",
  general: "neutral",
};

const CATEGORY_OPTIONS = [
  { value: "announcement", label: "School Announcement" },
  { value: "exam_result", label: "Examination Result" },
  { value: "fee_reminder", label: "Fee Reminder" },
  { value: "attendance_alert", label: "Attendance Alert" },
  { value: "library", label: "Library" },
  { value: "general", label: "General" },
];

const CHANNEL_OPTIONS = [
  { value: "in_app", label: "In-App" },
  { value: "email", label: "Email" },
  { value: "sms", label: "SMS" },
];

export default function NotificationsPage() {
  const { user } = useAuth();
  const canBroadcast = [ROLES.ADMIN, ROLES.HEAD_TEACHER].includes(user?.role);

  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [broadcastOpen, setBroadcastOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await notificationsApi.list({ page_size: 100 });
      setNotifications(data.results || data);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleMarkRead(id) {
    await notificationsApi.markRead(id);
    load();
  }

  async function handleMarkAllRead() {
    await notificationsApi.markAllRead();
    load();
  }

  async function handleBroadcast(values) {
    const payload = { ...values };
    if (!payload.role) delete payload.role;
    await notificationsApi.broadcast(payload);
    setBroadcastOpen(false);
    load();
  }

  return (
    <div>
      <div className="page-header">
        <h1>Notifications</h1>
        <div style={{ display: "flex", gap: 10 }}>
          <button className="btn btn-secondary" type="button" onClick={handleMarkAllRead}>
            Mark all read
          </button>
          {canBroadcast && (
            <button className="btn btn-primary" type="button" onClick={() => setBroadcastOpen(true)}>
              + Broadcast announcement
            </button>
          )}
        </div>
      </div>

      <AlertBanner type="error">{error}</AlertBanner>

      {loading ? (
        <LoadingSpinner ink />
      ) : notifications.length === 0 ? (
        <p className="hint">You have no notifications.</p>
      ) : (
        <div className="surface">
          {notifications.map((n) => (
            <div
              key={n.id}
              style={{
                padding: "14px 18px",
                borderBottom: "1px solid var(--border)",
                background: n.is_read ? "transparent" : "var(--accent-soft)",
                display: "flex",
                justifyContent: "space-between",
                gap: 14,
                alignItems: "flex-start",
              }}
            >
              <div>
                <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 4 }}>
                  <strong>{n.title}</strong>
                  <Badge tone={CATEGORY_TONE[n.category] || "neutral"}>{titleCase(n.category)}</Badge>
                </div>
                <p style={{ margin: "0 0 4px", maxWidth: "60ch" }}>{n.message}</p>
                <span className="hint">
                  {formatDateTime(n.created_at)}
                  {n.created_by_name ? ` · From ${n.created_by_name}` : ""}
                  {n.channel && n.channel !== "in_app" ? ` · ${titleCase(n.channel)}` : ""}
                </span>
              </div>
              {!n.is_read && (
                <button className="btn btn-secondary btn-sm" type="button" onClick={() => handleMarkRead(n.id)}>
                  Mark read
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {broadcastOpen && (
        <Modal title="Broadcast announcement" onClose={() => setBroadcastOpen(false)}>
          <ResourceForm
            fields={[
              {
                name: "role",
                label: "Send to",
                type: "select",
                options: [
                  { value: "", label: "Everyone" },
                  { value: "admin", label: "System Administrators" },
                  { value: "head_teacher", label: "Head Teachers" },
                  { value: "registrar", label: "Registrars" },
                  { value: "teacher", label: "Teachers" },
                  { value: "accountant", label: "Accountants" },
                  { value: "librarian", label: "Librarians" },
                  { value: "parent", label: "Parents" },
                  { value: "student", label: "Students" },
                ],
              },
              { name: "category", label: "Category", type: "select", options: CATEGORY_OPTIONS, required: true },
              { name: "channel", label: "Delivery channel", type: "select", options: CHANNEL_OPTIONS, required: true },
              { name: "title", label: "Title", type: "text", required: true },
              { name: "message", label: "Message", type: "textarea", required: true, rows: 4 },
            ]}
            initialValues={{ category: "announcement", channel: "in_app" }}
            onSubmit={handleBroadcast}
            onCancel={() => setBroadcastOpen(false)}
            submitLabel="Send"
          />
        </Modal>
      )}
    </div>
  );
}
