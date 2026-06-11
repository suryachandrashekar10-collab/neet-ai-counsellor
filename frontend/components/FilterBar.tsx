"use client";

export interface Filters {
  course:    "ALL" | "MBBS" | "BDS";
  collegeType: "ALL" | "GOVT" | "PVT";
  sortBy:    "probability" | "r1_closing" | "fill_rate" | "name";
}

export const DEFAULT_FILTERS: Filters = {
  course:      "ALL",
  collegeType: "ALL",
  sortBy:      "probability",
};

interface Props {
  filters: Filters;
  onChange: (f: Filters) => void;
  totalShown: number;
  totalAll: number;
}

function Pill({
  active, onClick, children,
}: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
        active
          ? "bg-blue-600 text-white"
          : "bg-slate-700 text-slate-400 hover:bg-slate-600 hover:text-slate-200"
      }`}
    >
      {children}
    </button>
  );
}

export default function FilterBar({ filters, onChange, totalShown, totalAll }: Props) {
  const set = (patch: Partial<Filters>) => onChange({ ...filters, ...patch });

  return (
    <div className="bg-slate-800/60 border border-slate-700 rounded-xl px-4 py-3 flex flex-wrap items-center gap-4">

      {/* Course */}
      <div className="flex items-center gap-1.5">
        <span className="text-xs text-slate-500 mr-1">Course</span>
        <Pill active={filters.course === "ALL"}  onClick={() => set({ course: "ALL" })}>All</Pill>
        <Pill active={filters.course === "MBBS"} onClick={() => set({ course: "MBBS" })}>MBBS</Pill>
        <Pill active={filters.course === "BDS"}  onClick={() => set({ course: "BDS" })}>BDS</Pill>
      </div>

      <div className="w-px h-5 bg-slate-700" />

      {/* College type */}
      <div className="flex items-center gap-1.5">
        <span className="text-xs text-slate-500 mr-1">Type</span>
        <Pill active={filters.collegeType === "ALL"}  onClick={() => set({ collegeType: "ALL" })}>All</Pill>
        <Pill active={filters.collegeType === "GOVT"} onClick={() => set({ collegeType: "GOVT" })}>Govt</Pill>
        <Pill active={filters.collegeType === "PVT"}  onClick={() => set({ collegeType: "PVT" })}>Private</Pill>
      </div>

      <div className="w-px h-5 bg-slate-700" />

      {/* Sort */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-slate-500">Sort by</span>
        <select
          value={filters.sortBy}
          onChange={(e) => set({ sortBy: e.target.value as Filters["sortBy"] })}
          className="bg-slate-700 border border-slate-600 rounded-lg px-2 py-1 text-xs text-slate-300 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="probability">Probability</option>
          <option value="r1_closing">R1 Closing Rank</option>
          <option value="fill_rate">Fill Rate</option>
          <option value="name">College Name</option>
        </select>
      </div>

      {/* Count */}
      <div className="ml-auto text-xs text-slate-500">
        Showing <span className="text-slate-300 font-medium">{totalShown}</span> of {totalAll} colleges
      </div>
    </div>
  );
}
