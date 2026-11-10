import { useState } from "react";

import { extractErrorMessage } from "../../api/client";
import { usersApi } from "../../api/auth";
import AlertBanner from "../../components/AlertBanner";
import Badge from "../../components/Badge";
import Modal from "../../components/Modal";
import ResourceForm from "../../components/ResourceForm";
import ResourceManager from "../../components/ResourceManager";
import UsersReport from "./UsersReport";
import { ROLE_LABELS } from "../../utils/roles";

const ROLE_OPTIONS = Object.entries(ROLE_LABELS)
  .filter(([value]) => value !== "student") // Students are created via the Students module (auto index number).
  .map(([value, label]) => ({ value, label }));

export default function UsersPage() {
  const [resetFor, setResetFor] = useState(null);
  const [actionError, setActionError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);
  const [view, setView] = useState("records");

  const createFields = [
    { name: "username", label: "Username", type: "text", required: true },
    { name: "first_name", label: "First name", type: "text", required: true },
    { name: "last_name", label: "Last name", type: "text", required: true },
    { name: "email", label: "Email", type: "email" },
    { name: "phone_number", label: "Phone number", type: "text" },
    { name: "role", label: "Role", type: "select", options: ROLE_OPTIONS, required: true },
    { name: "password", label: "Temporary password", type: "password", required: true },
  ];

  const editFields = [
    { name: "first_name", label: "First name", type: "text" },
    { name: "last_name", label: "Last name", type: "text" },
    { name: "email", label: "Email", type: "email" },
    { name: "phone_number", label: "Phone number", type: "text" },
  ];

  async function handleToggleActive(row) {
    setActionError("");
    try {
      if (row.is_active) await usersApi.deactivate(row.id);
      else await usersApi.activate(row.id);
      setRefreshKey((k) => k + 1);
    } catch (err) {
      setActionError(extractErrorMessage(err));
    }
  }

  async function handleUnlock(row) {
    setActionError("");
    try {
      await usersApi.unlock(row.id);
      setRefreshKey((k) => k + 1);
    } catch (err) {
      setActionError(extractErrorMessage(err));
    }
  }

  async function handleResetPassword(values) {
    await usersApi.resetPassword(resetFor.id, values.new_password);
    setResetFor(null);
    setRefreshKey((k) => k + 1);
  }

  const columns = [
    { key: "username", label: "Username" },
    { key: "name", label: "Name", render: (row) => `${row.first_name} ${row.last_name}`.trim() },
    { key: "role_display", label: "Role" },
    {
      key: "is_active",
      label: "Status",
      render: (row) => <Badge tone={row.is_active ? "accent" : "neutral"}>{row.is_active ? "Active" : "Inactive"}</Badge>,
    },
  ];

  if (view === "report") return <UsersReport onBack={() => setView("records")} />;

  return (
    <div key={refreshKey}>
      <AlertBanner type="error">{actionError}</AlertBanner>
      <ResourceManager
        headerActions={
          <button className="btn btn-secondary" type="button" onClick={() => setView("report")}>
            📊 Reports
          </button>
        }
        canPrint={false}
        title="User Accounts"
        subtitle="Create accounts, assign roles, and manage account security."
        api={usersApi}
        columns={columns}
        createFields={createFields}
        editFields={editFields}
        createLabel="Create account"
        rowActions={(row) => (
          <>
            <button className="btn btn-secondary btn-sm" type="button" onClick={() => handleToggleActive(row)}>
              {row.is_active ? "Deactivate" : "Activate"}
            </button>
            <button className="btn btn-secondary btn-sm" type="button" onClick={() => handleUnlock(row)}>
              Unlock
            </button>
            <button className="btn btn-secondary btn-sm" type="button" onClick={() => setResetFor(row)}>
              Reset password
            </button>
          </>
        )}
        emptyTitle="No accounts found"
      />

      {resetFor && (
        <Modal title={`Reset password — ${resetFor.username}`} onClose={() => setResetFor(null)}>
          <ResourceForm
            fields={[{ name: "new_password", label: "New password", type: "password", required: true }]}
            onSubmit={handleResetPassword}
            onCancel={() => setResetFor(null)}
            submitLabel="Reset password"
          />
        </Modal>
      )}
    </div>
  );
}
