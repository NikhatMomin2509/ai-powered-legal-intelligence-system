import { BookOpen } from "lucide-react";

/**
 * AuthorityCard — renders a retrieved statutory provision.
 * Metaphor: A citation card from an annotated legal brief.
 * Formatted with monospace section identifier, authoritative act title,
 * and a clear distinction between the statute reference and the reason it matters.
 */
export default function AuthorityCard({ law }) {
  if (!law) return null;

  const sectionLabel = law?.section ? `§ ${law.section}` : null;
  const actName = law?.act || "Indian Statute";
  const title = law?.title;
  const whyRelevant = law?.why_relevant;
  const contentExcerpt = law?.content;

  return (
    <div className="rounded-xl border border-statute/25 bg-ink-900/90 p-4 citation-border-statute shadow-sm hover:border-statute/40 transition-colors">
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono tracking-wider uppercase font-semibold text-statute-light bg-statute/10 border border-statute/20">
            <BookOpen size={11} />
            Statute
          </span>
          {sectionLabel && (
            <span className="text-xs font-mono font-medium text-amber-200/90 px-1.5 py-0.5 rounded bg-white/[0.04]">
              {sectionLabel}
            </span>
          )}
        </div>
        {law?.category && (
          <span className="text-[11px] text-ink-500 font-mono capitalize">
            {law.category}
          </span>
        )}
      </div>

      <div className="min-w-0">
        <h4 className="text-sm font-serif font-medium text-ink-100 tracking-tight">
          {actName}
        </h4>
        {title && (
          <p className="text-xs text-ink-400 mt-0.5 font-sans leading-snug">
            {title}
          </p>
        )}

        {whyRelevant && (
          <div className="mt-3 pt-2.5 border-t border-white/[0.06]">
            <p className="text-[11px] uppercase tracking-wider text-ink-500 font-mono mb-1">
              Relevance to Issue
            </p>
            <p className="text-xs text-ink-300 leading-relaxed font-sans">
              {whyRelevant}
            </p>
          </div>
        )}

        {!whyRelevant && contentExcerpt && (
          <div className="mt-3 pt-2.5 border-t border-white/[0.06]">
            <p className="text-[11px] uppercase tracking-wider text-ink-500 font-mono mb-1">
              Statutory Text Excerpt
            </p>
            <p className="text-xs text-ink-300 leading-relaxed font-sans italic line-clamp-4">
              &ldquo;{contentExcerpt}&rdquo;
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
