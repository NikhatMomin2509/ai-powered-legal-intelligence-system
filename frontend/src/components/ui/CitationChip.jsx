/**
 * CitationChip — compact inline reference tag for provisions and cases.
 */
export default function CitationChip({ type = "statute", children, className = "" }) {
  const styles = {
    statute: "bg-statute/10 text-amber-300 border-statute/25",
    precedent: "bg-precedent/10 text-indigo-300 border-precedent/25",
    neutral: "bg-white/[0.04] text-ink-300 border-white/10",
  };

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono font-medium border ${styles[type] || styles.neutral} ${className}`}
    >
      {children}
    </span>
  );
}
