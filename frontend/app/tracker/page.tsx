"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  fetchColleges, fetchCutoffs, CATEGORIES, CATEGORY_LABELS,
  type CollegeListItem, type CutoffRow,
} from "@/lib/api";
import CollegeSearch from "@/components/CollegeSearch";

const ROUNDS = ["R1", "R2", "R3", "R4", "R5"];

interface CollegeResult {
  college: CollegeListItem;
  cutoffs: CutoffRow[];
  loading: boolean;
  error: boolean;
}

function roundResult(cutoffs: CutoffRow[], round: string, category: string, womenQuota: boolean, air: number) {
  // Find best matching cutoff row: exact category + women_quota + round
  const rows = cutoffs.filter(
    (c) => c.round === round && c.category === category && c.women_quota === womenQuota
  );
  // Also check OPEN category rows for this round if student isn't OPEN
  const openRows = category !== "OPEN"
    ? cutoffs.filter((c) => c.round === round && c.category === "OPEN" && c.women_quota === womenQuota)
    : [];

  const allRows = [...rows, ...openRows];
  if (allRows.length === 0) return { status: "no-data" as const, closing: null };

  // Best closing rank in this round (highest AIR admitted = most accessible seat)
  const bestClosing = Math.max(...allRows.map((r) => r.closing_rank));
  const cleared = air <= bestClosing;

  return { status: cleared ? ("cleared" as const) : ("not-cleared" as const), closing: bestClosing };
}

