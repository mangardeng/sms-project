import { useEffect, useState } from "react";

import { extractErrorMessage } from "../../api/client";
import { booksApi, borrowingApi } from "../../api/library";
import { studentsApi } from "../../api/students";
import { teachersApi } from "../../api/teachers";
import AlertBanner from "../../components/AlertBanner";
import Badge from "../../components/Badge";
import ResourceManager from "../../components/ResourceManager";
import LibraryReport from "./LibraryReport";
import { useAuth } from "../../context/AuthContext";
import { formatCurrency, formatDate, titleCase } from "../../utils/format";
import { ROLES } from "../../utils/roles";

const STATUS_TONE = { borrowed: "info", returned: "accent", overdue: "alert", lost: "alert" };

export default function LibraryPage() {
  const { user } = useAuth();
  const canManage = [ROLES.ADMIN, ROLES.LIBRARIAN].includes(user?.role);
  const [tab, setTab] = useState("books");
  const [studentOptions, setStudentOptions] = useState([]);
  const [teacherOptions, setTeacherOptions] = useState([]);
  const [bookOptions, setBookOptions] = useState([]);
  const [returnError, setReturnError] = useState("");

  // Refresh the book list whenever the Borrowing tab is opened so newly added books appear in the dropdown.
  useEffect(() => {
    if (canManage && tab === "borrowing") {
      booksApi.list({ page_size: 500 }).then((d) =>
        setBookOptions(
          (d.results || d).map((b) => ({ value: b.id, label: `${b.title}${b.author ? ` — ${b.author}` : ""} (${b.available_copies} available)` }))
        )
      );
    }
  }, [canManage, tab]);

  useEffect(() => {
    if (canManage) {
      studentsApi.list({ page_size: 300 }).then((d) =>
        setStudentOptions((d.results || d).map((s) => ({ value: s.id, label: `${s.index_number} — ${s.user?.first_name || ""} ${s.user?.last_name || ""}`.trim() })))
      );
      teachersApi.list({ page_size: 300 }).then((d) =>
        setTeacherOptions((d.results || d).map((t) => ({ value: t.id, label: `${t.staff_id} — ${t.user?.first_name || ""} ${t.user?.last_name || ""}`.trim() })))
      );
    }
  }, [canManage]);

  const bookFields = [
    { name: "title", label: "Title", type: "text", required: true },
    { name: "author", label: "Author", type: "text" },
    { name: "isbn", label: "ISBN", type: "text", emptyAsNull: true },
    { name: "category", label: "Category", type: "text" },
    { name: "total_copies", label: "Total copies", type: "number", required: true },
    { name: "available_copies", label: "Available copies", type: "number", required: true },
  ];

  const borrowFields = [
    { name: "book", label: "Book", type: "select", options: bookOptions, required: true },
        { name: "student", label: "Borrowing student", type: "select", options: studentOptions, dependsOn: "teacher", hint: "Choose a student OR a teacher (choosing one clears the other)." },
    { name: "teacher", label: "Borrowing teacher", type: "select", options: teacherOptions, dependsOn: "student" },
    { name: "due_date", label: "Due date", type: "date", hint: "Leave blank for the default 14-day loan." },
  ];

  return (
    <div>
      <div className="page-header">
        <h1>Library</h1>
      </div>

      <div className="toolbar">
        <button className={`btn btn-sm ${tab === "books" ? "btn-primary" : "btn-secondary"}`} type="button" onClick={() => setTab("books")}>
          Book catalog
        </button>
        <button className={`btn btn-sm ${tab === "borrowing" ? "btn-primary" : "btn-secondary"}`} type="button" onClick={() => setTab("borrowing")}>
          Borrowing records
        </button>
        {user?.role !== ROLES.STUDENT && (
          <button className={`btn btn-sm ${tab === "report" ? "btn-primary" : "btn-secondary"}`} type="button" onClick={() => setTab("report")}>
            📊 Report
          </button>
        )}
      </div>

      <AlertBanner type="error">{returnError}</AlertBanner>

      {tab === "report" ? (
        <LibraryReport />
      ) : tab === "books" ? (
        <ResourceManager
          key="books"
          printTitle="Library Book Catalogue"
          title=""
          api={booksApi}
          columns={[
            { key: "title", label: "Title" },
            { key: "author", label: "Author" },
            { key: "category", label: "Category" },
            { key: "available_copies", label: "Available" },
            { key: "total_copies", label: "Total" },
          ]}
          formFields={canManage ? bookFields : null}
          canCreate={canManage}
          canEdit={canManage}
          canDelete={canManage}
          createLabel="Add book"
          emptyTitle="No books in the catalog yet"
        />
      ) : (
        <ResourceManager
          key="borrowing"
          printTitle="Library Borrowing Records"
          title=""
          api={borrowingApi}
          columns={[
            { key: "book_title", label: "Book" },
            { key: "borrower_name", label: "Borrower" },
            { key: "issued_date", label: "Issued", render: (row) => formatDate(row.issued_date) },
            { key: "due_date", label: "Due", render: (row) => formatDate(row.due_date) },
            { key: "returned_date", label: "Returned", render: (row) => formatDate(row.returned_date) },
            { key: "status", label: "Status", render: (row) => <Badge tone={STATUS_TONE[row.status] || "neutral"}>{titleCase(row.status)}</Badge> },
            { key: "fine_amount", label: "Fine", render: (row) => (Number(row.fine_amount) > 0 ? formatCurrency(row.fine_amount) : "—") },
          ]}
          formFields={canManage ? borrowFields : null}
          canCreate={canManage}
          canEdit={false}
          canDelete={false}
          createLabel="Issue book"
          rowActions={
            canManage
              ? (row) =>
                  row.status === "borrowed" ? (
                    <button
                      className="btn btn-secondary btn-sm"
                      type="button"
                      onClick={async () => {
                        setReturnError("");
                        try {
                          await borrowingApi.markReturned(row.id);
                          window.location.reload();
                        } catch (err) {
                          setReturnError(extractErrorMessage(err));
                        }
                      }}
                    >
                      Mark returned
                    </button>
                  ) : null
              : undefined
          }
          emptyTitle="No borrowing records yet"
        />
      )}
    </div>
  );
}
