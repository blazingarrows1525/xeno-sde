"use client";

import {
  Area,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Line,
  LabelList,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { CalibrationPoint, ChannelRoi, FunnelStat } from "@/lib/types";

const tooltipStyle = {
  background: "rgba(12, 13, 13, 0.92)",
  border: "1px solid rgba(255, 255, 255, 0.08)",
  borderRadius: 10,
  color: "#e2e8f0",
  fontSize: 12,
  boxShadow: "0 12px 32px -12px rgba(0, 0, 0, 0.6)",
  backdropFilter: "blur(8px)",
};

export function FunnelChart({ funnel }: { funnel: FunnelStat }) {
  const data = [
    { stage: "Sent", value: funnel.sent },
    { stage: "Delivered", value: funnel.delivered },
    { stage: "Opened", value: funnel.opened },
    { stage: "Read", value: funnel.read },
    { stage: "Clicked", value: funnel.clicked },
    { stage: "Converted", value: funnel.converted },
  ];
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} layout="vertical" margin={{ left: 24, right: 28, top: 8, bottom: 8 }}>
        <defs>
          <linearGradient id="funnelFill" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#0d9488" />
            <stop offset="100%" stopColor="#34d399" />
          </linearGradient>
        </defs>
        <CartesianGrid horizontal={false} stroke="#27272a" />
        <XAxis type="number" tick={{ fill: "#64748b", fontSize: 12 }} />
        <YAxis type="category" dataKey="stage" width={80} tick={{ fill: "#94a3b8", fontSize: 12 }} />
        <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "#27272a55" }} />
        <Bar dataKey="value" radius={[0, 4, 4, 0]} fill="url(#funnelFill)" animationDuration={1100}>
          <LabelList dataKey="value" position="right" fill="#94a3b8" fontSize={11} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function ChannelRoiChart({ data }: { data: ChannelRoi[] }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ left: 8, right: 16, top: 20, bottom: 8 }}>
        <defs>
          <linearGradient id="barTop" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#2dd4bf" />
            <stop offset="100%" stopColor="#0f766e" />
          </linearGradient>
          <linearGradient id="barBest" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#6ee7b7" />
            <stop offset="100%" stopColor="#059669" />
          </linearGradient>
        </defs>
        <CartesianGrid vertical={false} stroke="#27272a" />
        <XAxis dataKey="channel" tick={{ fill: "#94a3b8", fontSize: 12 }} />
        <YAxis tick={{ fill: "#64748b", fontSize: 12 }} />
        <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "#27272a55" }} />
        <Bar dataKey="roas" radius={[6, 6, 0, 0]} animationDuration={1100}>
          {data.map((entry, i) => (
            <Cell key={entry.channel} fill={i === 0 ? "url(#barBest)" : "url(#barTop)"} />
          ))}
          <LabelList
            dataKey="roas"
            position="top"
            formatter={(v) => `${Number(v).toFixed(1)}×`}
            fill="#94a3b8"
            fontSize={11}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function CalibrationChart({ points }: { points: CalibrationPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <ComposedChart data={points} margin={{ left: 8, right: 16, top: 8, bottom: 8 }}>
        <defs>
          <linearGradient id="actualFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#22c55e" stopOpacity={0.35} />
            <stop offset="100%" stopColor="#22c55e" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="#27272a" strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="campaign" tick={{ fill: "#94a3b8", fontSize: 11 }} tickMargin={8} />
        <YAxis tick={{ fill: "#64748b", fontSize: 12 }} domain={[0, "dataMax + 1"]} />
        <Tooltip contentStyle={tooltipStyle} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Area
          type="monotone"
          dataKey="actualRoas"
          name="Actual"
          stroke="#22c55e"
          strokeWidth={2.5}
          fill="url(#actualFill)"
          dot={{ r: 3, fill: "#22c55e" }}
          activeDot={{ r: 5 }}
          animationDuration={1400}
        />
        <Line
          type="monotone"
          dataKey="predictedRoas"
          name="Predicted"
          stroke="#38bdf8"
          strokeWidth={2}
          strokeDasharray="5 4"
          dot={false}
          animationDuration={1400}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
