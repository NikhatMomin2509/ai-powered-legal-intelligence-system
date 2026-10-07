import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, Lightbulb } from "lucide-react";
import RiskBadge from "./RiskBadge";
import AuthorityCard from "./AuthorityCard";

export default function ClauseAccordion({ clause }) {
  const [open, setOpen] = useState(false);
  if (!clause) return null;

  const hasExplanation = !clause?.llm_error && (clause?.plain_explanation || clause?.why_risky);
  const laws = Array.isArray(clause?.relevant_laws) ? clause.relevant_laws : [];

  return (
    <div className="glass rounded-2xl overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between gap-4 p-4 text-left hover:bg-white/[0.03] transition-colors"
      >
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1.5 flex-wrap">
            <RiskBadge level={clause?.risk_level} />
            <span className="text-xs text-zinc-500">
              {clause?.risk_category || "Uncategorized"}
              {clause?.page_number ? ` · Page ${clause.page_number}` : ""}
            </span>
          </div>
          <p className="text-sm text-zinc-300 line-clamp-1">
            {clause?.clause_text || "No clause text available."}
          </p>
        </div>
        <motion.div animate={{ rotate: open ? 180 : 0 }} transition={{ duration: 0.2 }} className="shrink-0">
          <ChevronDown size={18} className="text-zinc-500" />
        </motion.div>
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-5 pt-1 space-y-4 border-t border-white/[0.06]">
              <div>
                <p className="text-xs font-medium text-zinc-500 mb-1.5">Clause text</p>
                <p className="text-sm text-zinc-300 leading-relaxed whitespace-pre-wrap">
                  {clause?.clause_text}
                </p>
              </div>

              <div>
                <p className="text-xs font-medium text-zinc-500 mb-1.5">Why this was flagged</p>
                <p className="text-sm text-zinc-400 leading-relaxed">{clause?.reason}</p>
              </div>

              {hasExplanation && (
                <div>
                  <p className="text-xs font-medium text-zinc-500 mb-1.5">Plain-English explanation</p>
                  {clause?.plain_explanation && (
                    <p className="text-sm text-zinc-300 leading-relaxed mb-2">{clause.plain_explanation}</p>
                  )}
                  {clause?.why_risky && (
                    <p className="text-sm text-zinc-400 leading-relaxed">{clause.why_risky}</p>
                  )}
                </div>
              )}

              {clause?.llm_error && (
                <p className="text-xs text-zinc-600 italic">
                  A detailed explanation could not be generated for this clause.
                </p>
              )}

              {clause?.negotiation_point && (
                <div className="rounded-xl bg-emerald-500/[0.06] border border-emerald-500/15 p-3.5 flex gap-2.5">
                  <Lightbulb size={15} className="text-emerald-400 shrink-0 mt-0.5" />
                  <div>
                    <p className="text-xs font-medium text-emerald-400 mb-1">Negotiation point</p>
                    <p className="text-sm text-zinc-300 leading-relaxed">{clause.negotiation_point}</p>
                  </div>
                </div>
              )}

              {laws.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-zinc-500 mb-2">Cited provisions</p>
                  <div className="space-y-2">
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
