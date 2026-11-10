
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { notificationsApi } from "../api/notifications";
import { useAuth } from "../context/AuthContext";
import { initialsFor, ROLE_LABELS } from "../utils/roles";

export default function Topbar({ title, onToggleSidebar }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [unread, setUnread] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const data = await notificationsApi.unreadCount();

        if (!cancelled) {
          setUnread(data.unread_count || 0);
        }
      } catch {
        // Silently ignore
      }
    }

    poll();

    const id = setInterval(poll, 30000);

    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  const firstName = user?.first_name || "";
  const lastName = user?.last_name || "";
  const username = user?.username || "User";

  let fullName = firstName + " " + lastName;
  fullName = fullName.trim();

  if (!fullName) {
    fullName = username;
  }

  return (
    <header className="topbar">
      <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
        <button
          className="btn-ghost"
          type="button"
          onClick={onToggleSidebar}
          aria-label="Toggle navigation"
          style={{ display: "none" }}
          id="sidebar-toggle"
        >
          ☰
        </button>

        <span className="topbar-title">{title}</span>
      </div>

      <div
        className="topbar-right"
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
        }}
      >
        {/* Notifications */}
        <Link
          to="/notifications"
          className="btn-ghost"
          aria-label="Notifications"
          style={{ position: "relative" }}
        >
          🔔

          {unread > 0 && (
            <span
              style={{
                position: "absolute",
                top: -2,
                right: -2,
                background: "var(--alert)",
                color: "#fff",
                borderRadius: "999px",
                fontSize: "0.65rem",
                padding: "1px 5px",
                fontWeight: 700,
              }}
            >
              {unread > 9 ? "9+" : unread}
            </span>
          )}
        </Link>

        {/* User */}
        <div className="user-chip">
          <span className="avatar">{initialsFor(fullName)}</span>

          <span className="who">
            <span className="name">{fullName}</span>

            <span className="role">
              {ROLE_LABELS[user?.role] || user?.role}
            </span>
          </span>
        </div>

        {/* Change Password */}
        <Link
          to="/change-password"
          className="btn-ghost"
          style={{
            textDecoration: "none",
            whiteSpace: "nowrap",
          }}
        >
          🔑 Change password
        </Link>

        {/* Log Out */}
        <button
          type="button"
          className="btn-ghost"
          onClick={handleLogout}
          style={{
            border: "none",
            cursor: "pointer",
            whiteSpace: "nowrap",
          }}
        >
          🚪 Log out
        </button>
      </div>
    </header>
  );
}
