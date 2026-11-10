import EmptyState from "./EmptyState";
import LoadingSpinner from "./LoadingSpinner";

/**
 * columns: [{ key, label, render?: (row) => node }]
 */
export default function DataTable({
  columns,
  rows,
  loading,
  emptyTitle = "No records found",
  emptyDescription,
  rowKey = "id",
  pagination,
  onPageChange,
}) {
  if (loading) return <LoadingSpinner ink />;

  if (!rows || rows.length === 0) {
    return <EmptyState title={emptyTitle} description={emptyDescription} />;
  }

  return (
    <div className="surface">
      <div className="data-table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              {columns.map((col) => (
                <th key={col.key}>{col.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row[rowKey]}>
                {columns.map((col) => (
                  <td key={col.key}>{col.render ? col.render(row) : row[col.key] ?? "—"}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {pagination && pagination.total_pages > 1 && (
        <div className="pagination">
          <span>
            Page {pagination.current_page} of {pagination.total_pages} · {pagination.count} total
          </span>
          <button
            className="btn btn-secondary btn-sm"
            disabled={!pagination.previous}
            onClick={() => onPageChange(pagination.current_page - 1)}
            type="button"
          >
            Previous
          </button>
          <button
            className="btn btn-secondary btn-sm"
            disabled={!pagination.next}
            onClick={() => onPageChange(pagination.current_page + 1)}
            type="button"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
