"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { EquityPoint } from "../lib/types";

interface EquityCurveProps {
  data: EquityPoint[];
}

export function EquityCurve({ data }: EquityCurveProps) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-card border border-border rounded-lg p-4 h-64 flex items-center justify-center">
        <div className="text-muted">No data yet</div>
      </div>
    );
  }

  const chartData = data
    .slice()
    .sort((a, b) =>
      a.date && b.date
        ? new Date(a.date).getTime() - new Date(b.date).getTime()
        : 0,
    );

  return (
    <div className="bg-card border border-border rounded-lg p-4 h-125">
      <div className="text-muted text-xs uppercase tracking-wider mb-2">
        Equity Curve
      </div>
      <ResponsiveContainer width="100%" height={500}>
        <LineChart data={chartData}>
          <XAxis
            dataKey="date"
            stroke="#737373"
            fontSize={10}
            tickFormatter={(v) => {
              if (!v) return "";
              const d = new Date(v);
              return `${d.getMonth() + 1}/${d.getDate()}`;
            }}
          />
          <YAxis
            stroke="#737373"
            fontSize={10}
            tickFormatter={(v) => {
              if (v >= 1000000) return `£${(v / 1000000).toFixed(1)}M`;
              if (v >= 1000) return `£${(v / 1000).toFixed(0)}K`;
              return `£${v.toFixed(0)}`;
            }}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const point = payload[0].payload as EquityPoint;
              const dateStr = point.date
                ? new Date(point.date).toLocaleDateString()
                : "Start";
              return (
                <div className="bg-[#141414] border border-[#262626] rounded px-3 py-2">
                  <div className="text-[#737373] text-xs mb-1">{dateStr}</div>
                  <div className="text-white text-sm">
                    {(() => {
                      const v = payload[0].value as number;
                      if (v >= 1000000) return `£${(v / 1000000).toFixed(2)}M`;
                      if (v >= 1000) return `£${(v / 1000).toFixed(1)}K`;
                      return `£${v.toFixed(2)}`;
                    })()}
                  </div>
                </div>
              );
            }}
          />
          <Line
            type="monotone"
            dataKey="equity"
            stroke="#22c55e"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
