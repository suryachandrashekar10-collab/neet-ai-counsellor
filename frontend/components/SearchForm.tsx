"use client";

import { useState } from "react";
import { CATEGORIES, CATEGORY_LABELS } from "@/lib/api";

interface Props {
  onSearch: (air: number, category: string, womenQuota: boolean) => void;
  loading: boolean;
}

export default function SearchForm({ onSearch, loading }: Props) {
  const [air, setAir] = useState("");
  const [category, setCategory] = useState("OPEN");
  const [womenQuota, setWomenQuota] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const airNum = parseInt(air, 10);
    if (!airNum || airNum < 1) return;
    onSearch(airNum, category, womenQuota);
  }

  return (
    <form onSubmit={handleSubmit} className="bg-slate-800 border border-slate-700 rounded-2xl p-6 space-y-4">

      {/* Row 1 — main inputs */}
      <div className="flex flex-col sm:flex-row gap-4 items-end">
        {/* AIR */}
        <div className="flex-1">
          <label className="block text-xs font-medium text-slate-400 mb-1.5">
            NEET All India Rank (AIR)
          </label>
          <input
            type="number" min={1} max={2000000}
            value={air} onChange={(e) => setAir(e.target.value)}
            placeholder="e.g. 25000" required
            className="w-full bg-slate-900 border border-slate-600 rounded-lg px-4 py-2.5 text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
          />
        </div>

        {/* Category */}
        <div className="w-52">
          <label className="block text-xs font-medium text-slate-400 mb-1.5">Category</label>
          <select
            value={category} onChange={(e) => setCategory(e.target.value)}
            className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
          >
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>{CATEGORY_LABELS[c] ?? c}</option>
            ))}
          </select>
        </div>

        {/* Women quota */}
        <div className="flex items-center gap-2 pb-2.5">
          <button
            type="button" role="switch" aria-checked={womenQuota}
            onClick={() => setWomenQuota((v) => !v)}
            className={`relative w-10 h-5 rounded-full transition-colors ${womenQuota ? "bg-pink-500" : "bg-slate-600"}`}
          >
            <span className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${womenQuota ? "translate-x-5" : ""}`} />
          </button>
          <span className="text-xs text-slate-400 cursor-pointer select-none" onClick={() => setWomenQuota((v) => !v)}>
            Women&apos;s quota
          </span>
        </div>

        {/* Submit */}
        <button
          type="submit" disabled={loading || !air}
          className="bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500 text-white font-medium px-6 py-2.5 rounded-lg transition-colors text-sm whitespace-nowrap"
        >
          {loading ? "Searching…" : "Find Colleges"}
        </button>
      </div>

      {/* Advanced toggle */}
      <button
        type="button"
        onClick={() => setShowAdvanced((v) => !v)}
        className="text-xs text-slate-500 hover:text-slate-300 transition-colors flex items-center gap-1"
      >
        {showAdvanced ? "▲" : "▼"} Advanced options
      </button>

      {showAdvanced && (
        <div className="border-t border-slate-700 pt-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Quota type info */}
          <div className="bg-slate-900/60 rounded-lg p-3 text-xs text-slate-400 col-span-full">
            <p className="font-medium text-slate-300 mb-1">About Quota Types</p>
            <p><span className="text-blue-400">State Quota (CAP)</span> — Results shown above are for Maharashtra state quota seats allotted through CAP rounds R1–R4.</p>
            <p className="mt-1"><span className="text-yellow-400">Management Quota</span> — Direct admission by college management (~15% seats). Not through CAP — contact college directly.</p>
            <p className="mt-1"><span className="text-purple-400">NRI / Minority Quota</span> — Separate process. Check individual college prospectus.</p>
          </div>

          {/* Domicile note */}
          <div className="bg-amber-950/40 border border-amber-800/40 rounded-lg p-3 text-xs text-amber-300 col-span-full">
            <span className="font-medium">Maharashtra Domicile Required</span> — State quota seats are only for students with Maharashtra domicile or Maharashtra-board education.
            All India Quota (AIQ) seats go through MCC counselling separately.
          </div>
        </div>
      )}
    </form>
  );
}
