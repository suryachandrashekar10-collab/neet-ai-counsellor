"use client";

import { useState } from "react";
import { type PredictResponse, type College, SECTION_LABEL } from "@/lib/api";

interface Props {
  result: PredictResponse;
  onReset: () => void;
}

const TIER_STYLES = {
  Safe:       { badge: "bg-emerald-900/60 text-emerald-300 border-emerald-700", dot: "bg-emerald-400" },
  Moderate:   { badge: "bg-yellow-900/60 text-yellow-300 border-yellow-700",   dot: "bg-yellow-400" },
  Aggressive: { badge: "bg-red-900/60 text-red-300 border-red-700",            dot: "bg-red-400" },
};

const PROB_COLOR = (p: number) =>
  p >= 0.8 ? "text-emerald-400" : p >= 0.5 ? "text-yellow-400" : "text-red-400";

function ProbBar({ value }: { value: number }) {
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 bg-slate-700 rounded-full h-1.5">
        <div
          className={`h-1.5 rounded-full ${
            value >= 0.8 ? "bg-emerald-400" : value >= 0.5 ? "bg-yellow-400" : "bg-red-400"
          }`}
          style={{ width: `${Math.round(value * 100)}%` }}
        />
      </div>
      <span className={`text-xs font-medium ${PROB_COLOR(value)}`}>
        {Math.round(value * 100)}%
      </span>
    </div>
  );
}

function CollegeRow({ c }: { c: College }) {
  const [expanded, setExpanded] = useState(false);
  const roundKeys = ["R1", "R2", "R3", "R4"].filter((r) => r in c.rounds);

  return (
    <>
      <tr
        className="border-b border-slate-700/50 hover:bg-slate-700/30 cursor-pointer transition-colors"
        onClick={() => setExpanded((v) => !v)}
      >
        <td className="px-4 py-3 text-xs text-slate-400 font-mono">{c.college_code}</td>
        <td className="px-4 py-3">
          <div className="text-sm font-medium text-slate-100">{c.college_name}</div>
          <div className="text-xs text-slate-500 mt-0.5">{SECTION_LABEL[c.section] ?? c.section}</div>
        </td>
        <td className="px-4 py-3 text-xs text-slate-300">{c.category}{c.women_quota ? " (W)" : ""}</td>
        <td className="px-4 py-3 text-sm text-slate-300 tabular-nums">{c.r1_closing.toLocaleString()}</td>
        <td className="px-4 py-3">
          <ProbBar value={c.final_probability} />
        </td>
        <td className="px-4 py-3 text-xs text-slate-400">
          {c.seat_movement > 0 ? (
            <span className="text-emerald-400">+{c.seat_movement.toLocaleString()}</span>
          ) : "—"}
        </td>
        <td className="px-4 py-3 text-xs text-slate-400">
          {c.fill_rate > 0 ? `${Math.round(c.fill_rate * 100)}%` : "—"}
        </td>
        <td className="px-4 py-3 text-slate-500 text-xs">{expanded ? "▲" : "▼"}</td>
      </tr>
      {expanded && (
        <tr className="bg-slate-800/50">
          <td colSpan={8} className="px-6 py-3">
            <div className="flex gap-6 flex-wrap">
              {roundKeys.map((r) => {
                const d = c.rounds[r];
                return (
                  <div key={r} className="text-xs">
                    <span className="text-slate-500 font-medium">{r}</span>
                    <div className="text-slate-300 tabular-nums">Closing: {d.closing_rank.toLocaleString()}</div>
                    <div className="text-slate-500">Filled: {d.seats_filled} seats</div>
                  </div>
                );
              })}
              <div className="text-xs">
                <span className="text-slate-500 font-medium">Capacity</span>
                <div className="text-slate-300">{c.total_seats} seats</div>
                <div className="text-slate-500">Round prob: {Math.round(c.round_probability * 100)}%</div>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

function TierSection({ title, colleges, defaultOpen }: { title: string; colleges: College[]; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen ?? false);
  if (colleges.length === 0) return null;
  const tier = colleges[0].tier as keyof typeof TIER_STYLES;
  const s = TIER_STYLES[tier];

  return (
    <div className="border border-slate-700 rounded-xl overflow-hidden">
      <button
        className="w-full flex items-center justify-between px-5 py-4 bg-slate-800 hover:bg-slate-700/60 transition-colors"
        onClick={() => setOpen((v) => !v)}
      >
        <div className="flex items-center gap-3">
          <span className={`w-2 h-2 rounded-full ${s.dot}`} />
          <span className="font-semibold text-slate-100">{title}</span>
          <span className={`text-xs border rounded px-2 py-0.5 ${s.badge}`}>
            {colleges.length} college{colleges.length !== 1 ? "s" : ""}
          </span>
        </div>
        <span className="text-slate-500 text-xs">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-slate-700 bg-slate-800/50">
                <th className="px-4 py-2 text-xs font-medium text-slate-500">Code</th>
                <th className="px-4 py-2 text-xs font-medium text-slate-500">College</th>
                <th className="px-4 py-2 text-xs font-medium text-slate-500">Cat</th>
                <th className="px-4 py-2 text-xs font-medium text-slate-500">R1 Closing</th>
                <th className="px-4 py-2 text-xs font-medium text-slate-500">Probability</th>
                <th className="px-4 py-2 text-xs font-medium text-slate-500">Movement</th>
                <th className="px-4 py-2 text-xs font-medium text-slate-500">Fill Rate</th>
                <th className="px-4 py-2 text-xs font-medium text-slate-500"></th>
              </tr>
            </thead>
            <tbody>
              {colleges.map((c) => (
                <CollegeRow key={`${c.college_code}-${c.category}-${c.women_quota}`} c={c} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function ResultsPanel({ result, onReset }: Props) {
  return (
    <div className="space-y-4">
      {/* Summary bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-800 border border-slate-700 rounded-xl px-5 py-4">
        <div>
          <p className="text-sm text-slate-400">
            Results for AIR <span className="text-white font-semibold">{result.student_air.toLocaleString()}</span>
            {" · "}<span className="text-white font-semibold">{result.category}</span>
            {result.women_quota && <span className="text-pink-400"> (Women)</span>}
          </p>
          <p className="text-xs text-slate-500 mt-0.5">
            {result.total_options} colleges found · {result.safe_count} safe · {result.moderate_count} moderate · {result.aggressive_count} aggressive
          </p>
        </div>
        <button
          onClick={onReset}
          className="text-xs text-slate-400 hover:text-white border border-slate-600 hover:border-slate-400 rounded-lg px-3 py-1.5 transition-colors"
        >
          New search
        </button>
      </div>

      {/* Tier sections — Safe open by default */}
      <TierSection title="Safe"       colleges={result.safe}       defaultOpen={true} />
      <TierSection title="Moderate"   colleges={result.moderate}   defaultOpen={true} />
      <TierSection title="Aggressive" colleges={result.aggressive} defaultOpen={false} />

      {result.total_options === 0 && (
        <div className="text-center py-12 text-slate-500">
          No colleges found in range for AIR {result.student_air.toLocaleString()} · {result.category}
        </div>
      )}
    </div>
  );
}
