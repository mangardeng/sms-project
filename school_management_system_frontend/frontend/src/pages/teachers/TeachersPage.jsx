import Avatar from "../../components/Avatar";
import Badge from "../../components/Badge";
import { useState } from "react";
import ResourceManager from "../../components/ResourceManager";
import TeachersReport from "./TeachersReport";
import { teachersApi } from "../../api/teachers";
import { useAuth } from "../../context/AuthContext";
import { ROLES } from "../../utils/roles";

const GENDER_OPTIONS = [
  { value: "male", label: "Male" },
  { value: "female", label: "Female" },
  { value: "other", label: "Other" },
];

const fullName = (row) => `${row.user?.first_name || ""} ${row.user?.last_name || ""}`.trim();

export default function TeachersPage() {
  const { user } = useAuth();
  const canManage = user?.role === ROLES.ADMIN;
  const isSelf = user?.role === ROLES.TEACHER;
  const [view, setView] = useState("records");

  const photoField = { name: "photo", label: "Photo", type: "file" };

  const createFields = [
    photoField,
    { name: "username", label: "Login username", type: "text", required: true },
    { name: "first_name", label: "First name", type: "text", required: true },
    { name: "last_name", label: "Last name", type: "text", required: true },
    { name: "email", label: "Email", type: "email" },
    { name: "phone_number", label: "Phone number", type: "text" },
    { name: "password", label: "Temporary password", type: "password", required: true },
    { name: "staff_id", label: "Staff ID", type: "text", required: true, placeholder: "e.g. TCH0004" },
    { name: "gender", label: "Gender", type: "select", options: GENDER_OPTIONS },
    { name: "date_of_birth", label: "Date of birth", type: "date" },
    { name: "date_employed", label: "Date employed", type: "date" },
    { name: "qualification", label: "Qualification", type: "text" },
    { name: "address", label: "Address", type: "text" },
  ];

  const editFields = [
    photoField,
    { name: "first_name", label: "First name", type: "text", required: true },
    { name: "last_name", label: "Last name", type: "text", required: true },
    { name: "email", label: "Email", type: "email" },
    { name: "phone_number", label: "Phone number", type: "text" },
    { name: "staff_id", label: "Staff ID", type: "text", readOnly: true },
    { name: "gender", label: "Gender", type: "select", options: GENDER_OPTIONS },
    { name: "date_of_birth", label: "Date of birth", type: "date" },
    { name: "date_employed", label: "Date employed", type: "date" },
    { name: "qualification", label: "Qualification", type: "text" },
    { name: "address", label: "Address", type: "text" },
    { name: "is_active_staff", label: "Active", type: "checkbox", checkboxLabel: "Currently active staff member" },
  ];

  const mapRowToForm = (row) => ({
    ...row,
    first_name: row.user?.first_name ?? "",
    last_name: row.user?.last_name ?? "",
    email: row.user?.email ?? "",
    phone_number: row.user?.phone_number ?? "",
  });

  const columns = [
    { key: "photo", label: "Photo", render: (row) => <Avatar src={row.photo} name={fullName(row)} size={36} /> },
    { key: "staff_id", label: "Staff ID" },
    { key: "name", label: "Name", render: (row) => fullName(row) || "—" },
    { key: "qualification", label: "Qualification", render: (row) => row.qualification || "—" },
    { key: "assigned_class_count", label: "Classes assigned" },
    {
      key: "is_active_staff",
      label: "Status",
      render: (row) => <Badge tone={row.is_active_staff ? "accent" : "neutral"}>{row.is_active_staff ? "Active" : "Inactive"}</Badge>,
    },
  ];

  if (view === "report") return <TeachersReport onBack={() => setView("records")} />;

  return (
    <ResourceManager
      headerActions={
        <button className="btn btn-secondary" type="button" onClick={() => setView("report")}>
          📊 Reports
        </button>
      }
      title="Teachers"
      subtitle={canManage ? "Register and manage teacher accounts." : isSelf ? "Your teaching profile." : "Teacher directory."}
      api={teachersApi}
      columns={columns}
      createFields={canManage ? createFields : null}
      editFields={canManage || isSelf ? editFields : null}
      mapRowToForm={mapRowToForm}
      canCreate={canManage}
      canEdit={canManage || isSelf}
      canDelete={canManage}
      createLabel="Register teacher"
      emptyTitle="No teachers found"
    />
  );
}
