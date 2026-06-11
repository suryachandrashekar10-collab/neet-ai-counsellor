"use client";

import { useState, useMemo } from "react";
import { type PredictResponse, type College, SECTION_LABEL, CATEGORY_LABELS } from "@/lib/api";
import FilterBar, { type Filters, DEFAULT_FILTERS } from "@/components/FilterBar";

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

const ROUND_CLEARED: Record<string, (c: College) => boolean> = {
  R1: (c) => c.r1_cleared,
  R2: (c) => c.r2_cleared,
  R3: (c) => c.r3_cleared,
  R4: (c) => c.r4_cleared,
};

function RoundBadges({ c }: { c: College }) {
  return (
    <div className="flex gap-1">
      {["R1", "R2", "R3", "R4"].map((r) => {
        const hasData = r in c.rounds;
        const cleared = ROUND_CLEARED[r]?.(c) ?? false;
        if (!hasData) return <span key={r} className="text-xs text-slate-700">{r}</span>;
        return (
          <span
            key={r}
            className={`text-xs px-1.5 py-0.5 rounded font-medium ${
              cleared
                ? "bg-emerald-900/60 text-emerald-300"
                : "bg-red-900/40 text-red-400"
            }`}
          >
            {cleared ? "✓" : "✗"}{r}
          </span>
        );
      })}
    </div>
  );
}

