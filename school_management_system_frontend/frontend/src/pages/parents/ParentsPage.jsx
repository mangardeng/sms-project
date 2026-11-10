import { useEffect, useState } from "react";

import { parentsApi } from "../../api/parents";
import { studentsApi } from "../../api/students";
import ResourceManager from "../../components/ResourceManager";
import ParentsReport from "./ParentsReport";
import { useAuth } from "../../context/AuthContext";
import { ROLES } from "../../utils/roles";

export default function ParentsPage() {
  const { user } = useAuth();
  const canManage = [ROLES.ADMIN, ROLES.REGISTRAR].includes(user?.role);
  const [studentOptions, setStudentOptions] = useState([]);
  const [view, setView] = useState("records");

  useEffect(() => {
    if (canManage) {
      studentsApi.list({ page_size: 200 }).then((data) => {
        const list = data.results || data;
        setStudentOptions(
          list.map((s) => ({
            value: s.id,
            label: `${s.index_number} — ${s.user?.first_name || ""} ${s.user?.last_name || ""}`.trim(),
          }))
        );
      });
    }
  }, [canManage]);

  const createFields = [
    { name: "username", label: "Login username", type: "text", required: true },
    { name: "first_name", label: "First name", type: "text", required: true },
    { name: "last_name", label: "Last name", type: "text", required: true },
    { name: "email", label: "Email", type: "email" },
    { name: "phone_number", label: "Phone number", type: "text" },
    { name: "password", label: "Temporary password", type: "password", required: true },
    { name: "address", label: "Address", type: "text" },
    { name: "occupation", label: "Occupation", type: "text" },
    { name: "alternate_phone", label: "Alternate phone", type: "text" },
    {
      name: "relationship",
      label: "Relationship to child/children",
      type: "select",
      options: [
        { value: "father", label: "Father" },
        { value: "mother", label: "Mother" },
        { value: "guardian", label: "Guardian" },
        { value: "other", label: "Other" },
      ],
    },
    {
      name: "student_ids",
      label: "Link to student(s)",
      type: "multiselect",
      options: studentOptions,
      hint: "Hold Ctrl/Cmd to select more than one child.",
    },
  ];

  const editFields = [
    { name: "first_name", label: "First name", type: "text", required: true },
    { name: "last_name", label: "Last name", type: "text", required: true },
    { name: "email", label: "Email", type: "email" },
    { name: "phone_number", label: "Phone number", type: "text" },
    { name: "address", label: "Address", type: "text" },
    { name: "occupation", label: "Occupation", type: "text" },
    { name: "alternate_phone", label: "Alternate phone", type: "text" },
  ];

  const mapRowToForm = (row) => ({
    ...row,
    first_name: row.user?.first_name ?? "",
    last_name: row.user?.last_name ?? "",
    email: row.user?.email ?? "",
    phone_number: row.user?.phone_number ?? "",
  });

  const columns = [
    { key: "name", label: "Name", render: (row) => `${row.user?.first_name || ""} ${row.user?.last_name || ""}`.trim() },
    { key: "phone_number", label: "Phone", render: (row) => row.user?.phone_number || "—" },
    { key: "occupation", label: "Occupation" },
    {
      key: "linked_students",
      label: "Linked children",
      render: (row) => (row.linked_students?.length ? row.linked_students.map((l) => l.student_index_number).join(", ") : "—"),
    },
  ];

  if (view === "report") return <ParentsReport onBack={() => setView("records")} />;

  return (
    <ResourceManager
      headerActions={
        <button className="btn btn-secondary" type="button" onClick={() => setView("report")}>
          📊 Reports
        </button>
      }
      title="Parents"
      subtitle={canManage ? "Register parents and link them to their children." : "Parent accounts."}
      api={parentsApi}
      columns={columns}
      createFields={canManage ? createFields : null}
      editFields={editFields}
      mapRowToForm={mapRowToForm}
      canCreate={canManage}
      canEdit={canManage || user?.role === ROLES.PARENT}
      canDelete={canManage}
      createLabel="Register parent"
      emptyTitle="No parents found"
    />
  );
}
