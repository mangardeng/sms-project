export default function EmptyState({ title = "Nothing here yet", description, action }) {
  return (
    <div className="empty-state">
      <h3>{title}</h3>
      {description && <p style={{ margin: "0 auto 16px" }}>{description}</p>}
      {action}
    </div>
  );
}
