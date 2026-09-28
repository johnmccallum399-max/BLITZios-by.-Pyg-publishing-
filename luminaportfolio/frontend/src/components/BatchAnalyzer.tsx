"use client";

import { useState } from "react";
import type { BatchAnalyzeResponse, ScoreWeights } from "@/lib/api";
import { analyzeBatch } from "@/lib/api";
import { VerdictBadge } from "./VerdictBadge";

interface BatchAnalyzerProps {
  weights?: ScoreWeights;
}

export function BatchAnalyzer({ weights }: BatchAnalyzerProps) {
  const [rawUrls, setRawUrls] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BatchAnalyzeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const urls = rawUrls
    .split(/[\n,]+/)
    .map((u) => u.trim())
    .filter(Boolean);

  async function handleAnalyze() {
    if (urls.length === 0) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await analyzeBatch(urls, weights);
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Batch analysis failed");
    } finally {
      setLoading(false);
    }
  }

  const sorted = result
    ? [...result.results].sort(
        (a, b) => (b.scores?.overall ?? -1) - (a.scores?.overall ?? -1)
      )
    : [];

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <label className="text-sm font-medium text-[#d1d5db]">
          Image URLs{" "}
          <span className="text-[#6b7280]">(one per line or comma-separated, max 50)</span>
        </label>
        <textarea
          value={rawUrls}
          onChange={(e) => setRawUrls(e.target.value)}
          placeholder={"https://example.com/photo1.jpg\nhttps://example.com/photo2.jpg"}
          rows={5}
          className="w-full resize-y rounded-xl border border-[#2a2a2a] bg-[#0a0a0a] px-4 py-3 text-sm text-[#f5f5f5] placeholder-[#3a3a3a] focus:border-amber-500 focus:outline-none transition-colors"
        />
        <div className="flex items-center justify-between">
          <span className="text-xs text-[#6b7280]">{urls.length} URL{urls.length !== 1 ? "s" : ""}</span>
          <button
            onClick={handleAnalyze}
            disabled={loading || urls.length === 0 || urls.length > 50}
            className="rounded-xl bg-amber-500 px-5 py-2 text-sm font-semibold text-black hover:bg-amber-400 disabled:cursor-not-allowed disabled:opacity-40 transition-colors"
          >
            {loading ? "Analyzing…" : `Analyze ${urls.length > 0 ? urls.length : ""} Images`}
          </button>
        </div>
      </div>

      {error && (
        <p className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </p>
      )}

      {sorted.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-[#6b7280]">
            Results — sorted best first
          </p>
          <div className="overflow-hidden rounded-xl border border-[#2a2a2a]">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[#2a2a2a] bg-[#141414]">
                  <th className="px-4 py-2.5 text-left font-medium text-[#6b7280]">Image</th>
                  <th className="px-4 py-2.5 text-right font-medium text-[#6b7280]">Score</th>
                  <th className="px-4 py-2.5 text-right font-medium text-[#6b7280]">Verdict</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((item, i) => (
                  <tr
                    key={i}
                    className="border-b border-[#2a2a2a] last:border-0 bg-[#0a0a0a] hover:bg-[#141414] transition-colors"
                  >
                    <td className="max-w-xs truncate px-4 py-3 text-[#9ca3af]" title={item.image_url}>
                      {item.image_url.replace(/^https?:\/\//, "").slice(0, 60)}
                      {item.image_url.replace(/^https?:\/\//, "").length > 60 ? "…" : ""}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums font-semibold text-[#f5f5f5]">
                      {item.scores ? Math.round(item.scores.overall) : "—"}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {item.scores ? (
                        <VerdictBadge verdict={item.scores.verdict} />
                      ) : (
                        <span className="text-red-400 text-xs">{item.error ?? "Error"}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-[#6b7280]">
            {sorted.filter((r) => r.scores?.verdict === "portfolio-ready").length} portfolio-ready
            {" · "}
            {sorted.filter((r) => r.scores?.verdict === "cull").length} culled
          </p>
        </div>
      )}
    </div>
  );
}
