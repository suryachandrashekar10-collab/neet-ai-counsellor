"use client";

import { useState } from "react";
import Link from "next/link";
import { predict, type PredictResponse } from "@/lib/api";
import SearchForm from "@/components/SearchForm";
import ResultsPanel from "@/components/ResultsPanel";

export default function Home() {
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSearch(air: number, category: string, womenQuota: boolean) {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await predict({ air, category, women_quota: womenQuota });
      setResult(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-900 text-slate-100">
      {/* Header */}
      <header className="border-b border-slate-700 bg-slate-900/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold text-sm">MH</div>
          <div className="flex-1">
            <h1 className="text-base font-semibold leading-tight">NEET Maharashtra CAP Counsellor</h1>
            <p className="text-xs text-slate-400">Predict your college admission chances · 2025 data</p>
          </div>
          <Link href="/tracker" className="text-xs text-slate-400 hover:text-white transition-colors border border-slate-700 rounded-lg px-3 py-1.5">
            College Tracker →
          </Link>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 py-8 space-y-8">
        {/* Hero */}
        {!result && !loading && (
          <div className="text-center pt-8 pb-4">
            <h2 className="text-3xl font-bold text-white mb-3">Find Your College</h2>
            <p className="text-slate-400 max-w-xl mx-auto text-sm leading-relaxed">
              Enter your NEET AIR and category to see which Maharashtra medical colleges
              you can get into — across all CAP rounds with probability scores.
            </p>
          </div>
        )}

        {/* Search Form */}
        <SearchForm onSearch={handleSearch} loading={loading} />

        {/* Error */}
        {error && (
          <div className="bg-red-900/40 border border-red-700 rounded-xl p-4 text-red-300 text-sm">
            {error}
          </div>
        )}

        {/* Scorecard upload placeholder — will use Claude Vision when API key available */}
        {!result && !loading && (
          <div className="border border-dashed border-slate-600 rounded-xl p-6 text-center">
            <div className="text-3xl mb-2">📄</div>
            <p className="text-slate-400 text-sm font-medium">
              Upload NEET Scorecard
              <span className="text-xs bg-slate-700 text-slate-400 rounded px-2 py-0.5 ml-2">Coming Soon</span>
            </p>
            <p className="text-slate-600 text-xs mt-1">
              Auto-fill AIR and category from your scorecard image using Claude Vision
            </p>
          </div>
        )}

        {/* Results */}
        {result && <ResultsPanel result={result} onReset={() => setResult(null)} />}
      </div>
    </main>
  );
}
