import { AlertTriangle } from "lucide-react";

/**
 * Disclaimer — mandatory statutory and ethical disclaimer.
 * Prominently visible on every analysis result.
 */
export default function Disclaimer({ text }) {
  const fallback =
    "This assessment is informational only. It does not constitute legal advice, does not predict " +
    "litigation or dispute outcomes, and cannot substitute for representation by an enrolled advocate.";

  return (
    <div
      role="note"
      aria-label="Legal Disclaimer"
      className="rounded-xl border border-amber-500/25 bg-amber-500/[0.04] p-4 flex gap-3 items-start"
    >
      <AlertTriangle size={16} className="text-amber-400 shrink-0 mt-0.5" />
      <div className="text-xs leading-relaxed text-ink-300">
        <p className="font-semibold text-amber-300 mb-0.5">
          Informational Tool — Not Legal Advice
        </p>
        <p>{text || fallback}</p>
      </div>
    </div>
  );
}
