import { useEffect, useState } from "react";

import { extractErrorMessage } from "../../api/client";
import { paymentsApi } from "../../api/fees";
import AlertBanner from "../../components/AlertBanner";
import LoadingSpinner from "../../components/LoadingSpinner";
import Modal from "../../components/Modal";
import ResourceForm from "../../components/ResourceForm";
import { formatDateTime } from "../../utils/format";

export const METHOD_OPTIONS = [
  { value: "cash", label: "Cash" },
  { value: "bank_transfer", label: "Bank Transfer" },
  { value: "mobile_money", label: "Mobile Money" },
  { value: "card", label: "Card" },
  { value: "cheque", label: "Cheque" },
];

/** Accountant-only: correct a payment that was recorded wrongly. A reason is required and kept in its history. */
export function PaymentEditModal({ payment, studentOptions, structureOptions, sponsorOptions, onClose, onSaved }) {
  const fields = [
    { name: "student", label: "Student", type: "select", options: studentOptions, required: true },
    { name: "fee_structure", label: "Fee structure", type: "select", options: structureOptions, required: true },
    { name: "amount_paid", label: "Amount paid", type: "number", step: "0.01", required: true },
    { name: "method", label: "Payment method", type: "select", options: METHOD_OPTIONS, required: true },
    { name: "payment_date", label: "Payment date", type: "date", required: true },
    { name: "sponsor", label: "Paid by sponsor (if any)", type: "select", options: sponsorOptions },
    { name: "notes", label: "Notes", type: "text" },
    { name: "reason", label: "Reason for this correction", type: "text", required: true, placeholder: "e.g. Keyed 300 instead of 350" },
  ];

  return (
    <Modal title={`Correct payment ${payment.receipt_number}`} onClose={onClose} width={680}>
      <p className="hint" style={{ marginTop: 0 }}>
        Only the accountant can do this. The old and new values and your reason are saved in the payment's history.
      </p>
      <ResourceForm
        fields={fields}
        initialValues={{ ...payment, sponsor: payment.sponsor ?? "", reason: "" }}
        onCancel={onClose}
        submitLabel="Save correction"
        mode="edit"
        onSubmit={async (values) => {
          await paymentsApi.correct(payment.id, values);
          onSaved();
        }}
      />
    </Modal>
  );
}

/** Accountant-only: cancel a payment entered by mistake (it is kept for the record, but no longer counted). */
export function PaymentVoidModal({ payment, onClose, onSaved }) {
  return (
    <Modal title={`Void payment ${payment.receipt_number}`} onClose={onClose} width={560}>
      <p className="hint" style={{ marginTop: 0 }}>
        The payment stays in the history marked VOID, but it is no longer counted in balances, income or receipts for the family. Use
        this when a payment was recorded for the wrong student or should never have been entered.
      </p>
      <ResourceForm
        fields={[{ name: "reason", label: "Reason", type: "text", required: true, placeholder: "e.g. Recorded for the wrong student" }]}
        onCancel={onClose}
        submitLabel="Void payment"
        onSubmit={async (values) => {
          await paymentsApi.void(payment.id, values.reason);
          onSaved();
        }}
      />
    </Modal>
  );
}

export function PaymentHistoryModal({ payment, onClose }) {
  const [rows, setRows] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    paymentsApi
      .history(payment.id)
      .then(setRows)
      .catch((err) => setError(extractErrorMessage(err)));
  }, [payment.id]);

  return (
    <Modal title={`History of ${payment.receipt_number}`} onClose={onClose} width={720}>
      <AlertBanner type="error">{error}</AlertBanner>
      {rows === null && !error ? (
        <LoadingSpinner ink />
      ) : rows && rows.length === 0 ? (
        <p className="hint">This payment has never been corrected.</p>
      ) : (
        rows && (
          <table className="data-table">
            <thead>
              <tr>
                <th>When</th>
                <th>By</th>
                <th>What changed</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td>{formatDateTime(r.changed_at)}</td>
                  <td>{r.changed_by_name || "—"}</td>
                  <td>
                    <strong>{r.action === "void" ? "Voided: " : ""}</strong>
                    {r.changes}
                  </td>
                  <td>{r.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )
      )}
    </Modal>
  );
}
