"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { CalibrationPoint, ChannelRoi, FunnelStat } from "@/lib/types";

const tooltipStyle = {
  background: "#0f172a",
  border: "1px solid #1e293b",
  borderRadius: 8,
  color: "#e2e8f0",
  fontSize: 12,
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
      <BarChart data={data} layout="vertical" margin={{ left: 24, right: 16, top: 8, bottom: 8 }}>
        <CartesianGrid horizontal={false} stroke="#1e293b" />
        <XAxis type="number" tick={{ fill: "#64748b", fontSize: 12 }} />
        <YAxis type="category" dataKey="stage" width={80} tick={{ fill: "#94a3b8", fontSize: 12 }} />
        <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "#1e293b55" }} />
        <Bar dataKey="value" radius={[0, 4, 4, 0]} fill="#6366f1" />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function ChannelRoiChart({ data }: { data: ChannelRoi[] }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ left: 8, right: 16, top: 8, bottom: 8 }}>
        <CartesianGrid vertical={false} stroke="#1e293b" />
        <XAxis dataKey="channel" tick={{ fill: "#94a3b8", fontSize: 12 }} />
        <YAxis tick={{ fill: "#64748b", fontSize: 12 }} />
        <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "#1e293b55" }} />
        <Bar dataKey="roas" radius={[4, 4, 0, 0]}>
          {data.map((entry, i) => (
            <Cell key={entry.channel} fill={i === 0 ? "#22c55e" : "#6366f1"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function CalibrationChart({ points }: { points: CalibrationPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={points} margin={{ left: 8, right: 16, top: 8, bottom: 8 }}>
        <CartesianGrid stroke="#1e293b" />
        <XAxis dataKey="campaign" tick={{ fill: "#94a3b8", fontSize: 12 }} />
        <YAxis tick={{ fill: "#64748b", fontSize: 12 }} />
        <Tooltip contentStyle={tooltipStyle} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Line type="monotone" dataKey="predictedRoas" name="Predicted" stroke="#a78bfa" strokeWidth={2} dot={false} />
        <Line type="monotone" dataKey="actualRoas" name="Actual" stroke="#22c55e" strokeWidth={2} dot={{ r: 3 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}
