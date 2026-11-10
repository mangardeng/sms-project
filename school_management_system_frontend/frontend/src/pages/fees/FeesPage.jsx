import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { classesApi } from "../../api/classes";
import { termsApi } from "../../api/academic";
import { extractErrorMessage } from "../../api/client";
import { feeStructuresApi, getFeeBalance, paymentsApi, sponsorsApi } from "../../api/fees";
import { studentsApi } from "../../api/students";
import AlertBanner from "../../components/AlertBanner";
import Badge from "../../components/Badge";
import LoadingSpinner from "../../components/LoadingSpinner";
import ResourceManager from "../../components/ResourceManager";
import StatCard from "../../components/StatCard";
import { useAuth } from "../../context/AuthContext";
import { formatCurrency, formatDate, titleCase } from "../../utils/format";
import { documentShell, escapeHtml, printHtml, printReport, SCHOOL_NAME, formatStamp } from "../../utils/print";
import FeesReport from "./FeesReport";
import {
  CarryForwardPanel,
  ExpensesPanel,
  FinanceSummaryPanel,
  OtherIncomePanel,
  SalariesPanel,
  SponsorshipPanel,
} from "./FinancePanels";
import { PaymentEditModal, PaymentHistoryModal, PaymentVoidModal } from "./PaymentTools";
import { ROLES } from "../../utils/roles";

const METHOD_OPTIONS = [
  { value: "cash", label: "Cash" },
  { value: "bank_transfer", label: "Bank Transfer" },
  { value: "mobile_money", label: "Mobile Money" },
  { value: "card", label: "Card" },
  { value: "cheque", label: "Cheque" },
];

/** Prints an official receipt for one payment. */
function printReceipt(p, issuedBy) {
  const row = (label, value) => `<div class="row"><span>${escapeHtml(label)}</span><span>${escapeHtml(value || "—")}</span></div>`;
  printHtml(
    documentShell({
      title: `Receipt ${p.receipt_number}`,
      body: `
        <div class="doc-head">
          <div><div class="school">${escapeHtml(SCHOOL_NAME)}</div><div class="doc-title">Official Fee Receipt</div></div>
          <div class="meta">Receipt No.<br/><b>${escapeHtml(p.receipt_number)}</b></div>
        </div>
        <div class="receipt">
          ${row("Date", formatDate(p.payment_date))}
          ${row("Student", p.student_name)}
          ${row("Index number", p.student_index_number)}
          ${row("Fee paid for", p.fee_structure_name)}
          ${row("Payment method", titleCase(p.method))}
          ${p.notes ? row("Notes", p.notes) : ""}
          <div class="amount">${escapeHtml(formatCurrency(p.amount_paid))}</div>
          <div class="sign"><div>Received by${issuedBy ? ` (${escapeHtml(issuedBy)})` : ""}</div><div>Parent / guardian signature</div></div>
          <div class="foot"><span>Printed ${escapeHtml(formatStamp())}</span><span>Keep this receipt as proof of payment</span></div>
        </div>`,
    })
  );
}

export default function FeesPage() {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const studentFilter = searchParams.get("student");

  const canManage = [ROLES.ADMIN, ROLES.ACCOUNTANT].includes(user?.role);

  if ([ROLES.PARENT, ROLES.STUDENT].includes(user?.role) || (studentFilter && !canManage)) {
    return <MyFeesView studentId={studentFilter} />;
  }
  return <ManageFees studentFilter={studentFilter} />;
}

/** Term breakdown: fees, payments, balance carried from earlier terms and what a sponsor covers. */
function StatementBreakdown({ balance }) {
  const s = balance?.statement;
  if (!s) return null;
  const sponsored = Number(s.sponsor_share) > 0;
  return (
    <div style={{ marginTop: 10 }}>
      <p className="hint" style={{ margin: "0 0 6px" }}>
        {balance.statement_term}
      </p>
      <div className="stat-grid">
        <StatCard label="Fees this term" value={formatCurrency(s.fees_due)} />
        <StatCard label="Carried forward (unpaid before)" value={formatCurrency(s.carried_forward)} />
        <StatCard label="Paid this term" value={formatCurrency(s.paid)} />
        <StatCard label="Balance this term" value={formatCurrency(s.balance)} />
      </div>
      {sponsored && (
        <div className="stat-grid" style={{ marginTop: 10 }}>
          <StatCard label={`Sponsor covers (${s.sponsor_names})`} value={formatCurrency(s.sponsor_share)} />
          <StatCard label="Sponsor has paid" value={formatCurrency(s.sponsor_paid)} />
          <StatCard label="Family share" value={formatCurrency(s.family_share)} />
          <StatCard label="Family still to pay" value={formatCurrency(s.family_outstanding)} />
        </div>
      )}
    </div>
  );
}

