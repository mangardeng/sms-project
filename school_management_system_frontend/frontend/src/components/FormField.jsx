import PhotoInput from "./PhotoInput";

/**
 * Renders one input based on a field descriptor:
 *   { name, label, type, required, options, hint, placeholder, readOnly, step, dependsOn }
 * type: "text" | "email" | "password" | "number" | "date" | "select" | "multiselect"
 *       | "checkbox" | "textarea" | "file"
 * options (for select): [{ value, label }] OR a function (formValues) => [{ value, label }]
 *   — the function form lets one dropdown depend on another (e.g. stream by class).
 * readOnly: shown but not editable, and never sent to the API.
 */
export default function FormField({ field, value, onChange, error, values = {}, initialValue }) {
  const { name, label, type = "text", required, hint, placeholder, readOnly } = field;
  const options = typeof field.options === "function" ? field.options(values) : field.options;

  const commonProps = {
    id: name,
    name,
    required: required && !readOnly,
    placeholder,
    disabled: readOnly,
  };

  function handleChange(e) {
    const raw = type === "checkbox" ? e.target.checked : e.target.value;
    onChange(name, raw);
  }

  return (
    <div className={`field${type === "file" ? " field-wide" : ""}`}>
      <label htmlFor={name}>
        {label}
        {required && !readOnly ? <span className="required-mark"> *</span> : null}
      </label>

      {type === "file" ? (
        <PhotoInput id={name} name={name} value={value} existing={initialValue} onChange={onChange} />
      ) : type === "select" ? (
        <select {...commonProps} value={value ?? ""} onChange={handleChange}>
          <option value="">{field.placeholder || "Select…"}</option>
          {(options || []).map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      ) : type === "multiselect" ? (
        <select
          {...commonProps}
          multiple
          size={Math.min(6, Math.max(3, (options || []).length))}
          value={(value || []).map(String)}
          onChange={(e) => {
            const selected = Array.from(e.target.selectedOptions).map((o) => o.value);
            onChange(name, selected);
          }}
        >
          {(options || []).map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      ) : type === "textarea" ? (
        <textarea {...commonProps} rows={field.rows || 3} value={value ?? ""} onChange={handleChange} />
      ) : type === "checkbox" ? (
        <label style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 400 }}>
          <input type="checkbox" checked={!!value} onChange={handleChange} disabled={readOnly} />
          {field.checkboxLabel || "Yes"}
        </label>
      ) : (
        <input
          {...commonProps}
          type={type}
          step={type === "number" ? field.step || "any" : undefined}
          value={value ?? ""}
          onChange={handleChange}
        />
      )}

      {hint && !error && <span className="hint">{hint}</span>}
      {error && <span className="field-error">{error}</span>}
    </div>
  );
}
