import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { classesApi, streamsApi } from "../../api/classes";
import { studentsApi } from "../../api/students";
import Avatar from "../../components/Avatar";
import Badge from "../../components/Badge";
import ResourceManager from "../../components/ResourceManager";
import StudentsReport from "./StudentsReport";
import { useAuth } from "../../context/AuthContext";
import { ROLES } from "../../utils/roles";

const STATUS_TONE = {
  active: "accent",
  transferred: "info",
  graduated: "gold",
  suspended: "alert",
  withdrawn: "neutral",
};

const GENDER_OPTIONS = [
  { value: "male", label: "Male" },
  { value: "female", label: "Female" },
  { value: "other", label: "Other" },
];

const STATUS_OPTIONS = [
  { value: "active", label: "Active" },
  { value: "transferred", label: "Transferred" },
  { value: "graduated", label: "Graduated" },
  { value: "suspended", label: "Suspended" },
  { value: "withdrawn", label: "Withdrawn" },
];

const fullName = (row) => `${row.user?.first_name || ""} ${row.user?.last_name || ""}`.trim();

export default function StudentsPage() {
  const { user } = useAuth();
  const [classOptions, setClassOptions] = useState([]);
  const [streams, setStreams] = useState([]);
  const [view, setView] = useState("records");

  useEffect(() => {
    classesApi.list({ page_size: 200 }).then((data) => {
      const list = data.results || data;
      setClassOptions(list.map((c) => ({ value: c.id, label: c.name })));
    });
    streamsApi.list({ page_size: 500 }).then((data) => setStreams(data.results || data));
  }, []);

  const canManage = [ROLES.ADMIN, ROLES.REGISTRAR].includes(user?.role);

  // Streams belong to a class, so only offer the ones for the class currently chosen in the form.
  const streamOptionsFor = useMemo(
    () => (values) =>
      streams
        .filter((s) => String(s.school_class) === String(values.school_class))
        .map((s) => ({ value: s.id, label: s.name })),
    [streams]
  );

  const photoField = { name: "photo", label: "Photo", type: "file" };

  const createFields = useMemo(
    () => [
      photoField,
      { name: "username", label: "Login username", type: "text", required: true },
      { name: "first_name", label: "First name", type: "text", required: true },
      { name: "last_name", label: "Last name", type: "text", required: true },
      { name: "email", label: "Email", type: "email" },
      { name: "phone_number", label: "Phone number", type: "text" },
      { name: "password", label: "Temporary password", type: "password", required: true },
      { name: "gender", label: "Gender", type: "select", options: GENDER_OPTIONS },
      { name: "date_of_birth", label: "Date of birth", type: "date" },
      { name: "school_class", label: "Class", type: "select", options: classOptions, required: true },
      {
        name: "stream",
        label: "Stream",
        type: "select",
        options: streamOptionsFor,
        dependsOn: "school_class",
        hint: "Choose a class first, then its stream (optional).",
      },
      { name: "address", label: "Address", type: "text" },
      { name: "emergency_contact_name", label: "Emergency contact name", type: "text" },
      { name: "emergency_contact_phone", label: "Emergency contact phone", type: "text" },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [classOptions, streamOptionsFor]
  );

  const editFields = useMemo(
    () => [
      photoField,
      { name: "first_name", label: "First name", type: "text", required: true },
      { name: "last_name", label: "Last name", type: "text", required: true },
      { name: "email", label: "Email", type: "email" },
      { name: "phone_number", label: "Phone number", type: "text" },
      { name: "gender", label: "Gender", type: "select", options: GENDER_OPTIONS },
      { name: "date_of_birth", label: "Date of birth", type: "date" },
      {
        name: "school_class",
        label: "Class",
        type: "select",
        options: classOptions,
        readOnly: true,
        hint: "To change class, use “Transfer to new class” on the student's page so it is recorded in the history.",
      },
      { name: "stream", label: "Stream", type: "select", options: streamOptionsFor },
      { name: "address", label: "Address", type: "text" },
      { name: "status", label: "Status", type: "select", options: STATUS_OPTIONS },
      { name: "emergency_contact_name", label: "Emergency contact name", type: "text" },
      { name: "emergency_contact_phone", label: "Emergency contact phone", type: "text" },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [classOptions, streamOptionsFor]
  );

  const mapRowToForm = (row) => ({
    ...row,
    first_name: row.user?.first_name ?? "",
    last_name: row.user?.last_name ?? "",
    email: row.user?.email ?? "",
    phone_number: row.user?.phone_number ?? "",
    school_class: row.school_class ?? "",
    stream: row.stream ?? "",
  });

  const columns = [
    {
      key: "photo",
      label: "Photo",
      render: (row) => <Avatar src={row.photo} name={fullName(row)} size={36} />,
    },
    { key: "index_number", label: "Index No." },
    { key: "name", label: "Name", render: (row) => fullName(row) || "—" },
    { key: "gender", label: "Gender", render: (row) => (row.gender ? row.gender[0].toUpperCase() + row.gender.slice(1) : "—") },
    { key: "school_class_name", label: "Class" },
    { key: "stream_name", label: "Stream" },
    {
      key: "status",
      label: "Status",
      render: (row) => <Badge tone={STATUS_TONE[row.status] || "neutral"}>{row.status}</Badge>,
    },
  ];

  if (view === "report") return <StudentsReport onBack={() => setView("records")} />;

  return (
    <ResourceManager
      headerActions={
        user?.role === ROLES.STUDENT ? null : (
          <button className="btn btn-secondary" type="button" onClick={() => setView("report")}>
            📊 Reports
          </button>
        )
      }
      title="Students"
      subtitle={canManage ? "Register and manage student records." : "Student records you have access to."}
      api={studentsApi}
      columns={columns}
      createFields={canManage ? createFields : null}
      editFields={canManage ? editFields : null}
      mapRowToForm={mapRowToForm}
      canCreate={canManage}
      canEdit={canManage}
      canDelete={canManage}
      createLabel="Register student"
      rowActions={(row) => (
        <Link to={`/students/${row.id}`} className="btn btn-secondary btn-sm">
          View
        </Link>
      )}
      emptyTitle="No students found"
      emptyDescription={canManage ? "Register your first student to get started." : "No student records are linked to your account."}
    />
  );
}
