import { useEffect, useState } from "react";

import { academicYearsApi, termsApi } from "../../api/academic";
import { extractErrorMessage } from "../../api/client";
import {
  carryForwardApi,
  expensesApi,
  financeApi,
  otherIncomeApi,
  salariesApi,
  sponsorsApi,
  sponsorshipsApi,
} from "../../api/fees";
import { studentsApi } from "../../api/students";
import AlertBanner from "../../components/AlertBanner";
import Badge from "../../components/Badge";
import LoadingSpinner from "../../components/LoadingSpinner";
import ResourceManager from "../../components/ResourceManager";
import StatCard from "../../components/StatCard";
import { useAuth } from "../../context/AuthContext";
import { formatCurrency, formatDate, titleCase } from "../../utils/format";
import { printReport } from "../../utils/print";
import { ROLES } from "../../utils/roles";
import { METHOD_OPTIONS } from "./PaymentTools";

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const monthOptions = MONTHS.map((m, i) => ({ value: i + 1, label: m }));
const today = () => new Date().toISOString().slice(0, 10);
const printedByOf = (user) => `${user?.first_name || ""} ${user?.last_name || ""}`.trim() || user?.username;

/** Dropdown options shared by the finance forms. */
function useFinanceOptions() {
  const [options, setOptions] = useState({ students: [], terms: [], years: [] });
  useEffect(() => {
    Promise.all([studentsApi.list({ page_size: 300 }), termsApi.list({ page_size: 50 }), academicYearsApi.list({ page_size: 20 })]).then(
      ([students, terms, years]) =>
        setOptions({
          students: (students.results || students).map((s) => ({
            value: s.id,
            label: `${s.index_number} — ${s.user?.first_name || ""} ${s.user?.last_name || ""}`.trim(),
          })),
          terms: (terms.results || terms).map((t) => ({ value: t.id, label: t.display_name || `${t.name} — ${t.academic_year_name}`, current: t.is_current })),
          years: (years.results || years).map((y) => ({ value: y.id, label: y.name })),
        })
    );
  }, []);
  return options;
}

function useReadOnly() {
  const { user } = useAuth();
  return user?.role === ROLES.HEAD_TEACHER; // head teacher can look but not change finance records
}

