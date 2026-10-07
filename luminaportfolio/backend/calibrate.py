#!/usr/bin/env python3
"""Sharpness threshold calibration utility.

Run this against a directory of reference portraits to find the Laplacian
variance that best separates your "sharp" shots from "blurry" ones, then
set LUMINA_SHARPNESS_THRESHOLD to the printed recommendation.

Usage:
    python calibrate.py --sharp  /path/to/sharp_portraits/ \
                        --blurry /path/to/blurry_rejects/

Options:
    --sharp DIR    Directory of images you consider acceptably sharp.
    --blurry DIR   Directory of images you consider too blurry (rejects).
    --exts EXTS    Comma-separated image extensions (default: jpg,jpeg,png,webp).
    --plot         Show a histogram (requires matplotlib).

The script prints the Laplacian variance for every image, reports the mean
and median for each class, and suggests a threshold midpoint. A threshold
midpoint between the two class means is a reasonable starting point; adjust
upward if you still get too many blurry keepers, downward if too many sharp
shots are marked cull.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np


def laplacian_variance(path: Path) -> float | None:
    img = cv2.imread(str(path))
    if img is None:
        return None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def scan(directory: Path, exts: set[str]) -> list[tuple[Path, float]]:
    results = []
    for f in sorted(directory.iterdir()):
        if f.suffix.lower().lstrip(".") not in exts:
            continue
        var = laplacian_variance(f)
        if var is None:
            print(f"  [skip] could not decode {f.name}", file=sys.stderr)
            continue
        results.append((f, var))
    return results


def stats(values: list[float]) -> dict:
    arr = np.array(values)
    return {
        "n": len(arr),
        "min": float(arr.min()),
        "max": float(arr.max()),
        "mean": float(arr.mean()),
        "median": float(np.median(arr)),
        "std": float(arr.std()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sharp", required=True, type=Path, metavar="DIR")
    parser.add_argument("--blurry", required=True, type=Path, metavar="DIR")
    parser.add_argument("--exts", default="jpg,jpeg,png,webp")
    parser.add_argument("--plot", action="store_true")
    args = parser.parse_args()

    exts = {e.strip().lower() for e in args.exts.split(",")}

    print("Scanning sharp images …")
    sharp = scan(args.sharp, exts)
    print("Scanning blurry images …")
    blurry = scan(args.blurry, exts)

    if not sharp:
        sys.exit("No sharp images found — check --sharp path and --exts")
    if not blurry:
        sys.exit("No blurry images found — check --blurry path and --exts")

    sharp_vars = [v for _, v in sharp]
    blurry_vars = [v for _, v in blurry]

    s = stats(sharp_vars)
    b = stats(blurry_vars)

    print(f"\n{'Sharp':>30}  {'Blurry':>30}")
    print(f"{'─'*30}  {'─'*30}")
    for key in ("n", "min", "max", "mean", "median", "std"):
        print(f"  {key:>6}: {s[key]:>20.2f}    {key:>6}: {b[key]:>20.2f}")

    midpoint = (s["mean"] + b["mean"]) / 2.0
    print(f"\nSuggested LUMINA_SHARPNESS_THRESHOLD ≈ {midpoint:.1f}")
    print("  (midpoint of class means; tune up if blurry shots still pass, down if sharp shots are culled)")

    # Per-image detail
    print("\n--- Sharp images ---")
    for path, var in sharp:
        flag = "✓" if var >= midpoint else "✗ would cull"
        print(f"  {var:8.1f}  {path.name}  {flag}")

    print("\n--- Blurry images ---")
    for path, var in blurry:
        flag = "✗ would keep" if var >= midpoint else "✓"
        print(f"  {var:8.1f}  {path.name}  {flag}")

    if args.plot:
        try:
            import matplotlib.pyplot as plt

            bins = np.linspace(0, max(max(sharp_vars), max(blurry_vars)) * 1.1, 40)
            plt.hist(sharp_vars, bins=bins, alpha=0.6, label="Sharp", color="steelblue")
            plt.hist(blurry_vars, bins=bins, alpha=0.6, label="Blurry", color="tomato")
            plt.axvline(midpoint, color="gold", linewidth=2, linestyle="--", label=f"Threshold {midpoint:.1f}")
            plt.xlabel("Laplacian variance")
            plt.ylabel("Count")
            plt.title("Sharpness calibration")
            plt.legend()
            plt.tight_layout()
            plt.show()
        except ImportError:
            print("\n[plot skipped] install matplotlib to use --plot")


if __name__ == "__main__":
    main()
