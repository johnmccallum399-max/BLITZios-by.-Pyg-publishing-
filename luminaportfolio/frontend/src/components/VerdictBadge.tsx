"use client";

import type { ScoreResponse } from "@/lib/api";

const VERDICT_CONFIG = {
  "portfolio-ready": {
    label: "Portfolio Ready",
    classes: "bg-emerald-500/20 text-emerald-400 border-emerald-500/40",
    dot: "bg-emerald-400",
  },
  strong: {
    label: "Strong",
    classes: "bg-blue-500/20 text-blue-400 border-blue-500/40",
    dot: "bg-blue-400",
  },
  usable: {
    label: "Usable",
    classes: "bg-amber-500/20 text-amber-400 border-amber-500/40",
    dot: "bg-amber-400",
  },
  cull: {
    label: "Cull",
    classes: "bg-red-500/20 text-red-400 border-red-500/40",
    dot: "bg-red-400",
  },
} as const;

export function VerdictBadge({ verdict }: { verdict: ScoreResponse["verdict"] }) {
  const cfg = VERDICT_CONFIG[verdict];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm font-medium ${cfg.classes}`}
    >
      <span className={`h-2 w-2 rounded-full ${cfg.dot}`} />
      {cfg.label}
    </span>
  );
}
