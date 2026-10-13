import { motion, AnimatePresence } from "framer-motion";
import { Check, Loader2 } from "lucide-react";

/**
 * ProcessingSteps — general visual progress view.
 * Labeled explicitly as "What the system is doing", avoiding claims of precise live stage.
 */
export default function ProcessingSteps({ steps, activeIndex }) {
  return (
    <div className="glass rounded-2xl p-6 border border-white/10">
      <div className="mb-4 pb-3 border-b border-white/[0.06]">
        <h4 className="text-sm font-serif font-medium text-ink-200">
          What the system is doing
        </h4>
        <p className="text-xs text-ink-500 mt-0.5">
          Searching Indian legal corpora and synthesizing verified considerations.
        </p>
      </div>

      <div className="space-y-1">
        {steps.map((step, i) => {
          const isDone = i < activeIndex;
          const isActive = i === activeIndex;
          return (
            <div key={step.label} className="flex items-center gap-3 py-2">
              <div
                className={`flex items-center justify-center w-5 h-5 rounded-full border shrink-0 transition-colors duration-200 ${
                  isDone
                    ? "bg-emerald-500 border-emerald-500 text-ink-950"
                    : isActive
                    ? "border-amber-400 bg-amber-400/10"
                    : "border-white/15"
                }`}
              >
                <AnimatePresence>
                  {isDone ? (
                    <motion.div key="check" initial={{ scale: 0 }} animate={{ scale: 1 }}>
                      <Check size={12} strokeWidth={3} />
                    </motion.div>
                  ) : isActive ? (
                    <Loader2 size={11} className="text-amber-400 animate-spin" />
                  ) : null}
                </AnimatePresence>
              </div>
              <span
                className={`text-xs transition-colors duration-200 ${
                  isDone
                    ? "text-ink-400 font-sans"
                    : isActive
                    ? "text-ink-100 font-medium font-sans"
                    : "text-ink-600 font-sans"
                }`}
              >
                {step.label}
              </span>
            </div>
          );
        })}
      </div>

      {activeIndex >= steps.length - 1 && (
        <div className="mt-3 pt-3 border-t border-white/[0.06] flex items-center gap-2 text-[11px] text-ink-400">
          <Loader2 size={12} className="text-accent-400 animate-spin shrink-0" />
          <span>Finalizing legal assessment... (If cloud instance is waking up, this may take a moment)</span>
        </div>
      )}
    </div>
  );
}
