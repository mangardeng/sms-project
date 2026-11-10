import { useEffect, useMemo, useState } from "react";

import { extractErrorMessage } from "../../api/client";
import { booksApi, borrowingApi } from "../../api/library";
import ReportPanel from "../../components/ReportPanel";
import { fetchAll } from "../../utils/fetchAll";
import { formatCurrency, formatDate, titleCase } from "../../utils/format";

const today = () => new Date().toISOString().slice(0, 10);

export default function LibraryReport({ onBack }) {
  const [books, setBooks] = useState([]);
  const [records, setRecords] = useState([]);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([fetchAll(booksApi), fetchAll(borrowingApi)])
      .then(([b, r]) => {
        setBooks(b);
        setRecords(r);
      })
      .catch((err) => setError(extractErrorMessage(err, "Could not load the library report.")))
      .finally(() => setLoading(false));
  }, []);

  // A loan that is still out past its due date counts as overdue even if the status field hasn't been refreshed.
  const effective = (r) => (r.status === "borrowed" && r.due_date && r.due_date < today() ? "overdue" : r.status);

  const shown = useMemo(() => records.filter((r) => !status || effective(r) === status), [records, status]);
  const overdue = records.filter((r) => effective(r) === "overdue");
  const fines = records.reduce((a, r) => a + Number(r.fine_amount || 0), 0);
  const copies = books.reduce((a, b) => a + (b.total_copies || 0), 0);
  const available = books.reduce((a, b) => a + (b.available_copies || 0), 0);

  const byCategory = useMemo(() => {
    const map = new Map();
    books.forEach((b) => {
      const k = b.category || "Uncategorised";
      const row = map.get(k) || { name: k, titles: 0, total: 0, available: 0 };
      row.titles += 1;
      row.total += b.total_copies || 0;
      row.available += b.available_copies || 0;
      map.set(k, row);
    });
    return [...map.values()].sort((a, b) => a.name.localeCompare(b.name));
  }, [books]);

  return (
    <ReportPanel
      title="Library Report"
      subtitle="Stock, loans, overdue items and fines"
      filename="library-report"
      onBack={onBack}
      loading={loading}
      error={error}
      filterSummary={`Loans shown: ${status ? titleCase(status) : "All statuses"}`}
      filters={
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All loans</option>
          {["borrowed", "returned", "overdue", "lost"].map((s) => (
            <option key={s} value={s}>
              {titleCase(s)}
            </option>
          ))}
        </select>
      }
      stats={[
        { label: "Titles", value: books.length },
        { label: "Copies in stock", value: `${available} / ${copies}` },
        { label: "On loan", value: records.filter((r) => ["borrowed", "overdue"].includes(effective(r))).length },
        { label: "Overdue", value: overdue.length },
        { label: "Fines charged", value: formatCurrency(fines) },
      ]}
      sections={[
        {
          heading: "Stock by category",
          columns: [
            { label: "Category", value: (r) => r.name },
            { label: "Titles", value: (r) => r.titles, align: "right" },
            { label: "Copies", value: (r) => r.total, align: "right" },
            { label: "Available", value: (r) => r.available, align: "right" },
            { label: "On loan", value: (r) => r.total - r.available, align: "right" },
          ],
          rows: byCategory,
        },
        {
          heading: "Book catalogue",
          columns: [
            { label: "Title", value: (b) => b.title },
            { label: "Author", value: (b) => b.author },
            { label: "Category", value: (b) => b.category },
            { label: "ISBN", value: (b) => b.isbn },
            { label: "Available", value: (b) => b.available_copies, align: "right" },
            { label: "Total", value: (b) => b.total_copies, align: "right" },
          ],
          rows: books,
        },
        {
          heading: "Borrowing records",
          columns: [
            { label: "Book", value: (r) => r.book_title },
            { label: "Borrower", value: (r) => r.borrower_name },
            { label: "Issued", value: (r) => formatDate(r.issued_date) },
            { label: "Due", value: (r) => formatDate(r.due_date) },
            { label: "Returned", value: (r) => (r.returned_date ? formatDate(r.returned_date) : "") },
            { label: "Status", value: (r) => titleCase(effective(r)) },
            { label: "Fine", value: (r) => (Number(r.fine_amount) > 0 ? formatCurrency(r.fine_amount) : ""), align: "right" },
          ],
          rows: shown,
        },
      ]}
    />
  );
}
