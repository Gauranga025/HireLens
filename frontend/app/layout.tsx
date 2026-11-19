import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "HireLens - AI Resume Screening Platform",
  description: "AI-powered resume screening and candidate matching for recruiters",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="antialiased">
      <body className="min-h-screen bg-background text-foreground">{children}</body>
    </html>
  );
}
