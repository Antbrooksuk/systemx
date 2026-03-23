"use client";

export interface ViewToggleProps {
  view: "table" | "markdown";
  onViewChange: (view: "table" | "markdown") => void;
}

export function ViewToggle({ view, onViewChange }: ViewToggleProps) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <button
        onClick={() => onViewChange("table")}
        className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
          view === "table"
            ? "bg-profit/20 text-profit border border-profit"
            : "bg-card text-muted border border-border hover:bg-border"
        }`}
      >
        Table
      </button>
      <button
        onClick={() => onViewChange("markdown")}
        className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
          view === "markdown"
            ? "bg-profit/20 text-profit border border-profit"
            : "bg-card text-muted border border-border hover:bg-border"
        }`}
      >
        Markdown
      </button>
    </div>
  );
}
