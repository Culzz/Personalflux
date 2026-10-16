import type { ReactNode } from "react";

export default function EmptyState({
  icon,
  title,
  hint,
  action,
}: {
  icon: ReactNode;
  title: string;
  hint: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty">
      <div>{icon}</div>
      <h3 style={{ color: "var(--ink)" }}>{title}</h3>
      <p className="muted">{hint}</p>
      {action}
    </div>
  );
}
