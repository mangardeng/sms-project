import { useState } from "react";

import { extractErrorMessage } from "../api/client";
import AlertBanner from "./AlertBanner";
import FormField from "./FormField";

const isFile = (v) => typeof File !== "undefined" && v instanceof File;

/**
 * Builds the request body from the raw form state:
 *  - read-only fields are never sent;
 *  - file fields are only sent when a NEW file was chosen (so editing a
 *    record never wipes its existing photo);
 *  - blank optional dates / numbers are omitted (or cleared with null when editing a date),
 *    because the API rejects "" for those types;
 *  - fields flagged `emptyAsNull` send null when blank (e.g. a unique, optional ISBN).
 */
export function buildPayload(fields, values, mode) {
  const payload = {};
  fields.forEach((f) => {
    if (f.readOnly) return;
    const v = values[f.name];

    if (f.type === "file") {
      if (isFile(v)) payload[f.name] = v;
      return;
    }
    if (v === "" && f.emptyAsNull) {
      payload[f.name] = null;
      return;
    }
    if (v === "" && f.type === "date") {
      if (mode === "edit") payload[f.name] = null;
      return;
    }
    if (v === "" && f.type === "number") return;

    payload[f.name] = v;
  });
  return payload;
}

export default function ResourceForm({
  fields,
  initialValues = {},
  onSubmit,
  onCancel,
  submitLabel = "Save",
  mode = "create",
}) {
  const [values, setValues] = useState(() => {
    const base = {};
    fields.forEach((f) => {
      base[f.name] = initialValues[f.name] ?? (f.type === "checkbox" ? false : f.type === "multiselect" ? [] : "");
    });
    return base;
  });
  const [fieldErrors, setFieldErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  function handleChange(name, value) {
    setValues((prev) => {
      const next = { ...prev, [name]: value };
      // A dependent dropdown (e.g. stream) is cleared when the field it depends on (class) changes.
      fields.forEach((f) => {
        if (f.dependsOn === name) next[f.name] = "";
      });
      return next;
    });
    setFieldErrors((prev) => ({ ...prev, [name]: undefined }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setFormError("");
    setFieldErrors({});
    setSaving(true);
    try {
      await onSubmit(buildPayload(fields, values, mode));
    } catch (error) {
      const data = error?.response?.data;
      const backendErrors = data?.errors || data;
      if (backendErrors && typeof backendErrors === "object" && !Array.isArray(backendErrors)) {
        const mapped = {};
        Object.entries(backendErrors).forEach(([key, val]) => {
          if (fields.some((f) => f.name === key)) mapped[key] = Array.isArray(val) ? val[0] : String(val);
        });
        setFieldErrors(mapped);
      }
      setFormError(extractErrorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <AlertBanner type="error">{formError}</AlertBanner>
      <div className="form-grid">
        {fields.map((f) => (
          <FormField
            key={f.name}
            field={f}
            value={values[f.name]}
            values={values}
            initialValue={initialValues[f.name]}
            onChange={handleChange}
            error={fieldErrors[f.name]}
          />
        ))}
      </div>
      <div className="modal-footer">
        <button type="button" className="btn btn-secondary" onClick={onCancel} disabled={saving}>
          Cancel
        </button>
        <button type="submit" className="btn btn-primary" disabled={saving}>
          {saving ? <span className="spinner" /> : null}
          {saving ? "Saving…" : submitLabel}
        </button>
      </div>
    </form>
  );
}
