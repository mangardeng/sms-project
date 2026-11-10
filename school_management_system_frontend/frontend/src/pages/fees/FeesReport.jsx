import { useEffect, useMemo, useState } from "react";

import { termsApi } from "../../api/academic";
import { classesApi } from "../../api/classes";
import { extractErrorMessage } from "../../api/client";
import { feeStructuresApi, paymentsApi } from "../../api/fees";
import { studentsApi } from "../../api/students";
import ReportPanel from "../../components/ReportPanel";
import { fetchAll, fetchAllSafe } from "../../utils/fetchAll";
import { formatCurrency, formatDate, fullName, titleCase } from "../../utils/format";

const sum = (list, fn) => list.reduce((a, x) => a + Number(fn(x) || 0), 0);

export default function FeesReport({ onBack }) {
  const [structures, setStructures] = useState([]);
  const [payments, setPayments] = useState([]);
  const [students, setStudents] = useState([]);
  const [classes, setClasses] = useState([]);
  const [terms, setTerms] = useState([]);
  const [classId, setClassId] = useState("");
  const [termId, setTermId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([fetchAll(feeStructuresApi), fetchAll(paymentsApi), fetchAll(studentsApi, { status: "active" }), fetchAllSafe(classesApi), fetchAllSafe(termsApi)])
      .then(([f, p, s, c, t]) => {
        setStructures(f);
        setPayments(p);
        setStudents(s);
        setClasses(c);
        setTerms(t);
      })
      .catch((err) => setError(extractErrorMessage(err, "Could not load the fees report.")))
      .finally(() => setLoading(false));
  }, []);

  const data = useMemo(() => {
    const structById = new Map(structures.map((f) => [f.id, f]));
    const inTerm = (f) => !termId || String(f.term) === termId;
    const classStudents = students.filter((s) => !classId || String(s.school_class) === classId);

    // One row per student: due = fee structures for the student's class, paid = their payments.
    const perStudent = classStudents.map((s) => {
      const due = sum(structures.filter((f) => f.school_class === s.school_class && inTerm(f)), (f) => f.amount);
      const paid = sum(payments.filter((p) => p.student === s.id && inTerm(structById.get(p.fee_structure) || {})), (p) => p.amount_paid);
      return { s, due, paid, balance: due - paid };
    });

    const byClass = new Map();
    perStudent.forEach((r) => {
      const k = r.s.school_class_name || "No class";
      const row = byClass.get(k) || { name: k, students: 0, due: 0, paid: 0 };
      row.students += 1;
      row.due += r.due;
      row.paid += r.paid;
      byClass.set(k, row);
    });

    const ids = new Set(classStudents.map((s) => s.id));
    const txns = payments.filter((p) => ids.has(p.student) && inTerm(structById.get(p.fee_structure) || {}));
    const byMethod = new Map();
    txns.forEach((p) => {
      const row = byMethod.get(p.method) || { method: p.method, count: 0, total: 0 };
      row.count += 1;
      row.total += Number(p.amount_paid);
      byMethod.set(p.method, row);
    });

    return {
      perStudent,
      byClass: [...byClass.values()].sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true })),
      txns,
      byMethod: [...byMethod.values()],
      due: sum(perStudent, (r) => r.due),
      paid: sum(perStudent, (r) => r.paid),
      defaulters: perStudent.filter((r) => r.balance > 0).sort((a, b) => b.balance - a.balance),
    };
  }, [structures, payments, students, classId, termId]);

  const money = formatCurrency;
  const termLabel = (t) => t.display_name || `${t.name} — ${t.academic_year_name}`;
  const filterSummary = `Class: ${classes.find((c) => String(c.id) === classId)?.name || "All classes"} · Term: ${terms.find((t) => String(t.id) === termId) ? termLabel(terms.find((t) => String(t.id) === termId)) : "All terms"}`;

  return (
    <ReportPanel
      title="Fees Report"
      subtitle="Expected fees, collections and outstanding balances (active students)"
      filename="fees-report"
      onBack={onBack}
      loading={loading}
      error={error}
      filterSummary={filterSummary}
      filters={
        <>
          <select value={classId} onChange={(e) => setClassId(e.target.value)}>
            <option value="">All classes</option>
            {classes.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
          <select value={termId} onChange={(e) => setTermId(e.target.value)}>
            <option value="">All terms</option>
            {terms.map((t) => (
              <option key={t.id} value={t.id}>
                {termLabel(t)}
              </option>
            ))}
          </select>
        </>
      }
      stats={[
        { label: "Expected", value: money(data.due) },
        { label: "Collected", value: money(data.paid) },
        { label: "Outstanding", value: money(Math.max(0, data.due - data.paid)) },
        { label: "Collection rate", value: data.due ? `${((data.paid / data.due) * 100).toFixed(1)}%` : "—" },
        { label: "Students owing", value: data.defaulters.length },
      ]}
      sections={[
        {
          heading: "Collection by class",
          columns: [
            { label: "Class", value: (r) => r.name },
            { label: "Students", value: (r) => r.students, align: "right" },
            { label: "Expected", value: (r) => money(r.due), align: "right" },
            { label: "Collected", value: (r) => money(r.paid), align: "right" },
            { label: "Balance", value: (r) => money(r.due - r.paid), align: "right" },
            { label: "Rate", value: (r) => (r.due ? `${((r.paid / r.due) * 100).toFixed(1)}%` : "—"), align: "right" },
          ],
          rows: data.byClass,
          footer: data.byClass.length ? ["Total", sum(data.byClass, (r) => r.students), money(data.due), money(data.paid), money(data.due - data.paid), ""] : undefined,
        },
        {
          heading: "Collection by payment method",
          columns: [
            { label: "Method", value: (r) => titleCase(r.method) },
            { label: "Payments", value: (r) => r.count, align: "right" },
            { label: "Amount", value: (r) => money(r.total), align: "right" },
          ],
          rows: data.byMethod,
        },
        {
          heading: "Outstanding balances",
          columns: [
            { label: "Index No.", value: (r) => r.s.index_number },
            { label: "Student", value: (r) => fullName(r.s) },
            { label: "Class", value: (r) => r.s.school_class_name },
            { label: "Fees due", value: (r) => money(r.due), align: "right" },
            { label: "Paid", value: (r) => money(r.paid), align: "right" },
            { label: "Balance", value: (r) => money(r.balance), align: "right" },
          ],
          rows: data.defaulters,
        },
        {
          heading: "Payment transactions",
          columns: [
            { label: "Receipt", value: (p) => p.receipt_number },
            { label: "Date", value: (p) => formatDate(p.payment_date) },
            { label: "Student", value: (p) => `${p.student_name} (${p.student_index_number})` },
            { label: "Fee", value: (p) => p.fee_structure_name },
            { label: "Method", value: (p) => titleCase(p.method) },
            { label: "Amount", value: (p) => money(p.amount_paid), align: "right" },
          ],
          rows: data.txns,
          footer: data.txns.length ? ["", "", "", "", "Total", money(sum(data.txns, (p) => p.amount_paid))] : undefined,
        },
      ]}
    />
  );
}