/* ------------------------------------------------------------------ carry forward */
export function CarryForwardPanel() {
  const readOnly = useReadOnly();
  const { terms, students } = useFinanceOptions();
  const [fromTerm, setFromTerm] = useState("");
  const [toTerm, setToTerm] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [version, setVersion] = useState(0);

  async function generate() {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const r = await carryForwardApi.generate({ from_term: Number(fromTerm), to_term: Number(toTerm) });
      setNotice(
        `Carried forward ${formatCurrency(r.total)} for ${r.students} student(s)` +
          (r.cleared ? `; ${r.cleared} student(s) have since paid up and were cleared.` : ".")
      );
      setVersion((v) => v + 1);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  const createFields = [
    { name: "student", label: "Student", type: "select", options: students, required: true },
    { name: "from_term", label: "Owed from term", type: "select", options: terms, required: true },
    { name: "to_term", label: "Carried into term", type: "select", options: terms, required: true },
    { name: "amount", label: "Amount", type: "number", step: "0.01", required: true },
    { name: "notes", label: "Notes", type: "text" },
  ];
  const editFields = [
    { name: "amount", label: "Amount (lower it to waive part of the debt)", type: "number", step: "0.01", required: true },
    { name: "notes", label: "Notes", type: "text" },
  ];

  return (
    <div>
      {!readOnly && (
        <div className="surface surface-pad" style={{ marginBottom: 16 }}>
          <h3 style={{ marginTop: 0 }}>Carry unpaid fees forward</h3>
          <p className="hint" style={{ marginTop: 0 }}>
            At the start of a new term, choose the term that just ended and the new term. Every student who has not fully paid has the unpaid
            balance added to the new term's account. Running it again simply refreshes the amounts.
          </p>
          <div className="toolbar" style={{ marginBottom: 0 }}>
            <select value={fromTerm} onChange={(e) => setFromTerm(e.target.value)}>
              <option value="">Carry FROM term…</option>
              {terms.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
            <select value={toTerm} onChange={(e) => setToTerm(e.target.value)}>
              <option value="">Carry INTO term…</option>
              {terms.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
            <button className="btn btn-primary" type="button" onClick={generate} disabled={busy || !fromTerm || !toTerm}>
              {busy ? "Working…" : "Generate carry-forward"}
            </button>
          </div>
          <AlertBanner type="error">{error}</AlertBanner>
          <AlertBanner type="success">{notice}</AlertBanner>
        </div>
      )}
      <ResourceManager
        key="carry"
        title=""
        api={carryForwardApi}
        params={{ _v: version }}
        printTitle="Fees Carried Forward"
        columns={[
          { key: "student_name", label: "Student", render: (r) => `${r.student_name} (${r.student_index_number})` },
          { key: "from_term_name", label: "Owed from" },
          { key: "to_term_name", label: "Carried into" },
          { key: "amount", label: "Amount", render: (r) => formatCurrency(r.amount) },
          { key: "notes", label: "Notes" },
        ]}
        createFields={createFields}
        editFields={editFields}
        canCreate={!readOnly}
        canEdit={!readOnly}
        canDelete={!readOnly}
        createLabel="Add carried-forward balance"
        emptyTitle="Nothing carried forward yet"
        emptyDescription="Use “Generate carry-forward” when a new term starts."
      />
    </div>
  );
}

/* ------------------------------------------------------------------ sponsorship */
export function SponsorshipPanel() {
  const readOnly = useReadOnly();
  const { user } = useAuth();
  const { terms, students, years } = useFinanceOptions();
  const [sub, setSub] = useState("students");
  const [sponsorOptions, setSponsorOptions] = useState([]);
  const [reportTerm, setReportTerm] = useState("");
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    sponsorsApi.list({ page_size: 200 }).then((d) => setSponsorOptions((d.results || d).map((s) => ({ value: s.id, label: s.name }))));
  }, [sub, version]);

  useEffect(() => {
    if (sub !== "report") return;
    const current = terms.find((t) => t.current) || terms[0];
    if (!reportTerm && current) setReportTerm(String(current.value));
  }, [sub, terms, reportTerm]);

  useEffect(() => {
    if (sub !== "report" || !reportTerm) return;
    setLoading(true);
    setError("");
    sponsorshipsApi
      .report(reportTerm)
      .then(setReport)
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [sub, reportTerm]);

  const sponsorFields = [
    { name: "name", label: "Sponsor name", type: "text", required: true },
    {
      name: "sponsor_type",
      label: "Type",
      type: "select",
      required: true,
      options: [
        { value: "individual", label: "Individual" },
        { value: "organization", label: "Organization / NGO" },
        { value: "church", label: "Church / Faith group" },
        { value: "government", label: "Government / Bursary" },
        { value: "company", label: "Company" },
        { value: "other", label: "Other" },
      ],
    },
    { name: "contact_person", label: "Contact person", type: "text" },
    { name: "phone", label: "Phone", type: "text" },
    { name: "email", label: "Email", type: "email" },
    { name: "notes", label: "Notes", type: "text" },
    { name: "is_active", label: "Active", type: "checkbox", checkboxLabel: "This sponsor is currently active" },
  ];

  const sponsorshipFields = [
    { name: "student", label: "Student", type: "select", options: students, required: true },
    { name: "sponsor", label: "Sponsor", type: "select", options: sponsorOptions, required: true },
    {
      name: "coverage_type",
      label: "What the sponsor pays",
      type: "select",
      required: true,
      options: [
        { value: "full", label: "Full fees" },
        { value: "percentage", label: "A percentage of the fees" },
        { value: "fixed", label: "A fixed amount per term" },
      ],
    },
    { name: "value", label: "Percentage or amount", type: "number", step: "0.01", hint: "Percentage (e.g. 60) or amount per term. Leave blank for full fees." },
    { name: "academic_year", label: "Academic year", type: "select", options: years, hint: "Leave blank for every year." },
    { name: "term", label: "Term", type: "select", options: terms, hint: "Leave blank for every term." },
    { name: "notes", label: "Notes", type: "text" },
    { name: "is_active", label: "Active", type: "checkbox", checkboxLabel: "This sponsorship is active" },
  ];

  const tabBtn = (key, label) => (
    <button className={`btn btn-sm ${sub === key ? "btn-primary" : "btn-secondary"}`} type="button" onClick={() => setSub(key)}>
      {label}
    </button>
  );

  function printReportOut() {
    printReport({
      title: "Sponsorship Report",
      subtitle: report.term,
      sections: report.sponsors.map((s) => ({
        heading: `${s.sponsor_name} — expected ${formatCurrency(s.expected)}, paid ${formatCurrency(s.paid)}, outstanding ${formatCurrency(s.outstanding)}`,
        columns: [
          { label: "Index No.", value: (r) => r.student_index_number },
          { label: "Student", value: (r) => r.student_name },
          { label: "Class", value: (r) => r.school_class_name },
          { label: "Covers", value: (r) => r.coverage },
          { label: "Expected", value: (r) => formatCurrency(r.expected), align: "right" },
          { label: "Paid", value: (r) => formatCurrency(r.paid), align: "right" },
          { label: "Outstanding", value: (r) => formatCurrency(r.outstanding), align: "right" },
        ],
        rows: s.students,
      })),
      printedBy: printedByOf(user),
    });
  }

  return (
    <div>
      <div className="toolbar">
        {tabBtn("students", "Students under sponsorship")}
        {tabBtn("sponsors", "Sponsors")}
        {tabBtn("report", "Sponsor report")}
      </div>

      {sub === "students" && (
        <ResourceManager
          key="sponsorships"
          title=""
          api={sponsorshipsApi}
          params={{ _v: version }}
          printTitle="Students Under Sponsorship"
          columns={[
            { key: "student_name", label: "Student", render: (r) => `${r.student_name} (${r.student_index_number})` },
            { key: "sponsor_name", label: "Sponsor" },
            {
              key: "coverage_type",
              label: "Covers",
              render: (r) =>
                r.coverage_type === "full" ? "Full fees" : r.coverage_type === "percentage" ? `${Number(r.value)}% of fees` : `${formatCurrency(r.value)} per term`,
            },
            { key: "term_name", label: "Term" },
            { key: "is_active", label: "Status", render: (r) => <Badge tone={r.is_active ? "accent" : "neutral"}>{r.is_active ? "Active" : "Ended"}</Badge> },
          ]}
          formFields={sponsorshipFields}
          canCreate={!readOnly}
          canEdit={!readOnly}
          canDelete={!readOnly}
          createLabel="Add sponsored student"
          emptyTitle="No students under sponsorship"
          emptyDescription="Add a sponsor first, then record which students they support."
          mapRowToForm={(r) => ({ ...r, academic_year: r.academic_year ?? "", term: r.term ?? "" })}
        />
      )}

      {sub === "sponsors" && (
        <ResourceManager
          key="sponsors"
          title=""
          api={sponsorsApi}
          params={{ _v: version }}
          printTitle="Sponsors"
          columns={[
            { key: "name", label: "Sponsor" },
            { key: "sponsor_type", label: "Type", render: (r) => titleCase(r.sponsor_type) },
            { key: "contact_person", label: "Contact" },
            { key: "phone", label: "Phone" },
            { key: "students_count", label: "Students" },
            { key: "is_active", label: "Status", render: (r) => <Badge tone={r.is_active ? "accent" : "neutral"}>{r.is_active ? "Active" : "Inactive"}</Badge> },
          ]}
          formFields={sponsorFields}
          canCreate={!readOnly}
          canEdit={!readOnly}
          canDelete={!readOnly}
          createLabel="Add sponsor"
          emptyTitle="No sponsors yet"
          onCreated={() => setVersion((v) => v + 1)}
        />
      )}

      {sub === "report" && (
        <div>
          <div className="toolbar">
            <select value={reportTerm} onChange={(e) => setReportTerm(e.target.value)}>
              {terms.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
            <button className="btn btn-secondary btn-sm" type="button" onClick={printReportOut} disabled={!report?.sponsors?.length}>
              🖨 Print
            </button>
          </div>
          <AlertBanner type="error">{error}</AlertBanner>
          {loading ? (
            <LoadingSpinner ink />
          ) : !report?.sponsors?.length ? (
            <p className="hint">No sponsored students for this term.</p>
          ) : (
            report.sponsors.map((s) => (
              <div className="surface surface-pad" key={s.sponsor} style={{ marginBottom: 16 }}>
                <h3 style={{ marginTop: 0 }}>{s.sponsor_name}</h3>
                <div className="stat-grid">
                  <StatCard label="Expected from sponsor" value={formatCurrency(s.expected)} />
                  <StatCard label="Paid by sponsor" value={formatCurrency(s.paid)} />
                  <StatCard label="Still to pay" value={formatCurrency(s.outstanding)} />
                </div>
                <table className="data-table" style={{ marginTop: 12 }}>
                  <thead>
                    <tr>
                      <th>Student</th>
                      <th>Class</th>
                      <th>Covers</th>
                      <th>Expected</th>
                      <th>Paid</th>
                      <th>Outstanding</th>
                    </tr>
                  </thead>
                  <tbody>
                    {s.students.map((r) => (
                      <tr key={r.student}>
                        <td>
                          {r.student_name} <span className="hint">({r.student_index_number})</span>
                        </td>
                        <td>{r.school_class_name}</td>
                        <td>{r.coverage}</td>
                        <td>{formatCurrency(r.expected)}</td>
                        <td>{formatCurrency(r.paid)}</td>
                        <td>{formatCurrency(r.outstanding)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ expenses & other income */
export function ExpensesPanel() {
  const readOnly = useReadOnly();
  const fields = [
    { name: "date", label: "Date", type: "date", required: true },
    {
      name: "category",
      label: "Category",
      type: "select",
      required: true,
      options: [
        { value: "utilities", label: "Utilities (water, power, internet)" },
        { value: "supplies", label: "Teaching & office supplies" },
        { value: "maintenance", label: "Repairs & maintenance" },
        { value: "transport", label: "Transport & fuel" },
        { value: "food", label: "Food & catering" },
        { value: "events", label: "Events & activities" },
        { value: "equipment", label: "Equipment & furniture" },
        { value: "security", label: "Security & cleaning" },
        { value: "other", label: "Other" },
      ],
    },
    { name: "description", label: "What was it for?", type: "text", required: true },
    { name: "amount", label: "Amount", type: "number", step: "0.01", required: true },
    { name: "paid_to", label: "Paid to", type: "text" },
    { name: "method", label: "Payment method", type: "select", options: METHOD_OPTIONS, required: true },
    { name: "reference", label: "Receipt / voucher no.", type: "text" },
  ];
  return (
    <ResourceManager
      key="expenses"
      title=""
      api={expensesApi}
      printTitle="School Expenses"
      columns={[
        { key: "date", label: "Date", render: (r) => formatDate(r.date) },
        { key: "category_label", label: "Category" },
        { key: "description", label: "Description" },
        { key: "paid_to", label: "Paid to" },
        { key: "amount", label: "Amount", render: (r) => formatCurrency(r.amount) },
        { key: "method", label: "Method", render: (r) => titleCase(r.method) },
        { key: "reference", label: "Ref." },
      ]}
      formFields={fields}
      mapRowToForm={(r) => r}
      canCreate={!readOnly}
      canEdit={!readOnly}
      canDelete={!readOnly}
      createLabel="Record expense"
      emptyTitle="No expenses recorded yet"
    />
  );
}

export function OtherIncomePanel() {
  const readOnly = useReadOnly();
  const fields = [
    { name: "date", label: "Date", type: "date", required: true },
    {
      name: "category",
      label: "Category",
      type: "select",
      required: true,
      options: [
        { value: "donation", label: "Donation" },
        { value: "grant", label: "Grant" },
        { value: "fundraising", label: "Fundraising" },
        { value: "sales", label: "Uniform / book sales" },
        { value: "rent", label: "Rent / hire of facilities" },
        { value: "other", label: "Other" },
      ],
    },
    { name: "description", label: "Description", type: "text", required: true },
    { name: "amount", label: "Amount", type: "number", step: "0.01", required: true },
    { name: "received_from", label: "Received from", type: "text" },
    { name: "method", label: "Payment method", type: "select", options: METHOD_OPTIONS, required: true },
    { name: "reference", label: "Receipt / reference no.", type: "text" },
  ];
  return (
    <ResourceManager
      key="income"
      title=""
      api={otherIncomeApi}
      printTitle="Other Income"
      subtitle="Money received that is not a student fee: donations, grants, fundraising, sales and so on."
      columns={[
        { key: "date", label: "Date", render: (r) => formatDate(r.date) },
        { key: "category_label", label: "Category" },
        { key: "description", label: "Description" },
        { key: "received_from", label: "From" },
        { key: "amount", label: "Amount", render: (r) => formatCurrency(r.amount) },
        { key: "method", label: "Method", render: (r) => titleCase(r.method) },
      ]}
      formFields={fields}
      mapRowToForm={(r) => r}
      canCreate={!readOnly}
      canEdit={!readOnly}
      canDelete={!readOnly}
      createLabel="Record income"
      emptyTitle="No other income recorded yet"
    />
  );
}

/* ------------------------------------------------------------------ staff salaries */
export function SalariesPanel() {
  const readOnly = useReadOnly();
  const [staff, setStaff] = useState([]);
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [version, setVersion] = useState(0);

  useEffect(() => {
    salariesApi.staff().then((rows) => setStaff(rows.map((s) => ({ value: s.id, label: `${s.name} (${s.role})` }))));
  }, []);

  async function generate() {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const r = await salariesApi.generate({ year, month });
      setNotice(
        r.created
          ? `Created ${r.created} pay line(s) for ${MONTHS[month - 1]} ${year}. Check the amounts, then mark each as paid.`
          : `Pay lines for ${MONTHS[month - 1]} ${year} already exist.`
      );
      setVersion((v) => v + 1);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function markPaid(row) {
    setError("");
    try {
      await salariesApi.markPaid(row.id, { paid_date: today() });
      setVersion((v) => v + 1);
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  const fields = [
    { name: "staff", label: "Staff member", type: "select", options: staff, required: true },
    { name: "year", label: "Year", type: "number", required: true },
    { name: "month", label: "Month", type: "select", options: monthOptions, required: true },
    { name: "basic_salary", label: "Basic salary", type: "number", step: "0.01", required: true },
    { name: "allowances", label: "Allowances", type: "number", step: "0.01" },
    { name: "deductions", label: "Deductions", type: "number", step: "0.01" },
    { name: "method", label: "Payment method", type: "select", options: METHOD_OPTIONS, required: true },
    {
      name: "status",
      label: "Status",
      type: "select",
      required: true,
      options: [
        { value: "pending", label: "Pending" },
        { value: "paid", label: "Paid" },
      ],
    },
    { name: "paid_date", label: "Date paid", type: "date" },
    { name: "reference", label: "Reference", type: "text" },
    { name: "notes", label: "Notes", type: "text" },
  ];

  return (
    <div>
      {!readOnly && (
        <div className="surface surface-pad" style={{ marginBottom: 16 }}>
          <h3 style={{ marginTop: 0 }}>Generate monthly payroll</h3>
          <p className="hint" style={{ marginTop: 0 }}>
            Creates a pay line for every staff member, copying last month's amounts. Then adjust anyone's pay and mark each as paid.
          </p>
          <div className="toolbar" style={{ marginBottom: 0 }}>
            <select value={month} onChange={(e) => setMonth(Number(e.target.value))}>
              {monthOptions.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </select>
            <input type="number" style={{ width: 100 }} value={year} onChange={(e) => setYear(Number(e.target.value))} />
            <button className="btn btn-primary" type="button" onClick={generate} disabled={busy}>
              {busy ? "Working…" : "Generate payroll"}
            </button>
          </div>
          <AlertBanner type="error">{error}</AlertBanner>
          <AlertBanner type="success">{notice}</AlertBanner>
        </div>
      )}
      <ResourceManager
        key="salaries"
        title=""
        api={salariesApi}
        params={{ _v: version }}
        printTitle="Staff Salaries"
        columns={[
          { key: "period", label: "Month", render: (r) => `${MONTHS[r.month - 1]} ${r.year}` },
          { key: "staff_name", label: "Staff", render: (r) => `${r.staff_name} (${r.staff_role})` },
          { key: "basic_salary", label: "Basic", render: (r) => formatCurrency(r.basic_salary) },
          { key: "allowances", label: "Allowances", render: (r) => formatCurrency(r.allowances) },
          { key: "deductions", label: "Deductions", render: (r) => formatCurrency(r.deductions) },
          { key: "net_salary", label: "Net pay", render: (r) => <strong>{formatCurrency(r.net_salary)}</strong> },
          {
            key: "status",
            label: "Status",
            render: (r) => <Badge tone={r.status === "paid" ? "accent" : "gold"}>{r.status === "paid" ? `Paid ${formatDate(r.paid_date)}` : "Pending"}</Badge>,
          },
        ]}
        formFields={fields}
        mapRowToForm={(r) => r}
        canCreate={!readOnly}
        canEdit={!readOnly}
        canDelete={!readOnly}
        createLabel="Add salary"
        emptyTitle="No salaries recorded yet"
        emptyDescription="Use “Generate payroll” to create this month's pay lines."
        rowActions={(row) =>
          !readOnly && row.status !== "paid" ? (
            <button className="btn btn-primary btn-sm" type="button" onClick={() => markPaid(row)}>
              Mark paid
            </button>
          ) : null
        }
      />
    </div>
  );
}

/* ------------------------------------------------------------------ income & expenditure summary */
export function FinanceSummaryPanel() {
  const { user } = useAuth();
  const { terms } = useFinanceOptions();
  const [start, setStart] = useState(`${new Date().getFullYear()}-01-01`);
  const [end, setEnd] = useState(today());
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [arrearsTerm, setArrearsTerm] = useState("");
  const [arrears, setArrears] = useState(null);
  const [arrearsBusy, setArrearsBusy] = useState(false);

  async function generate() {
    setLoading(true);
    setError("");
    try {
      setData(await financeApi.summary({ start, end }));
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  async function loadArrears() {
    setArrearsBusy(true);
    setError("");
    try {
      setArrears(await financeApi.arrears(arrearsTerm ? { term: arrearsTerm } : {}));
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setArrearsBusy(false);
    }
  }

  useEffect(() => {
    generate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function printStatement() {
    printReport({
      title: "Income and Expenditure Statement",
      subtitle: `${formatDate(data.start)} to ${formatDate(data.end)}`,
      stats: [
        { label: "Total income", value: formatCurrency(data.income.total) },
        { label: "Total expenditure", value: formatCurrency(data.expenditure.total) },
        { label: data.net >= 0 ? "Surplus" : "Deficit", value: formatCurrency(Math.abs(data.net)) },
      ],
      sections: [
        {
          heading: "Income",
          columns: [
            { label: "Source", value: (r) => r.label },
            { label: "Amount", value: (r) => formatCurrency(r.amount), align: "right" },
          ],
          rows: [
            ...data.income.fees_by_method.map((r) => ({ label: `Student fees — ${r.label}`, amount: r.amount })),
            ...data.income.other_by_category.map((r) => ({ label: `Other income — ${r.label}`, amount: r.amount })),
          ],
          footer: ["Total income", formatCurrency(data.income.total)],
        },
        {
          heading: "Expenditure",
          columns: [
            { label: "Item", value: (r) => r.label },
            { label: "Amount", value: (r) => formatCurrency(r.amount), align: "right" },
          ],
          rows: [
            ...data.expenditure.expenses_by_category.map((r) => ({ label: r.label, amount: r.amount })),
            { label: "Staff salaries", amount: data.expenditure.salaries },
          ],
          footer: ["Total expenditure", formatCurrency(data.expenditure.total)],
        },
        {
          heading: "Month by month",
          columns: [
            { label: "Month", value: (r) => r.month },
            { label: "Income", value: (r) => formatCurrency(r.income), align: "right" },
            { label: "Expenditure", value: (r) => formatCurrency(r.expenses), align: "right" },
            { label: "Net", value: (r) => formatCurrency(r.net), align: "right" },
          ],
          rows: data.monthly,
        },
      ],
      printedBy: printedByOf(user),
    });
  }

  function printArrears() {
    printReport({
      title: "Students With Unpaid Fees",
      subtitle: `${arrears.term} · ${arrears.count} student(s) · total ${formatCurrency(arrears.total)}`,
      sections: [
        {
          columns: [
            { label: "Index No.", value: (r) => r.student_index_number },
            { label: "Student", value: (r) => r.student_name },
            { label: "Class", value: (r) => r.school_class_name },
            { label: "Fees", value: (r) => formatCurrency(r.fees_due), align: "right" },
            { label: "Carried fwd", value: (r) => formatCurrency(r.carried_forward), align: "right" },
            { label: "Paid", value: (r) => formatCurrency(r.paid), align: "right" },
            { label: "Balance", value: (r) => formatCurrency(r.balance), align: "right" },
            { label: "Sponsor", value: (r) => r.sponsor_names || "" },
          ],
          rows: arrears.students,
        },
      ],
      printedBy: printedByOf(user),
    });
  }

  return (
    <div>
      <div className="surface surface-pad" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Income and expenditure statement</h3>
        <div className="toolbar" style={{ marginBottom: 0 }}>
          <label>
            From <input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
          </label>
          <label>
            To <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
          </label>
          <button className="btn btn-primary" type="button" onClick={generate} disabled={loading}>
            {loading ? "Working…" : "Generate"}
          </button>
          <button className="btn btn-secondary" type="button" onClick={printStatement} disabled={!data}>
            🖨 Print
          </button>
        </div>
      </div>
      <AlertBanner type="error">{error}</AlertBanner>

      {data && (
        <>
          <div className="stat-grid">
            <StatCard label="Fees collected" value={formatCurrency(data.income.fees)} />
            <StatCard label="Other income" value={formatCurrency(data.income.other)} />
            <StatCard label="Expenses" value={formatCurrency(data.expenditure.expenses)} />
            <StatCard label="Staff salaries paid" value={formatCurrency(data.expenditure.salaries)} />
            <StatCard label={data.net >= 0 ? "Surplus" : "Deficit"} value={formatCurrency(Math.abs(data.net))} />
          </div>
          {Number(data.income.fees_from_sponsors) > 0 && (
            <p className="hint">Of the fees collected, {formatCurrency(data.income.fees_from_sponsors)} came from sponsors.</p>
          )}

          <div className="surface surface-pad" style={{ marginBottom: 16 }}>
            <h3 style={{ marginTop: 0 }}>Month by month</h3>
            {data.monthly.length ? (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Month</th>
                    <th>Income</th>
                    <th>Expenditure</th>
                    <th>Net</th>
                  </tr>
                </thead>
                <tbody>
                  {data.monthly.map((m) => (
                    <tr key={m.month}>
                      <td>{m.month}</td>
                      <td>{formatCurrency(m.income)}</td>
                      <td>{formatCurrency(m.expenses)}</td>
                      <td>
                        <strong>{formatCurrency(m.net)}</strong>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="hint">Nothing recorded between these dates.</p>
            )}
          </div>
        </>
      )}

      <div className="surface surface-pad">
        <h3 style={{ marginTop: 0 }}>Students who have not paid</h3>
        <div className="toolbar">
          <select value={arrearsTerm} onChange={(e) => setArrearsTerm(e.target.value)}>
            <option value="">Current term</option>
            {terms.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
          <button className="btn btn-secondary" type="button" onClick={loadArrears} disabled={arrearsBusy}>
            {arrearsBusy ? "Working…" : "Show unpaid fees"}
          </button>
          <button className="btn btn-secondary" type="button" onClick={printArrears} disabled={!arrears?.count}>
            🖨 Print
          </button>
        </div>
        {arrears &&
          (arrears.count ? (
            <>
              <p className="hint">
                {arrears.term}: {arrears.count} student(s) owe {formatCurrency(arrears.total)} in total.
              </p>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Student</th>
                    <th>Class</th>
                    <th>Fees</th>
                    <th>Carried fwd</th>
                    <th>Paid</th>
                    <th>Balance</th>
                  </tr>
                </thead>
                <tbody>
                  {arrears.students.map((r) => (
                    <tr key={r.student}>
                      <td>
                        {r.student_name} <span className="hint">({r.student_index_number})</span>
                        {r.sponsor_names ? <Badge tone="info">{r.sponsor_names}</Badge> : null}
                      </td>
                      <td>{r.school_class_name}</td>
                      <td>{formatCurrency(r.fees_due)}</td>
                      <td>{formatCurrency(r.carried_forward)}</td>
                      <td>{formatCurrency(r.paid)}</td>
                      <td>
                        <strong>{formatCurrency(r.balance)}</strong>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          ) : (
            <p className="hint">Everyone has paid for {arrears.term}.</p>
          ))}
      </div>
    </div>
  );
}