function CollegeRow({ c }: { c: College }) {
  const [expanded, setExpanded] = useState(false);

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
        <td className="px-4 py-3 text-xs text-slate-300">
          {CATEGORY_LABELS[c.category] ?? c.category}{c.women_quota ? " (W)" : ""}
        </td>
        <td className="px-4 py-3 text-sm text-slate-300 tabular-nums">{c.r1_closing.toLocaleString()}</td>
        <td className="px-4 py-3"><RoundBadges c={c} /></td>
        <td className="px-4 py-3"><ProbBar value={c.final_probability} /></td>
        <td className="px-4 py-3 text-xs text-slate-400">
          {c.fill_rate > 0 ? `${Math.round(c.fill_rate * 100)}%` : "—"}
        </td>
        <td className="px-4 py-3 text-slate-500 text-xs">{expanded ? "▲" : "▼"}</td>
      </tr>
      {expanded && (
        <tr className="bg-slate-800/50">
          <td colSpan={8} className="px-6 py-3">
            <div className="flex gap-6 flex-wrap">
              {["R1", "R2", "R3", "R4"].filter((r) => r in c.rounds).map((r) => {
                const d = c.rounds[r];
                const cleared = ROUND_CLEARED[r]?.(c) ?? false;
                return (
                  <div key={r} className="text-xs">
                    <span className={`font-semibold ${cleared ? "text-emerald-400" : "text-red-400"}`}>
                      {r} {cleared ? "✓ You qualify" : "✗ Rank too high"}
                    </span>
                    <div className="text-slate-300 tabular-nums mt-0.5">
                      Closing: {d.closing_rank.toLocaleString()}
                    </div>
                    <div className="text-slate-500">Filled: {d.seats_filled} seats</div>
                  </div>
                );
              })}
              <div className="text-xs border-l border-slate-700 pl-4">
                <span className="text-slate-500 font-medium">Capacity</span>
                <div className="text-slate-300">{c.total_seats} total seats</div>
                <div className="text-slate-500">Fill rate: {Math.round(c.fill_rate * 100)}%</div>
                {c.earliest_round && (
                  <div className="mt-1 text-amber-400 font-medium">
                    Earliest entry: {c.earliest_round}
                  </div>
                )}
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
                <th className="px-4 py-2 text-xs font-medium text-slate-500">Category</th>
                <th className="px-4 py-2 text-xs font-medium text-slate-500">R1 Closing</th>
                <th className="px-4 py-2 text-xs font-medium text-slate-500">Rounds (R1–R4)</th>
                <th className="px-4 py-2 text-xs font-medium text-slate-500">Probability</th>
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

function TopPicks({ result }: { result: PredictResponse }) {
  // Best 5: prefer Moderate (realistic reach), then Safe with highest probability
  const allColleges = [...result.moderate, ...result.safe, ...result.aggressive]
    .sort((a, b) => b.final_probability - a.final_probability)
    .slice(0, 5);

  if (allColleges.length === 0) return null;

  return (
    <div className="bg-slate-800/60 border border-blue-800/40 rounded-xl p-4">
      <h3 className="text-xs font-semibold text-blue-400 uppercase tracking-wider mb-3">
        Top 5 Best Bets
      </h3>
      <div className="grid grid-cols-1 sm:grid-cols-5 gap-2">
        {allColleges.map((c, i) => {
          const s = TIER_STYLES[c.tier];
          return (
            <div key={`${c.college_code}-${i}`} className="bg-slate-900/70 rounded-lg p-3 space-y-1.5">
              <div className="flex items-center justify-between">
                <span className={`text-xs border rounded px-1.5 py-0.5 ${s.badge}`}>{c.tier}</span>
                <span className={`text-sm font-bold ${PROB_COLOR(c.final_probability)}`}>
                  {Math.round(c.final_probability * 100)}%
                </span>
              </div>
              <p className="text-xs font-medium text-slate-200 leading-tight">{c.college_name}</p>
              <p className="text-xs text-slate-500">{SECTION_LABEL[c.section] ?? c.section}</p>
              <div className="flex gap-1 flex-wrap">
                {["R1","R2","R3","R4"].filter(r => r in c.rounds).map(r => {
                  const cleared = ROUND_CLEARED[r]?.(c) ?? false;
                  return (
                    <span key={r} className={`text-xs px-1 rounded ${cleared ? "text-emerald-400" : "text-red-500"}`}>
                      {cleared ? "✓" : "✗"}{r}
                    </span>
                  );
                })}
              </div>
              {c.earliest_round && (
                <p className="text-xs text-amber-400">Entry from {c.earliest_round}</p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function applyFilters(colleges: College[], filters: Filters): College[] {
  let list = [...colleges];

  // Course filter
  if (filters.course !== "ALL") {
    list = list.filter((c) => c.section.includes(filters.course));
  }

  // College type filter
  if (filters.collegeType !== "ALL") {
    list = list.filter((c) => c.section.startsWith(filters.collegeType));
  }

  // Sort
  list.sort((a, b) => {
    switch (filters.sortBy) {
      case "r1_closing":    return a.r1_closing - b.r1_closing;
      case "fill_rate":     return b.fill_rate - a.fill_rate;
      case "name":          return a.college_name.localeCompare(b.college_name);
      default:              return b.final_probability - a.final_probability;
    }
  });

  return list;
}

export default function ResultsPanel({ result, onReset }: Props) {
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const catLabel = CATEGORY_LABELS[result.category] ?? result.category;

  const filteredSafe       = useMemo(() => applyFilters(result.safe,       filters), [result.safe,       filters]);
  const filteredModerate   = useMemo(() => applyFilters(result.moderate,   filters), [result.moderate,   filters]);
  const filteredAggressive = useMemo(() => applyFilters(result.aggressive, filters), [result.aggressive, filters]);
  const totalShown = filteredSafe.length + filteredModerate.length + filteredAggressive.length;

  return (
    <div className="space-y-4">
      {/* Summary bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-800 border border-slate-700 rounded-xl px-5 py-4">
        <div>
          <p className="text-sm text-slate-400">
            Results for AIR <span className="text-white font-semibold">{result.student_air.toLocaleString()}</span>
            {" · "}<span className="text-white font-semibold">{catLabel}</span>
            {result.women_quota && <span className="text-pink-400"> · Women&apos;s quota</span>}
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

      {/* Top 5 best bets */}
      <TopPicks result={result} />

      {/* Filter bar */}
      <FilterBar
        filters={filters}
        onChange={setFilters}
        totalShown={totalShown}
        totalAll={result.total_options}
      />

      {/* Tier sections */}
      <TierSection title="Safe"       colleges={filteredSafe}       defaultOpen={true} />
      <TierSection title="Moderate"   colleges={filteredModerate}   defaultOpen={true} />
      <TierSection title="Aggressive" colleges={filteredAggressive} defaultOpen={false} />

      {totalShown === 0 && (
        <div className="text-center py-12 text-slate-500">
          No colleges match your filters. Try changing Course or Type.
        </div>
      )}
    </div>
  );
}
