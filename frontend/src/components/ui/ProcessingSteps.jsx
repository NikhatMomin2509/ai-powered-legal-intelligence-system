import { motion, AnimatePresence } from "framer-motion";
import { Check, Loader2 } from "lucide-react";

/**
 * steps: [{label: string}]
 * activeIndex: index of the step currently in progress (steps before it are
 * complete; steps after are pending). Pass -1 for "not started".
 */
export default function ProcessingSteps({ steps, activeIndex }) {
  return (
    <div className="glass rounded-2xl p-6 space-y-1">
      {steps.map((step, i) => {
        const isDone = i < activeIndex;
        const isActive = i === activeIndex;
        return (
          <div key={step.label} className="flex items-center gap-3 py-2.5">
            <div
              className={`flex items-center justify-center w-6 h-6 rounded-full border shrink-0 transition-colors duration-300 ${
                isDone
                  ? "bg-emerald-500 border-emerald-500"
                  : isActive
                  ? "border-emerald-400 shadow-glow"
                  : "border-white/15"
              }`}
            >
              <AnimatePresence>
                {isDone ? (
                  <motion.div key="check" initial={{ scale: 0 }} animate={{ scale: 1 }}>
                    <Check size={13} className="text-zinc-950" strokeWidth={3} />
                  </motion.div>
                ) : isActive ? (
                  <Loader2 size={13} className="text-emerald-400 animate-spin" />
                ) : null}
              </AnimatePresence>
            </div>
            <span
              className={`text-sm transition-colors duration-300 ${
                isDone ? "text-zinc-400" : isActive ? "text-zinc-100 font-medium" : "text-zinc-600"
              }`}
            >
              {step.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}
