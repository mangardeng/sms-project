export default function LoadingSpinner({ ink = false, label }) {
  return (
    <div className="center-loading" role="status" aria-live="polite">
      <span className={`spinner ${ink ? "spinner-ink" : ""}`} />
      {label && <span style={{ marginLeft: 10 }}>{label}</span>}
    </div>
  );
}
