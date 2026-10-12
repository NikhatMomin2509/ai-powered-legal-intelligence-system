import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, Lightbulb, AlertTriangle, FileCode2, Scale } from "lucide-react";
import RiskBadge from "./RiskBadge";
import AuthorityCard from "./AuthorityCard";

export default function ClauseAccordion({ clause }) {
  const [open, setOpen] = useState(false);
  if (!clause) return null;

  const hasExplanation = !clause?.llm_error && (clause?.plain_explanation || clause?.why_risky);
  const laws = Array.isArray(clause?.relevant_laws) ? clause.relevant_laws : [];
  const riskBorder =
    clause?.risk_level?.toUpperCase() === "HIGH"
      ? "citation-border-oppose"
      : clause?.risk_level?.toUpperCase() === "MEDIUM"
      ? "citation-border-statute"
      : "citation-border-support";

  return (
    <div className={`glass rounded-2xl overflow-hidden ${riskBorder} transition-colors`}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between gap-4 p-4 text-left hover:bg-white/[0.03] transition-colors"
        aria-expanded={open}
      >
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1.5 flex-wrap">
            <RiskBadge level={clause?.risk_level} />
            <span className="text-xs font-mono text-ink-400">
              {clause?.risk_category || "Uncategorized"}
              {clause?.page_number ? ` · Page ${clause.page_number}` : ""}
            </span>
          </div>
          <p className="text-sm text-ink-200 line-clamp-1 font-mono">
            {clause?.clause_text || "No clause text available."}
          </p>
        </div>
        <motion.div animate={{ rotate: open ? 180 : 0 }} transition={{ duration: 0.2 }} className="shrink-0">
          <ChevronDown size={18} className="text-ink-500" />
        </motion.div>
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-5 pt-2 space-y-4 border-t border-white/[0.06]">
              {/* Verbatim Contract Text */}
              <div>
                <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-ink-500 font-mono mb-1.5">
                  <FileCode2 size={13} />
                  <span>Verbatim Clause Text</span>
                </div>
                <div className="rounded-xl bg-ink-950/80 border border-white/[0.06] p-3.5">
                  <p className="text-xs font-mono text-ink-200 leading-relaxed whitespace-pre-wrap">
                    {clause?.clause_text}
                  </p>
                </div>
              </div>

              {/* Rule Match Rationale */}
              <div>
                <p className="text-[11px] uppercase tracking-wider text-ink-500 font-mono mb-1">
                  Why this was flagged
                </p>
                <p className="text-xs text-ink-300 leading-relaxed font-sans">
                  {clause?.reason}
                </p>
              </div>

              {/* Plain-English Legal Explanation */}
              {hasExplanation && (
                <div className="rounded-xl bg-white/[0.02] border border-white/[0.06] p-3.5 space-y-2">
                  <p className="text-[11px] uppercase tracking-wider text-ink-400 font-mono">
                    Plain-English Assessment
                  </p>
                  {clause?.plain_explanation && (
                    <p className="text-xs text-ink-200 leading-relaxed">
                      {clause.plain_explanation}
                    </p>
                  )}
                  {clause?.why_risky && (
                    <p className="text-xs text-ink-400 leading-relaxed">
                      <span className="font-semibold text-ink-300">Potential Risk: </span>
                      {clause.why_risky}
                    </p>
                  )}
                </div>
              )}

              {/* Degraded Explanation Notice */}
              {clause?.llm_error && (
                <div className="rounded-xl border border-amber-500/20 bg-amber-500/[0.04] p-3 flex gap-2.5 items-start">
                  <AlertTriangle size={15} className="text-amber-400 shrink-0 mt-0.5" />
                  <p className="text-xs text-amber-300 leading-relaxed">
                    A detailed plain-English explanation could not be generated for this clause due to an analysis timeout. Rule-based detection remains verified above.
                  </p>
                </div>
              )}

              {/* Practical Negotiation Strategy */}
              {clause?.negotiation_point && (
                <div className="rounded-xl bg-emerald-500/[0.06] border border-emerald-500/20 p-3.5 flex gap-2.5">
                  <Lightbulb size={16} className="text-emerald-400 shrink-0 mt-0.5" />
                  <div>
                    <p className="text-xs font-semibold text-emerald-400 mb-1">
                      Negotiation Counterpoint
                    </p>
                    <p className="text-xs text-ink-200 leading-relaxed">
                      {clause.negotiation_point}
                    </p>
                  </div>
                </div>
              )}

              {/* Cited Indian Law Foundation */}
              {laws.length > 0 && (
                <div>
                  <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-ink-500 font-mono mb-2">
                    <Scale size={13} />
                    <span>Statutory Authority Found</span>
                  </div>
                  <div className="space-y-2.5">
                    {laws.map((law, i) => (
                      <AuthorityCard key={law?.ref_id || `${law?.act}-${law?.section}-${i}`} law={law} />
                    ))}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
