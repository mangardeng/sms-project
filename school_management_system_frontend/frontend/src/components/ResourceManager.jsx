import { useCallback, useEffect, useState } from "react";

import { extractErrorMessage } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { ROLES } from "../utils/roles";
import { fetchAll } from "../utils/fetchAll";
import { printReport } from "../utils/print";
import { renderToStaticMarkup } from "react-dom/server";
import AlertBanner from "./AlertBanner";
import DataTable from "./DataTable";
import Modal from "./Modal";
import ResourceForm from "./ResourceForm";

/**
 * A configurable list+create+edit+delete page for a single resource.
 *
 * Props:
 *  - title, subtitle
 *  - api: { list, create, update, remove }
 *  - columns: DataTable column config
 *  - formFields: fields for the create/edit form (omit to disable create/edit)
 *  - canCreate / canEdit / canDelete: booleans (default true if formFields/api.remove present)
 *  - extraFilters: node rendered in the toolbar (e.g. a <select> that sets `params`)
 *  - params: extra query params merged into every list() call
 *  - rowActions: (row) => node — extra buttons per row, alongside Edit/Delete
 *  - toResultsArray: (data) => rows, for endpoints that don't return the standard paginated shape
 *  - mapRowToForm: (row) => initialValues for the edit form
 *  - headerActions: node rendered next to the create button (e.g. a "Reports" button)
 *  - canPrint (default true): shows a "Print list" button that prints every record matching the
 *    current search, not just the visible page. printTitle sets the heading on the printout.
 *  - onCreated / onUpdated / onDeleted: optional callbacks
 */
export default function ResourceManager({
  title,
  subtitle,
  api,
  columns,
  formFields,
  createFields,
  editFields,
  canCreate = true,
  canEdit = true,
  canDelete = true,
  extraFilters,
  params = {},
  rowActions,
  toResultsArray,
  mapRowToForm,
  emptyTitle,
  emptyDescription,
  createLabel = "Add new",
  headerActions,
  canPrint = true,
  printTitle,
}) {
  const { user } = useAuth();
  const [printing, setPrinting] = useState(false);
  const [rows, setRows] = useState([]);
  const [pagination, setPagination] = useState(null);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [modalMode, setModalMode] = useState(null); // "create" | "edit" | null
  const [activeRow, setActiveRow] = useState(null);

  const load = useCallback(async () => {
    // Drop whatever the previous resource left behind so rows from another list
    // (e.g. fee structures) are never drawn under this list's columns.
    setLoading(true);
    setError("");
    try {
      const data = await api.list({ page, search: search || undefined, ...params });
      if (toResultsArray) {
        setRows(toResultsArray(data));
        setPagination(null);
      } else if (Array.isArray(data)) {
        setRows(data);
        setPagination(null);
      } else {
        setRows(data.results || []);
        setPagination(data);
      }
    } catch (err) {
      setError(extractErrorMessage(err, "Could not load this list."));
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api.list, page, search, JSON.stringify(params)]);

  useEffect(() => {
    setRows([]);
    setPagination(null);
    load();
  }, [load]);

  async function handlePrint() {
    setPrinting(true);
    setError("");
    try {
      let all;
      if (toResultsArray) all = toResultsArray(await api.list({ search: search || undefined, ...params }));
      else all = await fetchAll(api, { search: search || undefined, ...params });
      const printable = columns.filter((c) => c.key !== "photo" && c.key !== "__actions" && c.label);
      const cols = printable.map((c) => ({
        label: c.label,
        value: (row) => {
          const raw = c.render ? c.render(row) : row[c.key];
          if (raw === null || raw === undefined || raw === "") return "—";
          if (typeof raw === "string" || typeof raw === "number") return raw;
          // Render badges / JSX to plain text.
          return renderToStaticMarkup(raw).replace(/<[^>]+>/g, "").replace(/&amp;/g, "&").replace(/&#x27;/g, "'").replace(/&quot;/g, '"') || "—";
        },
      }));
      printReport({
        title: printTitle || title || "Records",
        subtitle: `${all.length} record${all.length === 1 ? "" : "s"}${search ? ` matching “${search}”` : ""}`,
        sections: [{ columns: cols, rows: all }],
        printedBy: `${user?.first_name || ""} ${user?.last_name || ""}`.trim() || user?.username,
      });
    } catch (err) {
      setError(extractErrorMessage(err, "Could not prepare the printout."));
    } finally {
      setPrinting(false);
    }
  }

  async function handleCreate(values) {
    await api.create(values);
    setModalMode(null);
    await load();
  }

  async function handleUpdate(values) {
    await api.update(activeRow.id, values);
    setModalMode(null);
    setActiveRow(null);
    await load();
  }

  async function handleDelete(row) {
    if (!window.confirm("Delete this record? This cannot be undone.")) return;
    try {
      await api.remove(row.id);
      await load();
    } catch (err) {
      setError(extractErrorMessage(err, "Could not delete this record."));
    }
  }

  const resolvedCreateFields = createFields || formFields;
  const resolvedEditFields = editFields || formFields;

  const allColumns = [
    ...columns,
    (canEdit && resolvedEditFields) || canDelete || rowActions
      ? {
          key: "__actions",
          label: "",
          render: (row) => (
            <div className="table-actions">
              {rowActions?.(row)}
              {canEdit && resolvedEditFields && (
                <button
                  className="btn btn-secondary btn-sm"
                  type="button"
                  onClick={() => {
                    setActiveRow(row);
                    setModalMode("edit");
                  }}
                >
                  Edit
                </button>
              )}
              {canDelete && (
                <button className="btn btn-danger btn-sm" type="button" onClick={() => handleDelete(row)}>
                  Delete
                </button>
              )}
            </div>
          ),
        }
      : null,
  ].filter(Boolean);

  return (
    <div>
      <div className="page-header">
        <div>
          {title && <h1>{title}</h1>}
          {subtitle && <div className="subtitle">{subtitle}</div>}
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {headerActions}
          {canPrint && user?.role !== ROLES.STUDENT && (
            <button className="btn btn-secondary" type="button" onClick={handlePrint} disabled={printing || loading}>
              {printing ? "Preparing…" : "🖨 Print list"}
            </button>
          )}
          {canCreate && resolvedCreateFields && (
            <button className="btn btn-primary" type="button" onClick={() => setModalMode("create")}>
              + {createLabel}
            </button>
          )}
        </div>
      </div>

      <div className="toolbar">
        <input
          type="search"
          placeholder="Search…"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
        />
        {extraFilters}
      </div>

      <AlertBanner type="error">{error}</AlertBanner>

      <DataTable
        columns={allColumns}
        rows={rows}
        loading={loading}
        emptyTitle={emptyTitle}
        emptyDescription={emptyDescription}
        pagination={pagination}
        onPageChange={setPage}
      />

      {modalMode === "create" && resolvedCreateFields && (
        <Modal title={createLabel} onClose={() => setModalMode(null)} width={640}>
          <ResourceForm fields={resolvedCreateFields} onSubmit={handleCreate} onCancel={() => setModalMode(null)} mode="create" />
        </Modal>
      )}

      {modalMode === "edit" && resolvedEditFields && activeRow && (
        <Modal title="Edit record" onClose={() => setModalMode(null)} width={640}>
          <ResourceForm
            fields={resolvedEditFields}
            initialValues={mapRowToForm ? mapRowToForm(activeRow) : activeRow}
            onSubmit={handleUpdate}
            onCancel={() => {
              setModalMode(null);
              setActiveRow(null);
            }}
            submitLabel="Save changes"
            mode="edit"
          />
        </Modal>
      )}
    </div>
  );
}
