import { useEffect, useState } from "react";

import { classesApi, streamsApi } from "../../api/classes";
import { teachersApi } from "../../api/teachers";
import Modal from "../../components/Modal";
import ResourceManager from "../../components/ResourceManager";
import ClassesReport from "./ClassesReport";
import { useAuth } from "../../context/AuthContext";
import { ROLES } from "../../utils/roles";

export default function ClassesPage() {
  const { user } = useAuth();
  const canManage = user?.role === ROLES.ADMIN;
  const [teacherOptions, setTeacherOptions] = useState([]);
  const [streamsFor, setStreamsFor] = useState(null); // school class row, or null
  const [view, setView] = useState("records");

  useEffect(() => {
    if (canManage) {
      teachersApi.list({ page_size: 200 }).then((data) => {
        const list = data.results || data;
        setTeacherOptions(list.map((t) => ({ value: t.id, label: `${t.staff_id} — ${t.user?.first_name || ""} ${t.user?.last_name || ""}`.trim() })));
      });
    }
  }, [canManage]);

  const formFields = [
    { name: "name", label: "Class name", type: "text", required: true, placeholder: "e.g. Grade 9" },
    { name: "level", label: "Sort level", type: "number", required: true, hint: "Numeric order used for sorting, e.g. 9" },
    { name: "class_teacher", label: "Class teacher", type: "select", options: teacherOptions },
    { name: "is_active", label: "Active", type: "checkbox", checkboxLabel: "This class is currently in use" },
  ];

  const columns = [
    { key: "name", label: "Class" },
    { key: "level", label: "Level" },
    { key: "class_teacher_name", label: "Class teacher", render: (row) => row.class_teacher_name || "—" },
    { key: "student_count", label: "Students" },
  ];

  if (view === "report") return <ClassesReport onBack={() => setView("records")} />;

  return (
    <div>
      <ResourceManager
        headerActions={
          <button className="btn btn-secondary" type="button" onClick={() => setView("report")}>
            📊 Reports
          </button>
        }
        title="Classes"
        subtitle={canManage ? "Manage the school's classes and streams." : "The school's classes."}
        api={classesApi}
        columns={columns}
        formFields={canManage ? formFields : null}
        canCreate={canManage}
        canEdit={canManage}
        canDelete={canManage}
        createLabel="Add class"
        rowActions={(row) => (
          <button className="btn btn-secondary btn-sm" type="button" onClick={() => setStreamsFor(row)}>
            Streams
          </button>
        )}
        emptyTitle="No classes found"
      />

      {streamsFor && (
        <Modal title={`Streams — ${streamsFor.name}`} onClose={() => setStreamsFor(null)} width={640}>
          <ResourceManager
            title=""
            api={{
              ...streamsApi,
              create: (payload) => streamsApi.create({ ...payload, school_class: streamsFor.id }),
            }}
            params={{ school_class: streamsFor.id }}
            columns={[
              { key: "name", label: "Stream" },
              { key: "capacity", label: "Capacity" },
              { key: "student_count", label: "Students" },
            ]}
            formFields={
              canManage
                ? [
                    { name: "name", label: "Stream name", type: "text", required: true, placeholder: "e.g. A" },
                    { name: "capacity", label: "Capacity", type: "number" },
                  ]
                : null
            }
            canCreate={canManage}
            canEdit={canManage}
            canDelete={canManage}
            canPrint={false}
            createLabel="Add stream"
            emptyTitle="No streams for this class yet"
          />
        </Modal>
      )}
    </div>
  );
}
