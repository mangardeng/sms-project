import AlertBanner from "./AlertBanner";
import LoadingSpinner from "./LoadingSpinner";
import StatCard from "./StatCard";
import { useAuth } from "../context/AuthContext";
import { downloadCsv, printReport } from "../utils/print";

/**
 * Shared on-screen report with Print and CSV export.
 *
 * Props:
 *  - title, subtitle
 *  - onBack: shows a "← Back" button
 *  - filters: node (selects / date inputs) rendered above the report
 *  - filterSummary: plain-text description of the applied filters (printed on the page)
 *  - loading, error
 *  - stats: [{ label, value }]
 *  - sections: [{ heading, columns: [{ label, value: row => text, align? }], rows, footer? }]
 *  - filename: base name for the CSV download
 */
export default function ReportPanel({ title, subtitle, onBack, filters, filterSummary, loading, error, stats = [], sections = [], filename = "report" }) {
  const { user } = useAuth();
  const printedBy = `${user?.first_name || ""} ${user?.last_name || ""}`.trim() || user?.username;
  const hasData = sections.some((s) => s.rows?.length);

  return (
    <div>
      <div className="page-header">
        <div>
          {onBack && (
            <button className="btn-ghost" type="button" onClick={onBack} style={{ marginBottom: 8 }}>
              ← Back
            </button>
          )}
          <h1>{title}</h1>
          {subtitle && <div className="subtitle">{subtitle}</div>}
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            className="btn btn-secondary"
            type="button"
            disabled={loading || !hasData}
            onClick={() => downloadCsv(`${filename}-${new Date().toISOString().slice(0, 10)}`, sections)}
          >
            Download CSV
          </button>
          <button
            className="btn btn-primary"
            type="button"
            disabled={loading}
            onClick={() => printReport({ title, subtitle, filterSummary, stats, sections, printedBy })}
          >
            🖨 Print report
          </button>
        </div>
      </div>

      {filters && <div className="toolbar">{filters}</div>}
      <AlertBanner type="error">{error}</AlertBanner>

      {loading ? (
        <LoadingSpinner ink />
      ) : (
        <>
          {stats.length > 0 && (
            <div className="stat-grid">
              {stats.map((s) => (
                <StatCard key={s.label} label={s.label} value={s.value} />
              ))}
            </div>
          )}
          {sections.map((s, idx) => (
            <div className="surface surface-pad" style={{ marginBottom: 18 }} key={s.heading || idx}>
              {s.heading && <h3>{s.heading}</h3>}
              {s.rows?.length ? (
                <div className="data-table-wrap">
                  <table className="data-table">
                    <thead>
                      <tr>
                        {s.columns.map((c) => (
                          <th key={c.label} style={c.align === "right" ? { textAlign: "right" } : undefined}>
                            {c.label}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {s.rows.map((row, i) => (
                        <tr key={i}>
                          {s.columns.map((c) => {
                            const v = c.value(row);
                            return (
                              <td key={c.label} style={c.align === "right" ? { textAlign: "right" } : undefined}>
                                {v === null || v === undefined || v === "" ? "—" : v}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                    {s.footer && (
                      <tfoot>
                        <tr>
                          {s.columns.map((c, i) => (
                            <td key={c.label} style={{ fontWeight: 700, textAlign: c.align === "right" ? "right" : undefined }}>
                              {s.footer[i] ?? ""}
                            </td>
                          ))}
                        </tr>
                      </tfoot>
                    )}
                  </table>
                </div>
              ) : (
                <p className="hint" style={{ margin: 0 }}>No records for this selection.</p>
              )}
            </div>
          ))}
        </>
      )}
    </div>
  );
}
