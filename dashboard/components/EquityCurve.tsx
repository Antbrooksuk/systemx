"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
  Area,
  AreaChart,
} from "recharts";
import { EquityPoint } from "../lib/types";

interface EVData {
  trade: number;
  ev: number;
  upper: number;
  lower: number;
}

interface EquityCurveProps {
  data: EquityPoint[];
  evData?: EVData[];
  showEV?: boolean;
}

export function EquityCurve({ data, evData, showEV = false }: EquityCurveProps) {
  if (!data || data.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-muted text-xs">No data yet</div>
      </div>
    );
  }

  const chartData = data
    .slice()
    .sort((a, b) =>
      a.date && b.date
        ? new Date(a.date).getTime() - new Date(b.date).getTime()
        : 0,
    )
    .map((point, idx) => ({ ...point, idx }));

  const combinedData = chartData.map(point => {
    const evPoint = evData?.find(ev => ev.trade === point.trade);
    return {
      ...point,
      ev: evPoint?.ev,
      upper: evPoint?.upper,
      lower: evPoint?.lower,
    };
  });

  return (
    <div className="h-full w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={combinedData} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
          <XAxis
            dataKey="date"
            stroke="#737373"
            fontSize={9}
            tickFormatter={(v) => {
              if (!v) return "";
              const d = new Date(v);
              return `${d.getMonth() + 1}/${d.getDate()}`;
            }}
          />
          <YAxis
            stroke="#737373"
            fontSize={9}
            tickFormatter={(v) => {
              if (v >= 1000000) return `£${(v / 1000000).toFixed(1)}M`;
              if (v >= 1000) return `£${(v / 1000).toFixed(0)}K`;
              return `£${v.toFixed(0)}`;
            }}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const point = payload[0].payload as any;
              const dateStr = point.date
                ? new Date(point.date).toLocaleDateString()
                : "Start";
              return (
                <div className="bg-[#141414] border border-[#262626] rounded px-3 py-2">
                  <div className="text-[#737373] text-xs mb-1">{dateStr}</div>
                  <div className="text-white text-sm">
                    {(() => {
                      const v = point.equity;
                      if (v >= 1000000) return `£${(v / 1000000).toFixed(2)}M`;
                      if (v >= 1000) return `£${(v / 1000).toFixed(1)}K`;
                      return `£${v.toFixed(2)}`;
                    })()}
                  </div>
                  {showEV && point.ev && (
                    <>
                      <div className="text-green-400 text-xs mt-1">EV: £{point.ev.toFixed(2)}</div>
                      {point.upper && <div className="text-blue-300 text-xs">Upper: £{point.upper.toFixed(2)}</div>}
                      {point.lower && <div className="text-blue-300 text-xs">Lower: £{point.lower.toFixed(2)}</div>}
                    </>
                  )}
                </div>
              );
            }}
          />
          {showEV && evData && (
            <>
              <Area
                type="monotone"
                dataKey="upper"
                stroke="none"
                fill="#3b82f6"
                fillOpacity={0.1}
                isAnimationActive={false}
              />
              <Area
                type="monotone"
                dataKey="lower"
                stroke="none"
                fill="#3b82f6"
                fillOpacity={0.05}
                isAnimationActive={false}
              />
              <Line
                type="monotone"
                dataKey="ev"
                stroke="#22c55e"
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={false}
                isAnimationActive={false}
              />
            </>
          )}
          <Area
            type="monotone"
            dataKey="equity"
            stroke="#22c55e"
            fill="#22c55e"
            fillOpacity={0.1}
            strokeWidth={2}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