export default function TrackerPage() {
  const [colleges, setColleges] = useState<CollegeListItem[]>([]);
  const [colLoading, setColLoading] = useState(true);

  const [selected, setSelected] = useState<CollegeListItem[]>([]);
  const [results, setResults] = useState<CollegeResult[]>([]);

  const [air, setAir] = useState("");
  const [category, setCategory] = useState("OPEN");
  const [womenQuota, setWomenQuota] = useState(false);
  const [checked, setChecked] = useState(false);

  // Load college list once
  useEffect(() => {
    fetchColleges()
      .then((data) => setColleges(data.sort((a, b) => a.name.localeCompare(b.name))))
      .finally(() => setColLoading(false));
  }, []);

  function addCollege(c: CollegeListItem) {
    setSelected((prev) => [...prev, c]);
    setChecked(false);
  }

  function removeCollege(code: string) {
    setSelected((prev) => prev.filter((c) => c.code !== code));
    setResults((prev) => prev.filter((r) => r.college.code !== code));
    setChecked(false);
  }

  async function handleCheck() {
    const airNum = parseInt(air, 10);
    if (!airNum || airNum < 1 || selected.length === 0) return;

    // Init results with loading state
    setResults(selected.map((college) => ({ college, cutoffs: [], loading: true, error: false })));
    setChecked(true);

    // Fetch cutoffs for all selected colleges in parallel
    const fetched = await Promise.all(
      selected.map(async (college) => {
        try {
          const cutoffs = await fetchCutoffs(college.code);
          return { college, cutoffs, loading: false, error: false };
        } catch {
          return { college, cutoffs: [], loading: false, error: true };
        }
      })
    );
    setResults(fetched);
  }

  const airNum = parseInt(air, 10) || 0;
  const canCheck = airNum > 0 && selected.length > 0;

  return (
    <main className="min-h-screen bg-slate-900 text-slate-100">
      {/* Header */}
      <header className="border-b border-slate-700 bg-slate-900/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold text-sm">MH</div>
          <div className="flex-1">
            <h1 className="text-base font-semibold leading-tight">NEET Maharashtra CAP Counsellor</h1>
            <p className="text-xs text-slate-400">Predict your college admission chances · 2025 data</p>
          </div>
          <Link href="/" className="text-xs text-slate-400 hover:text-white transition-colors border border-slate-700 rounded-lg px-3 py-1.5">
            ← Predict Colleges
          </Link>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
        {/* Title */}
        <div>
          <h2 className="text-2xl font-bold text-white">College Tracker</h2>
          <p className="text-slate-400 text-sm mt-1">
            Pick up to 5 colleges and check which CAP round you'd get them in.
          </p>
        </div>

        {/* Input card */}
        <div className="bg-slate-800 border border-slate-700 rounded-2xl p-6 space-y-5">

          {/* AIR + Category row */}
          <div className="flex flex-col sm:flex-row gap-4 items-end">
            <div className="flex-1">
              <label className="block text-xs font-medium text-slate-400 mb-1.5">Your NEET AIR</label>
              <input
                type="number" min={1} max={2000000}
                value={air} onChange={(e) => { setAir(e.target.value); setChecked(false); }}
                placeholder="e.g. 25000"
                className="w-full bg-slate-900 border border-slate-600 rounded-lg px-4 py-2.5 text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              />
            </div>

            <div className="w-52">
              <label className="block text-xs font-medium text-slate-400 mb-1.5">Category</label>
              <select
                value={category} onChange={(e) => { setCategory(e.target.value); setChecked(false); }}
                className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              >
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>{CATEGORY_LABELS[c] ?? c}</option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2 pb-2.5">
              <button
                type="button" role="switch" aria-checked={womenQuota}
                onClick={() => { setWomenQuota((v) => !v); setChecked(false); }}
                className={`relative w-10 h-5 rounded-full transition-colors ${womenQuota ? "bg-pink-500" : "bg-slate-600"}`}
              >
                <span className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${womenQuota ? "translate-x-5" : ""}`} />
              </button>
              <span className="text-xs text-slate-400 cursor-pointer select-none" onClick={() => { setWomenQuota((v) => !v); setChecked(false); }}>
                Women&apos;s quota
              </span>
            </div>
          </div>

          {/* College search */}
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">
              Choose Colleges {colLoading ? <span className="text-slate-500">(loading…)</span> : <span className="text-slate-500">({colleges.length} available)</span>}
            </label>
            <CollegeSearch
              colleges={colleges}
              selected={selected}
              onAdd={addCollege}
              onRemove={removeCollege}
            />
          </div>

          {/* Check button */}
          <button
            onClick={handleCheck}
            disabled={!canCheck}
            className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500 text-white font-medium px-6 py-3 rounded-xl transition-colors text-sm"
          >
            Check My Chances
          </button>
        </div>

        {/* Results table */}
        {checked && results.length > 0 && (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <h3 className="text-base font-semibold text-white">Round-by-Round Chances</h3>
              <span className="text-xs text-slate-400">AIR {airNum.toLocaleString()} · {CATEGORY_LABELS[category] ?? category}{womenQuota ? " · Women's quota" : ""}</span>
            </div>

            {/* Legend */}
            <div className="flex flex-wrap gap-3 text-xs">
              <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm bg-emerald-500 inline-block" /> You clear this round</span>
              <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm bg-red-800 inline-block" /> Rank too high</span>
              <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm bg-slate-700 inline-block" /> No data for this round</span>
            </div>

            <div className="overflow-x-auto rounded-xl border border-slate-700">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-slate-800 border-b border-slate-700">
                    <th className="text-left px-4 py-3 text-xs font-medium text-slate-400 w-8">#</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-slate-400">College</th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-slate-400 hidden sm:table-cell">Type</th>
                    {ROUNDS.map((r) => (
                      <th key={r} className="text-center px-3 py-3 text-xs font-medium text-slate-400 w-16">{r}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700/50">
                  {results.map((res, idx) => (
                    <tr key={res.college.code} className="bg-slate-900/40 hover:bg-slate-800/60 transition-colors">
                      <td className="px-4 py-3 text-slate-500 text-xs">{idx + 1}</td>
                      <td className="px-4 py-3">
                        <div className="font-medium text-white text-sm leading-tight">{res.college.name}</div>
                        {res.error && <div className="text-xs text-red-400 mt-0.5">Failed to load data</div>}
                        {res.loading && <div className="text-xs text-slate-500 mt-0.5">Loading…</div>}
                        {!res.loading && !res.error && (
                          <EarliestRoundBadge cutoffs={res.cutoffs} category={category} womenQuota={womenQuota} air={airNum} />
                        )}
                      </td>
                      <td className="px-4 py-3 hidden sm:table-cell">
                        <span className="text-xs text-slate-400">
                          {res.college.section.replace("GOVT_", "Govt ").replace("PVT_", "Pvt ").replace("MIN_", "Min ")}
                        </span>
                      </td>
                      {ROUNDS.map((round) => (
                        <td key={round} className="px-2 py-3 text-center">
                          {res.loading ? (
                            <span className="inline-block w-8 h-6 bg-slate-700 rounded animate-pulse" />
                          ) : res.error ? (
                            <span className="text-slate-600 text-xs">—</span>
                          ) : (
                            <RoundCell cutoffs={res.cutoffs} round={round} category={category} womenQuota={womenQuota} air={airNum} />
                          )}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <p className="text-xs text-slate-500">
              Closing ranks shown are from 2025 CAP data. Actual 2026 cutoffs may vary.
            </p>
          </div>
        )}
      </div>
    </main>
  );
}

function RoundCell({ cutoffs, round, category, womenQuota, air }: {
  cutoffs: CutoffRow[]; round: string; category: string; womenQuota: boolean; air: number;
}) {
  const { status, closing } = roundResult(cutoffs, round, category, womenQuota, air);

  if (status === "no-data") {
    return <span className="inline-flex items-center justify-center w-8 h-7 rounded bg-slate-700/50 text-slate-600 text-xs">—</span>;
  }

  const cleared = status === "cleared";
  return (
    <span className={`inline-flex flex-col items-center justify-center w-full px-1 py-1 rounded text-xs leading-tight ${
      cleared ? "bg-emerald-900/60 text-emerald-300 border border-emerald-700/50" : "bg-red-900/30 text-red-400 border border-red-800/30"
    }`}>
      <span>{cleared ? "✓" : "✗"}</span>
      {closing && <span className="text-[10px] opacity-70">{(closing / 1000).toFixed(0)}k</span>}
    </span>
  );
}

function EarliestRoundBadge({ cutoffs, category, womenQuota, air }: {
  cutoffs: CutoffRow[]; category: string; womenQuota: boolean; air: number;
}) {
  const earliest = ROUNDS.find((r) => roundResult(cutoffs, r, category, womenQuota, air).status === "cleared");
  if (!earliest) {
    return <div className="text-xs text-red-400 mt-0.5">Not clearing any round</div>;
  }
  return (
    <div className="text-xs text-emerald-400 mt-0.5">Earliest: <span className="font-semibold">{earliest}</span></div>
  );
}
