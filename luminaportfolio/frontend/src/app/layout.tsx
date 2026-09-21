import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LuminaPortfolio — Photo Scoring",
  description:
    "Aesthetic scoring engine for portfolio curation. Score photos on sharpness, lighting, contrast, composition, and resolution.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#0a0a0a] text-[#f5f5f5] antialiased">
        {children}
      </body>
    </html>
  );
}
