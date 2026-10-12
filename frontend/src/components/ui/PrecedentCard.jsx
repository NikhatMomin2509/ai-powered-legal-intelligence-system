import { Landmark } from "lucide-react";

/**
 * PrecedentCard — renders retrieved Supreme Court judgments / case law.
 * Shows exact case name / appeal record without beautifying or inventing titles.
 * Displays domain tag, database source attribution, and why it is relevant.
 */
export default function PrecedentCard({ item }) {
  if (!item) return null;

  const rawName = item?.case_name || item?.title || "Judicial Precedent";
  const source = item?.source || "Supreme Court of India";
  const domain = item?.domain;
  const whyRelevant = item?.why_relevant;
  const caseId = item?.case_id;

  return (
    <div className="rounded-xl border border-precedent/25 bg-ink-900/90 p-4 citation-border-precedent shadow-sm hover:border-precedent/40 transition-colors">
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono tracking-wider uppercase font-semibold text-precedent-light bg-precedent/10 border border-precedent/20">
            <Landmark size={11} />
            Precedent
          </span>
          {domain && (
            <span className="text-[11px] font-mono font-medium text-indigo-200/90 px-1.5 py-0.5 rounded bg-white/[0.04]">
              {domain}
            </span>
          )}
        </div>
        {caseId && (
          <span className="text-[10px] text-ink-500 font-mono">
            ID: {caseId}
          </span>
        )}
      </div>

      <div className="min-w-0">
        {/* Rendered exactly as given by the database/retrieval engine — never beautified */}
        <h4 className="text-sm font-serif font-medium text-ink-100 tracking-tight leading-snug">
          {rawName}
        </h4>
        <p className="text-xs text-ink-400 mt-1 font-mono">
          Source: {source}
        </p>

        {whyRelevant && (
          <div className="mt-3 pt-2.5 border-t border-white/[0.06]">
            <p className="text-[11px] uppercase tracking-wider text-ink-500 font-mono mb-1">
              Precedential Application
            </p>
            <p className="text-xs text-ink-300 leading-relaxed font-sans">
              {whyRelevant}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
