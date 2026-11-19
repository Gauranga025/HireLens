"use client";

import { Loader2 } from 'lucide-react';

interface ScreeningProgressProps {
  isScreening: boolean;
}

export function ScreeningProgress({ isScreening }: ScreeningProgressProps) {
  if (!isScreening) return null;

  return (
    <section className="border-b bg-card">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-3xl">
          <div className="flex items-center gap-3">
            <Loader2 className="h-5 w-5 animate-spin text-primary" />
            <div>
              <h2 className="text-lg font-semibold">Screening Candidates</h2>
              <p className="text-sm text-muted-foreground">
                Analyzing resumes against job requirements...
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
