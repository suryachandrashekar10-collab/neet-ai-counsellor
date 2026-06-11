"use client";

import { useState, useRef, useEffect } from "react";
import type { CollegeListItem } from "@/lib/api";

interface Props {
  colleges: CollegeListItem[];
  selected: CollegeListItem[];
  onAdd: (college: CollegeListItem) => void;
  onRemove: (code: string) => void;
  maxSelections?: number;
}

export default function CollegeSearch({ colleges, selected, onAdd, onRemove, maxSelections = 5 }: Props) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const [highlighted, setHighlighted] = useState(0);

  const selectedCodes = new Set(selected.map((c) => c.code));

  // Filter + sort alphabetically, exclude already selected
  const filtered = colleges
    .filter((c) => {
      if (selectedCodes.has(c.code)) return false;
      if (!query.trim()) return true;
      const q = query.toLowerCase();
      return (
        c.name.toLowerCase().includes(q) ||
        c.code.toLowerCase().includes(q) ||
        c.section.toLowerCase().includes(q)
      );
    })
    .sort((a, b) => a.name.localeCompare(b.name))
    .slice(0, 40);

  const canAdd = selected.length < maxSelections;

  function pick(college: CollegeListItem) {
    if (!canAdd) return;
    onAdd(college);
    setQuery("");
    setHighlighted(0);
    inputRef.current?.focus();
  }

  function handleKey(e: React.KeyboardEvent) {
    if (!open) {
      if (e.key === "ArrowDown") { setOpen(true); return; }
      return;
    }
    if (e.key === "ArrowDown") {
      setHighlighted((h) => Math.min(h + 1, filtered.length - 1));
    } else if (e.key === "ArrowUp") {
      setHighlighted((h) => Math.max(h - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (filtered[highlighted]) pick(filtered[highlighted]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  // Close on outside click
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (
        !inputRef.current?.parentElement?.contains(e.target as Node) &&
        !listRef.current?.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Scroll highlighted item into view
  useEffect(() => {
    const el = listRef.current?.children[highlighted] as HTMLElement | undefined;
    el?.scrollIntoView({ block: "nearest" });
  }, [highlighted]);

  return (
    <div className="space-y-3">
      {/* Selected pills */}
      {selected.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {selected.map((c, i) => (
            <span
              key={c.code}
              className="flex items-center gap-1.5 bg-blue-900/50 border border-blue-700 text-blue-200 text-xs rounded-full px-3 py-1"
            >
              <span className="font-semibold text-blue-400">{i + 1}.</span>
              {c.name}
              <button
                type="button"
                onClick={() => onRemove(c.code)}
                className="ml-0.5 text-blue-400 hover:text-red-400 transition-colors leading-none"
                aria-label={`Remove ${c.name}`}
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Input */}
      {canAdd && (
        <div className="relative">
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 text-sm">🔍</span>
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => { setQuery(e.target.value); setOpen(true); setHighlighted(0); }}
              onFocus={() => setOpen(true)}
              onKeyDown={handleKey}
              placeholder={`Type college name… (${selected.length}/${maxSelections} selected)`}
              className="w-full bg-slate-900 border border-slate-600 rounded-lg pl-9 pr-4 py-2.5 text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            />
          </div>

          {open && filtered.length > 0 && (
            <ul
              ref={listRef}
              className="absolute z-50 mt-1 w-full max-h-64 overflow-y-auto bg-slate-800 border border-slate-600 rounded-xl shadow-2xl"
            >
              {filtered.map((c, i) => (
                <li key={c.code}>
                  <button
                    type="button"
                    onMouseDown={(e) => { e.preventDefault(); pick(c); }}
                    onMouseEnter={() => setHighlighted(i)}
                    className={`w-full text-left px-4 py-2.5 text-sm flex items-center justify-between gap-2 transition-colors ${
                      i === highlighted ? "bg-blue-700 text-white" : "text-slate-200 hover:bg-slate-700"
                    }`}
                  >
                    <span className="truncate">{c.name}</span>
                    <span className={`text-xs shrink-0 px-1.5 py-0.5 rounded ${
                      i === highlighted ? "bg-blue-600 text-blue-100" : "bg-slate-700 text-slate-400"
                    }`}>
                      {c.section.replace("GOVT_", "Govt ").replace("PVT_", "Pvt ").replace("MIN_", "Min ")}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}

          {open && query.length > 1 && filtered.length === 0 && (
            <div className="absolute z-50 mt-1 w-full bg-slate-800 border border-slate-600 rounded-xl px-4 py-3 text-sm text-slate-400">
              No colleges found for &ldquo;{query}&rdquo;
            </div>
          )}
        </div>
      )}

      {!canAdd && (
        <p className="text-xs text-amber-400">Maximum {maxSelections} colleges selected. Remove one to add another.</p>
      )}
    </div>
  );
}
