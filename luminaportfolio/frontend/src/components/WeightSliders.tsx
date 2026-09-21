"use client";

import type { ScoreWeights } from "@/lib/api";

const CRITERIA = ["sharpness", "lighting", "contrast", "composition", "resolution"] as const;

const DEFAULT_WEIGHTS: Required<ScoreWeights> = {
  sharpness: 0.3,
  lighting: 0.2,
  contrast: 0.15,
  composition: 0.15,
  resolution: 0.2,
};

interface WeightSlidersProps {
  weights: Required<ScoreWeights>;
  onChange: (w: Required<ScoreWeights>) => void;
}

export function WeightSliders({ weights, onChange }: WeightSlidersProps) {
  const total = Object.values(weights).reduce((a, b) => a + b, 0);

  function handleChange(key: keyof ScoreWeights, raw: string) {
    const val = Math.max(0, Math.min(1, parseFloat(raw) / 100));
    onChange({ ...weights, [key]: val });
  }

  function handleReset() {
    onChange({ ...DEFAULT_WEIGHTS });
  }

  return (
    <div className="rounded-2xl border border-[#2a2a2a] bg-[#141414] p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-[#6b7280]">
          Score weights
        </h3>
        <div className="flex items-center gap-3">
          <span
            className={`text-xs tabular-nums ${
              Math.abs(total - 1) > 0.01 ? "text-amber-400" : "text-[#6b7280]"
            }`}
          >
            sum {Math.round(total * 100)}%
            {Math.abs(total - 1) > 0.01 && " (renormalized by server)"}
          </span>
          <button
            onClick={handleReset}
            className="rounded-lg border border-[#2a2a2a] px-2 py-1 text-xs text-[#6b7280] hover:border-[#3a3a3a] hover:text-[#d1d5db] transition-colors"
          >
            Reset
          </button>
        </div>
      </div>

      <div className="space-y-3">
        {CRITERIA.map((key) => {
          const pct = Math.round((weights[key] ?? 0) * 100);
          return (
            <div key={key} className="space-y-1">
              <div className="flex items-center justify-between text-sm">
                <label
                  htmlFor={`weight-${key}`}
                  className="capitalize text-[#d1d5db]"
                >
                  {key}
                </label>
                <span className="tabular-nums text-[#f5f5f5] font-medium w-8 text-right">
                  {pct}%
                </span>
              </div>
              <input
                id={`weight-${key}`}
                type="range"
                min="0"
                max="100"
                step="5"
                value={pct}
                onChange={(e) => handleChange(key, e.target.value)}
                className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-[#2a2a2a] accent-amber-500"
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
