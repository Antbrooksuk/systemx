interface StatCardProps {
  label: string;
  value: string | number;
  suffix?: string;
  color?: "default" | "profit" | "loss" | "warn";
}

export function StatCard({ label, value, suffix = "", color = "default" }: StatCardProps) {
  const colorClass = {
    default: "text-fg",
    profit: "text-profit",
    loss: "text-loss",
    warn: "text-warn",
  }[color];

  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="text-muted text-xs uppercase tracking-wider mb-1">{label}</div>
      <div className={`text-2xl font-mono ${colorClass}`}>
        {value}
        {suffix}
      </div>
    </div>
  );
}
