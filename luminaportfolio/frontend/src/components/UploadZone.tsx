"use client";

import { useCallback, useRef, useState } from "react";

interface UploadZoneProps {
  onFile: (file: File) => void;
  disabled?: boolean;
}

export function UploadZone({ onFile, disabled }: UploadZoneProps) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    (f: File) => {
      if (f.type.startsWith("image/")) onFile(f);
    },
    [onFile]
  );

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }

  function onInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (f) handleFile(f);
    e.target.value = "";
  }

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label="Upload an image"
      onClick={() => !disabled && inputRef.current?.click()}
      onKeyDown={(e) =>
        (e.key === "Enter" || e.key === " ") && !disabled && inputRef.current?.click()
      }
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      className={`
        flex cursor-pointer flex-col items-center justify-center gap-3 rounded-2xl
        border-2 border-dashed p-10 text-center transition-colors duration-200
        ${disabled ? "cursor-not-allowed opacity-50" : ""}
        ${
          dragging
            ? "border-amber-500 bg-amber-500/5"
            : "border-[#2a2a2a] bg-[#141414] hover:border-[#3a3a3a] hover:bg-[#1a1a1a]"
        }
      `}
    >
      <svg
        className={`h-10 w-10 ${dragging ? "text-amber-400" : "text-[#3a3a3a]"}`}
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={1.5}
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
        />
      </svg>
      <div>
        <p className="font-medium text-[#d1d5db]">
          Drop an image here or{" "}
          <span className="text-amber-400 underline underline-offset-2">browse</span>
        </p>
        <p className="mt-1 text-sm text-[#6b7280]">JPEG, PNG, WebP — up to 20 MB</p>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        className="sr-only"
        onChange={onInputChange}
        disabled={disabled}
      />
    </div>
  );
}
