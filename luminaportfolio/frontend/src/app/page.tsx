"use client";

import { useState } from "react";
import type { ScoreResponse, ScoreWeights } from "@/lib/api";
import { analyzeUrl, analyzeUpload } from "@/lib/api";
import { UploadZone } from "@/components/UploadZone";
import { ScoreCard } from "@/components/ScoreCard";
import { WeightSliders } from "@/components/WeightSliders";
import { BatchAnalyzer } from "@/components/BatchAnalyzer";

type Tab = "single" | "batch";

const DEFAULT_WEIGHTS: Required<ScoreWeights> = {
  sharpness: 0.3,
  lighting: 0.2,
  contrast: 0.15,
  composition: 0.15,
  resolution: 0.2,
};

export default function Home() {
  const [tab, setTab] = useState<Tab>("single");
  const [urlInput, setUrlInput] = useState("");
  const [weights, setWeights] = useState<Required<ScoreWeights>>({ ...DEFAULT_WEIGHTS });
  const [showWeights, setShowWeights] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ScoreResponse | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [previewLabel, setPreviewLabel] = useState<string | null>(null);

  async function handleUrl(e: React.FormEvent) {
    e.preventDefault();
    if (!urlInput.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setPreview(null);
    try {
      const scores = await analyzeUrl(urlInput.trim(), weights);
      setResult(scores);
      setPreview(urlInput.trim());
      setPreviewLabel(urlInput.trim().replace(/^https?:\/\//, "").slice(0, 80));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleFile(file: File) {
    setLoading(true);
    setError(null);
    setResult(null);

    const objectUrl = URL.createObjectURL(file);
    setPreview(objectUrl);
    setPreviewLabel(file.name);

    try {
      const scores = await analyzeUpload(file);
      setResult(scores);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
      setPreview(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-12 space-y-10">
      {/* Header */}
      <header className="space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-2xl">✦</span>
          <h1 className="text-2xl font-bold tracking-tight text-[#f5f5f5]">
            LuminaPortfolio
          </h1>
        </div>
        <p className="text-[#6b7280]">
          Score photos on sharpness, lighting, contrast, composition, and
          resolution — surface your strongest shots automatically.
        </p>
      </header>

      {/* Tabs */}
      <div className="flex rounded-xl border border-[#2a2a2a] bg-[#141414] p-1">
        {(["single", "batch"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex-1 rounded-lg py-2 text-sm font-medium transition-colors capitalize ${
              tab === t
                ? "bg-amber-500 text-black"
                : "text-[#6b7280] hover:text-[#d1d5db]"
            }`}
          >
            {t === "single" ? "Single Image" : "Batch (up to 50)"}
          </button>
        ))}
      </div>

      {tab === "single" && (
        <div className="space-y-5">
          {/* URL input */}
          <form onSubmit={handleUrl} className="flex gap-2">
            <input
              type="url"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              placeholder="https://example.com/photo.jpg"
              className="flex-1 rounded-xl border border-[#2a2a2a] bg-[#141414] px-4 py-2.5 text-sm text-[#f5f5f5] placeholder-[#3a3a3a] focus:border-amber-500 focus:outline-none transition-colors"
            />
            <button
              type="submit"
              disabled={loading || !urlInput.trim()}
              className="rounded-xl bg-amber-500 px-5 py-2.5 text-sm font-semibold text-black hover:bg-amber-400 disabled:cursor-not-allowed disabled:opacity-40 transition-colors"
            >
              {loading ? "Scoring…" : "Score"}
            </button>
          </form>

          <div className="relative flex items-center gap-3">
            <div className="flex-1 border-t border-[#2a2a2a]" />
            <span className="text-xs text-[#3a3a3a] uppercase tracking-widest">or</span>
            <div className="flex-1 border-t border-[#2a2a2a]" />
          </div>

          <UploadZone onFile={handleFile} disabled={loading} />

          {/* Weight sliders toggle */}
          <button
            onClick={() => setShowWeights((p) => !p)}
            className="flex items-center gap-1.5 text-sm text-[#6b7280] hover:text-[#d1d5db] transition-colors"
          >
            <svg
              className={`h-4 w-4 transition-transform ${showWeights ? "rotate-180" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
            Adjust scoring weights
          </button>

          {showWeights && (
            <WeightSliders weights={weights} onChange={setWeights} />
          )}

          {/* Loading state */}
          {loading && (
            <div className="flex items-center gap-3 rounded-xl border border-[#2a2a2a] bg-[#141414] p-5">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-amber-500 border-t-transparent" />
              <p className="text-sm text-[#6b7280]">Analyzing image…</p>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3">
              <p className="text-sm font-medium text-red-400">{error}</p>
              <p className="mt-1 text-xs text-red-400/70">
                Make sure the backend is running on port 8000.
              </p>
            </div>
          )}

          {/* Result */}
          {result && !loading && (
            <ScoreCard
              scores={result}
              weights={weights}
              imagePreview={preview ?? undefined}
              imageLabel={previewLabel ?? undefined}
            />
          )}
        </div>
      )}

      {tab === "batch" && (
        <div className="space-y-5">
          {/* Weight sliders toggle */}
          <button
            onClick={() => setShowWeights((p) => !p)}
            className="flex items-center gap-1.5 text-sm text-[#6b7280] hover:text-[#d1d5db] transition-colors"
          >
            <svg
              className={`h-4 w-4 transition-transform ${showWeights ? "rotate-180" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
            Adjust scoring weights
          </button>

          {showWeights && (
            <WeightSliders weights={weights} onChange={setWeights} />
          )}

          <BatchAnalyzer weights={weights} />
        </div>
      )}

      {/* Footer */}
      <footer className="border-t border-[#2a2a2a] pt-6 text-xs text-[#3a3a3a] space-y-1">
        <p>
          Verdicts: <span className="text-emerald-700">portfolio-ready</span> ≥ 80 ·{" "}
          <span className="text-blue-700">strong</span> ≥ 60 ·{" "}
          <span className="text-amber-700">usable</span> ≥ 40 ·{" "}
          <span className="text-red-700">cull</span> &lt; 40
        </p>
        <p>Backend must be running at localhost:8000 · Google Photos integration coming in Phase 2</p>
      </footer>
    </div>
  );
}
