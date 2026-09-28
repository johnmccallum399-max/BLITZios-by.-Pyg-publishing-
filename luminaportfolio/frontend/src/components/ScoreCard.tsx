"use client";

import type { ScoreResponse, ScoreWeights } from "@/lib/api";
import { ScoreBar } from "./ScoreBar";
import { VerdictBadge } from "./VerdictBadge";

const CRITERIA = ["sharpness", "lighting", "contrast", "composition", "resolution"] as const;

const DEFAULT_WEIGHTS: ScoreWeights = {
  sharpness: 0.3,
  lighting: 0.2,
  contrast: 0.15,
  composition: 0.15,
  resolution: 0.2,
};

interface ScoreCardProps {
  scores: ScoreResponse;
  weights?: ScoreWeights;
  imagePreview?: string;
  imageLabel?: string;
}

export function ScoreCard({ scores, weights, imagePreview, imageLabel }: ScoreCardProps) {
  const w = weights ?? DEFAULT_WEIGHTS;

  return (
    <div className="animate-[fadeIn_0.4s_ease-out] rounded-2xl border border-[#2a2a2a] bg-[#141414] p-6 space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1 min-w-0">
          {imageLabel && (
            <p className="truncate text-sm text-[#6b7280]" title={imageLabel}>
              {imageLabel}
            </p>
          )}
          <div className="flex items-center gap-3">
            <span className="text-4xl font-bold tabular-nums text-[#f5f5f5]">
              {Math.round(scores.overall)}
            </span>
            <span className="text-lg text-[#6b7280]">/ 100</span>
          </div>
        </div>
        <VerdictBadge verdict={scores.verdict} />
      </div>

      {/* Image preview */}
      {imagePreview && (
        <div className="overflow-hidden rounded-xl bg-[#0a0a0a]">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={imagePreview}
            alt="Scored image"
            className="max-h-56 w-full object-contain"
          />
        </div>
      )}

      {/* Criteria bars */}
      <div className="space-y-3">
        {CRITERIA.map((key) => (
          <ScoreBar
            key={key}
            label={key}
            value={scores[key]}
            weight={w[key]}
          />
        ))}
      </div>
    </div>
  );
}