function BalanceLookup({ studentId: initialStudentId }) {
  const [studentId, setStudentId] = useState(initialStudentId || "");
  const [balance, setBalance] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function lookup(id) {
    if (!id) return;
    setLoading(true);
    setError("");
    try {
      const data = await getFeeBalance(id);
      setBalance(data);
    } catch (err) {
      setError(extractErrorMessage(err, "Could not look up this student's balance."));
      setBalance(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (initialStudentId) lookup(initialStudentId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialStudentId]);

  return (
    <div className="surface surface-pad" style={{ marginBottom: 20 }}>
      <h3>Check a student's balance</h3>
      <div className="toolbar" style={{ marginBottom: balance || error ? 14 : 0 }}>
        <input
          type="number"
          placeholder="Student ID"
          value={studentId}
          onChange={(e) => setStudentId(e.target.value)}
          style={{ minWidth: 140 }}
        />
        <button className="btn btn-secondary" type="button" onClick={() => lookup(studentId)} disabled={loading}>
          {loading ? "Checking…" : "Check balance"}
        </button>
      </div>
      <AlertBanner type="error">{error}</AlertBanner>
      {balance && (
        <p style={{ margin: 0 }}>
          <strong>{balance.student_name}</strong> ({balance.student_index_number}) —{" "}
          balance: <strong>{formatCurrency(balance.balance)}</strong>
        </p>
      )}
      {balance && <StatementBreakdown balance={balance} />}
    </div>
  );
}

function ManageFees({ studentFilter }) {
  const { user } = useAuth();
  const [classOptions, setClassOptions] = useState([]);
  const [studentOptions, setStudentOptions] = useState([]);
  const [termOptions, setTermOptions] = useState([]);
  const [structureOptions, setStructureOptions] = useState([]);
  const [tab, setTab] = useState(studentFilter ? "payments" : "structures");
  const [sponsorOptions, setSponsorOptions] = useState([]);
  const [editRow, setEditRow] = useState(null);
  const [voidRow, setVoidRow] = useState(null);
  const [historyRow, setHistoryRow] = useState(null);
  const [version, setVersion] = useState(0);
  const isAccountant = user?.role === ROLES.ACCOUNTANT || user?.is_superuser;
  const canSeeFinance = isAccountant || [ROLES.ADMIN, ROLES.HEAD_TEACHER].includes(user?.role);
  const canSeeHistory = canSeeFinance;

  useEffect(() => {
    classesApi.list({ page_size: 200 }).then((d) => setClassOptions((d.results || d).map((c) => ({ value: c.id, label: c.name }))));
    studentsApi.list({ page_size: 300 }).then((d) =>
      setStudentOptions(
        (d.results || d).map((s) => ({
          value: s.id,
          label: `${s.index_number} — ${s.user?.first_name || ""} ${s.user?.last_name || ""}`.trim(),
        }))
      )
    );
    termsApi.list({ page_size: 50 }).then((d) =>
      setTermOptions((d.results || d).map((t) => ({ value: t.id, label: t.display_name || `${t.name} — ${t.academic_year_name}` })))
    );
    if (canSeeFinance) {
      sponsorsApi.list({ page_size: 200 }).then((d) => setSponsorOptions((d.results || d).map((s) => ({ value: s.id, label: s.name }))));
    }
    feeStructuresApi.list({ page_size: 200 }).then((d) =>
      setStructureOptions((d.results || d).map((f) => ({ value: f.id, label: `${f.school_class_name} — ${f.name} (${f.term_name})` })))
    );
  }, []);

  const structureFields = [
    { name: "school_class", label: "Class", type: "select", options: classOptions, required: true },
    { name: "term", label: "Term", type: "select", options: termOptions, required: true },
    { name: "name", label: "Fee name", type: "text", required: true, placeholder: "e.g. Tuition Fee" },
    { name: "amount", label: "Amount", type: "number", required: true },
    { name: "is_mandatory", label: "Mandatory", type: "checkbox", checkboxLabel: "This fee is mandatory" },
  ];

  const paymentFields = [
    { name: "student", label: "Student", type: "select", options: studentOptions, required: true },
    { name: "fee_structure", label: "Fee structure", type: "select", options: structureOptions, required: true },
    { name: "amount_paid", label: "Amount paid", type: "number", step: "0.01", required: true },
    { name: "method", label: "Payment method", type: "select", options: METHOD_OPTIONS, required: true },
    { name: "payment_date", label: "Payment date", type: "date", hint: "Leave blank for today." },
    ...(canSeeFinance ? [{ name: "sponsor", label: "Paid by sponsor (if any)", type: "select", options: sponsorOptions }] : []),
    { name: "notes", label: "Notes", type: "text" },
  ];

  const tabButton = (key, label) => (
    <button className={`btn btn-sm ${tab === key ? "btn-primary" : "btn-secondary"}`} type="button" onClick={() => setTab(key)}>
      {label}
    </button>
  );

  return (
    <div>
      <div className="page-header">
        <h1>Fees</h1>
      </div>

      {tab !== "report" && <BalanceLookup studentId={studentFilter} />}

      <div className="toolbar">
        <button className={`btn btn-sm ${tab === "structures" ? "btn-primary" : "btn-secondary"}`} type="button" onClick={() => setTab("structures")}>
          Fee structures
        </button>
        <button className={`btn btn-sm ${tab === "payments" ? "btn-primary" : "btn-secondary"}`} type="button" onClick={() => setTab("payments")}>
          Payments
        </button>
        {canSeeFinance && tabButton("carry", "Carry forward")}
        {canSeeFinance && tabButton("sponsorship", "Sponsorship")}
        {canSeeFinance && tabButton("expenses", "Expenses")}
        {canSeeFinance && tabButton("salaries", "Staff salaries")}
        {canSeeFinance && tabButton("income", "Other income")}
        {canSeeFinance && tabButton("summary", "💰 Income & expenditure")}
        <button className={`btn btn-sm ${tab === "report" ? "btn-primary" : "btn-secondary"}`} type="button" onClick={() => setTab("report")}>
          📊 Report
        </button>
      </div>

      {tab === "report" ? (
        <FeesReport />
      ) : canSeeFinance && tab === "carry" ? (
        <CarryForwardPanel />
      ) : canSeeFinance && tab === "sponsorship" ? (
        <SponsorshipPanel />
      ) : canSeeFinance && tab === "expenses" ? (
        <ExpensesPanel />
      ) : canSeeFinance && tab === "salaries" ? (
        <SalariesPanel />
      ) : canSeeFinance && tab === "income" ? (
        <OtherIncomePanel />
      ) : canSeeFinance && tab === "summary" ? (
        <FinanceSummaryPanel />
      ) : tab === "structures" ? (
        <ResourceManager
          key="structures"
          title=""
          api={feeStructuresApi}
          printTitle="Fee Structures"
          columns={[
            { key: "school_class_name", label: "Class" },
            { key: "term_name", label: "Term" },
            { key: "name", label: "Fee" },
            { key: "amount", label: "Amount", render: (row) => formatCurrency(row.amount) },
            { key: "is_mandatory", label: "Mandatory", render: (row) => (row.is_mandatory ? "Yes" : "No") },
          ]}
          formFields={structureFields}
          createLabel="Add fee structure"
          emptyTitle="No fee structures yet"
        />
      ) : (
        <ResourceManager
          key="payments"
          title=""
          printTitle="Fee Payments"
          api={paymentsApi}
          params={{ ...(studentFilter ? { student: studentFilter } : {}), _v: version }}
          columns={[
            { key: "receipt_number", label: "Receipt" },
            { key: "student_name", label: "Student", render: (row) => `${row.student_name} (${row.student_index_number})` },
            { key: "fee_structure_name", label: "Fee" },
            {
              key: "amount_paid",
              label: "Amount",
              render: (row) => (
                <span style={row.is_void ? { textDecoration: "line-through", opacity: 0.6 } : undefined}>{formatCurrency(row.amount_paid)}</span>
              ),
            },
            { key: "method", label: "Method", render: (row) => titleCase(row.method) },
            { key: "payment_date", label: "Date", render: (row) => formatDate(row.payment_date) },
            { key: "sponsor_name", label: "Paid by", render: (row) => row.sponsor_name || "Family" },
            ...(canSeeFinance
              ? [{ key: "is_void", label: "Status", render: (row) => (row.is_void ? <Badge tone="alert">VOID</Badge> : <Badge tone="accent">Valid</Badge>) }]
              : []),
          ]}
          formFields={paymentFields}
          canEdit={false}
          canDelete={false}
          rowActions={(row) => (
            <>
              {!row.is_void && (
                <button className="btn btn-secondary btn-sm" type="button" onClick={() => printReceipt(row, `${user?.first_name || ""} ${user?.last_name || ""}`.trim())}>
                  🖨 Receipt
                </button>
              )}
              {isAccountant && !row.is_void && (
                <button className="btn btn-secondary btn-sm" type="button" onClick={() => setEditRow(row)}>
                  ✏️ Correct
                </button>
              )}
              {isAccountant && !row.is_void && (
                <button className="btn btn-secondary btn-sm" type="button" onClick={() => setVoidRow(row)}>
                  Void
                </button>
              )}
              {canSeeHistory && (
                <button className="btn btn-secondary btn-sm" type="button" onClick={() => setHistoryRow(row)}>
                  History
                </button>
              )}
            </>
          )}
          createLabel="Record payment"
          emptyTitle="No payments recorded yet"
        />
      )}

      {editRow && (
        <PaymentEditModal
          payment={editRow}
          studentOptions={studentOptions}
          structureOptions={structureOptions}
          sponsorOptions={sponsorOptions}
          onClose={() => setEditRow(null)}
          onSaved={() => {
            setEditRow(null);
            setVersion((v) => v + 1);
          }}
        />
      )}
      {voidRow && (
        <PaymentVoidModal
          payment={voidRow}
          onClose={() => setVoidRow(null)}
          onSaved={() => {
            setVoidRow(null);
            setVersion((v) => v + 1);
          }}
        />
      )}
      {historyRow && <PaymentHistoryModal payment={historyRow} onClose={() => setHistoryRow(null)} />}
    </div>
  );
}

function MyFeesView({ studentId }) {
  const { user } = useAuth();
  const [balance, setBalance] = useState(null);
  const [payments, setPayments] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      getFeeBalance(studentId).catch(() => null),
      paymentsApi.list(studentId ? { student: studentId, page_size: 100 } : { page_size: 100 }),
    ])
      .then(([balanceData, paymentsData]) => {
        setBalance(balanceData);
        setPayments(paymentsData.results || paymentsData);
      })
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [studentId]);

  if (loading) return <LoadingSpinner ink />;

  return (
    <div>
      <div className="page-header">
        <h1>Fees</h1>
        {user?.role !== ROLES.STUDENT && (
        <button
          className="btn btn-primary"
          type="button"
          disabled={!payments.length && !balance}
          onClick={() => {
            const multi = new Set(payments.map((p) => p.student)).size > 1;
            const total = formatCurrency(payments.reduce((a, p) => a + Number(p.amount_paid || 0), 0));
            printReport({
              title: "Fee Statement",
              subtitle: balance ? `${balance.student_name} (${balance.student_index_number})` : undefined,
              stats: balance ? [{ label: "Outstanding balance", value: formatCurrency(balance.balance) }] : [],
              sections: [
                {
                  heading: "Payment history",
                  columns: [
                    { label: "Receipt", value: (p) => p.receipt_number },
                    { label: "Date", value: (p) => formatDate(p.payment_date) },
                    ...(multi ? [{ label: "Student", value: (p) => p.student_name }] : []),
                    { label: "Fee", value: (p) => p.fee_structure_name },
                    { label: "Method", value: (p) => titleCase(p.method) },
                    { label: "Amount", value: (p) => formatCurrency(p.amount_paid), align: "right" },
                  ],
                  rows: payments,
                  footer: payments.length ? [...(multi ? ["", "", "", ""] : ["", "", ""]), "Total", total] : undefined,
                },
              ],
              printedBy: `${user?.first_name || ""} ${user?.last_name || ""}`.trim() || user?.username,
            });
          }}
        >
          🖨 Print statement
        </button>
        )}
      </div>
      <AlertBanner type="error">{error}</AlertBanner>

      {balance && (
        <>
          <div className="stat-grid">
            <StatCard label={`${balance.student_name}'s total balance`} value={formatCurrency(balance.balance)} />
          </div>
          <StatementBreakdown balance={balance} />
        </>
      )}

      <div className="surface surface-pad">
        <h3>Payment history</h3>
        {payments.length ? (
          <table className="data-table">
            <thead>
              <tr>
                <th>Receipt</th>
                <th>Fee</th>
                <th>Amount</th>
                <th>Method</th>
                <th>Date</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {payments.map((p) => (
                <tr key={p.id}>
                  <td>{p.receipt_number}</td>
                  <td>{p.fee_structure_name}</td>
                  <td>{formatCurrency(p.amount_paid)}</td>
                  <td>{titleCase(p.method)}</td>
                  <td>{formatDate(p.payment_date)}</td>
                  <td>
                    {user?.role !== ROLES.STUDENT && (
                      <button className="btn btn-secondary btn-sm" type="button" onClick={() => printReceipt(p)}>
                        🖨 Receipt
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="hint">No payments recorded yet.</p>
        )}
      </div>
    </div>
  );
}
