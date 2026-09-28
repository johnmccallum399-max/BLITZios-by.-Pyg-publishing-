"use client";

function scoreColor(value: number): string {
  if (value >= 80) return "bg-emerald-500";
  if (value >= 60) return "bg-blue-500";
  if (value >= 40) return "bg-amber-500";
  return "bg-red-500";
}

interface ScoreBarProps {
  label: string;
  value: number;
  weight?: number;
}

export function ScoreBar({ label, value, weight }: ScoreBarProps) {
  const pct = Math.round(value);
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-[#d1d5db] capitalize">{label}</span>
        <div className="flex items-center gap-2">
          {weight !== undefined && (
            <span className="text-xs text-[#6b7280]">
              {Math.round(weight * 100)}% wt
            </span>
          )}
          <span className="tabular-nums font-semibold text-[#f5f5f5]">
            {pct}
          </span>
        </div>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-[#2a2a2a]">
        <div
          className={`h-full rounded-full transition-all duration-700 ease-out ${scoreColor(value)}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
