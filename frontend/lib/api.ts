const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface RoundInfo {
  round: string;
  closing_rank: number;
  seats_filled: number;
}

export interface College {
  college_code: string;
  college_name: string;
  category: string;
  women_quota: boolean;
  section: string;
  total_seats: number;
  r1_closing: number;
  best_closing: number;
  worst_closing: number;
  fill_rate: number;
  seat_movement: number;
  round_probability: number;
  final_probability: number;
  tier: "Safe" | "Moderate" | "Aggressive";
  rounds: Record<string, RoundInfo>;
}

export interface PredictResponse {
  student_air: number;
  category: string;
  women_quota: boolean;
  year: number;
  safe: College[];
  moderate: College[];
  aggressive: College[];
  total_options: number;
  safe_count: number;
  moderate_count: number;
  aggressive_count: number;
}

export interface PredictRequest {
  air: number;
  category: string;
  women_quota: boolean;
  year?: number;
  top_n?: number;
}

export async function predict(req: PredictRequest): Promise<PredictResponse> {
  const res = await fetch(`${API_BASE}/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ year: 2025, top_n: 50, ...req }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `API error ${res.status}`);
  }
  return res.json();
}

export const CATEGORIES = [
  "OPEN", "OBC", "SEBC", "SC", "ST",
  "EWS", "VJA", "NTB", "NTC", "NTD",
  "HA", "D1", "D2", "D3",
];

export const SECTION_LABEL: Record<string, string> = {
  GOVT_MBBS: "Govt MBBS",
  PVT_MBBS:  "Private MBBS",
  GOVT_BDS:  "Govt BDS",
  PVT_BDS:   "Private BDS",
  MIN_MBBS:  "Minority MBBS",
  MIN_BDS:   "Minority BDS",
};
