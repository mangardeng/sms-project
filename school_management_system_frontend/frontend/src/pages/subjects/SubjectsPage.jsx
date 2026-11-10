import { useEffect, useState } from "react";

import { academicYearsApi } from "../../api/academic";
import { classesApi } from "../../api/classes";
import { classSubjectsApi, subjectsApi } from "../../api/subjects";
import { teachersApi } from "../../api/teachers";
import Modal from "../../components/Modal";
import ResourceManager from "../../components/ResourceManager";
import SubjectsReport from "./SubjectsReport";
import { useAuth } from "../../context/AuthContext";
import { ROLES } from "../../utils/roles";

export default function SubjectsPage() {
  const { user } = useAuth();
  const canManage = user?.role === ROLES.ADMIN;
  const [assignFor, setAssignFor] = useState(null);
  const [view, setView] = useState("records");
  const [classOptions, setClassOptions] = useState([]);
  const [teacherOptions, setTeacherOptions] = useState([]);
  const [yearOptions, setYearOptions] = useState([]);

  useEffect(() => {
    if (canManage) {
      classesApi.list({ page_size: 200 }).then((data) => {
        const list = data.results || data;
        setClassOptions(list.map((c) => ({ value: c.id, label: c.name })));
      });
      teachersApi.list({ page_size: 200 }).then((data) => {
        const list = data.results || data;
        setTeacherOptions(list.map((t) => ({ value: t.id, label: `${t.staff_id} — ${t.user?.first_name || ""} ${t.user?.last_name || ""}`.trim() })));
      });
      academicYearsApi.list({ page_size: 50 }).then((data) => {
        const list = data.results || data;
        setYearOptions(list.map((y) => ({ value: y.id, label: `${y.name}${y.is_current ? " (current)" : ""}` })));
      });
    }
  }, [canManage]);

  const formFields = [
    { name: "code", label: "Subject code", type: "text", required: true, placeholder: "e.g. MATH101" },
    { name: "name", label: "Subject name", type: "text", required: true },
    { name: "is_compulsory", label: "Compulsory", type: "checkbox", checkboxLabel: "This subject is compulsory" },
    { name: "description", label: "Description", type: "textarea" },
  ];

  const columns = [
    { key: "code", label: "Code" },
    { key: "name", label: "Subject" },
    { key: "is_compulsory", label: "Compulsory", render: (row) => (row.is_compulsory ? "Yes" : "No") },
  ];

  if (view === "report") return <SubjectsReport onBack={() => setView("records")} />;

  return (
    <div>
      <ResourceManager
        headerActions={
          <button className="btn btn-secondary" type="button" onClick={() => setView("report")}>
            📊 Reports
          </button>
        }
        title="Subjects"
        subtitle={canManage ? "Manage subjects and assign them to classes/teachers." : "The school's subjects."}
        api={subjectsApi}
        columns={columns}
        formFields={canManage ? formFields : null}
        canCreate={canManage}
        canEdit={canManage}
        canDelete={canManage}
        createLabel="Add subject"
        rowActions={
          canManage
            ? (row) => (
                <button className="btn btn-secondary btn-sm" type="button" onClick={() => setAssignFor(row)}>
                  Assignments
                </button>
              )
            : undefined
        }
        emptyTitle="No subjects found"
      />

      {assignFor && (
        <Modal title={`Class assignments — ${assignFor.name}`} onClose={() => setAssignFor(null)} width={640}>
          <ResourceManager
            title=""
            api={{
              ...classSubjectsApi,
              create: (payload) => classSubjectsApi.create({ ...payload, subject: assignFor.id }),
            }}
            params={{ subject: assignFor.id }}
            columns={[
              { key: "school_class_name", label: "Class" },
              { key: "teacher_name", label: "Teacher", render: (row) => row.teacher_name || "Unassigned" },
            ]}
            formFields={[
              { name: "school_class", label: "Class", type: "select", options: classOptions, required: true },
              { name: "teacher", label: "Teacher", type: "select", options: teacherOptions },
              { name: "academic_year", label: "Academic year", type: "select", options: yearOptions, required: true },
            ]}
            canCreate
            canEdit
            canDelete
            canPrint={false}
            createLabel="Assign to a class"
            emptyTitle="Not assigned to any class yet"
          />
        </Modal>
      )}
    </div>
  );
}
