export interface ScoreWeights {
  sharpness?: number;
  lighting?: number;
  contrast?: number;
  composition?: number;
  resolution?: number;
}

export interface ScoreResponse {
  sharpness: number;
  lighting: number;
  contrast: number;
  composition: number;
  resolution: number;
  overall: number;
  verdict: "portfolio-ready" | "strong" | "usable" | "cull";
}

export interface BatchItemResult {
  image_url: string;
  scores?: ScoreResponse;
  error?: string;
}

export interface BatchAnalyzeResponse {
  results: BatchItemResult[];
}

const API_BASE = "/api/v1";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export async function analyzeUrl(
  imageUrl: string,
  weights?: ScoreWeights
): Promise<ScoreResponse> {
  const res = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image_url: imageUrl, weights: weights ?? null }),
  });
  return handleResponse<ScoreResponse>(res);
}

export async function analyzeUpload(file: File): Promise<ScoreResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/analyze/upload`, {
    method: "POST",
    body: form,
  });
  return handleResponse<ScoreResponse>(res);
}

export async function analyzeBatch(
  imageUrls: string[],
  weights?: ScoreWeights
): Promise<BatchAnalyzeResponse> {
  const res = await fetch(`${API_BASE}/analyze/batch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image_urls: imageUrls, weights: weights ?? null }),
  });
  return handleResponse<BatchAnalyzeResponse>(res);
}
