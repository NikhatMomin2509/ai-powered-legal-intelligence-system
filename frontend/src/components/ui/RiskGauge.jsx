import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Info, ChevronDown } from "lucide-react";
import { normalizeRiskLevel, RISK_LEVEL_LABEL } from "../../services/normalize";

const COLOR = {
  HIGH: "#f43f5e",
  MEDIUM: "#f59e0b",
  LOW: "#10b981",
  UNKNOWN: "#94a3b8",
};

export default function RiskGauge({ score = 0, level }) {
  const [showFormula, setShowFormula] = useState(false);
  const normalized = normalizeRiskLevel(level);
  const color = COLOR[normalized];
  const clamped = Math.max(0, Math.min(100, Number(score) || 0));

  const radius = 68;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - clamped / 100);

  return (
    <div className="flex flex-col items-center">
      <div className="relative flex items-center justify-center w-44 h-44">
        <svg width="176" height="176" viewBox="0 0 176 176" className="-rotate-90">
          <circle
            cx="88"
            cy="88"
            r={radius}
            fill="none"
            stroke="rgba(255, 255, 255, 0.07)"
            strokeWidth="12"
          />
          <motion.circle
            cx="88"
            cy="88"
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth="12"
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 0.8, ease: "easeOut" }}
          />
        </svg>

        <div className="absolute flex flex-col items-center text-center px-2">
          <span className="text-3xl font-mono font-semibold tracking-tight text-ink-50">
            {clamped}
          </span>
          <span className="text-[11px] font-mono text-ink-500 uppercase tracking-wider">
            Index / 100
          </span>
          <span
            className="mt-1 px-2 py-0.5 rounded text-xs font-medium tracking-wide"
            style={{ color, backgroundColor: `${color}18` }}
          >
            {RISK_LEVEL_LABEL[normalized]} risk
          </span>
        </div>
      </div>

      <div className="mt-3 flex flex-col items-center">
        <span className="text-[11px] font-mono uppercase tracking-widest text-ink-500">
          Indicative Rule-Based Score
        </span>

        <button
          type="button"
          onClick={() => setShowFormula((v) => !v)}
          className="mt-2 inline-flex items-center gap-1.5 text-xs text-ink-400 hover:text-ink-200 transition-colors"
          aria-expanded={showFormula}
        >
          <Info size={13} className="text-ink-500" />
          <span>How this score is calculated</span>
          <motion.div animate={{ rotate: showFormula ? 180 : 0 }} transition={{ duration: 0.2 }}>
            <ChevronDown size={13} />
          </motion.div>
        </button>

        <AnimatePresence>
          {showFormula && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden mt-3 max-w-sm"
            >
              <div className="rounded-xl border border-white/10 bg-ink-950/90 p-3.5 text-left text-xs text-ink-400 leading-relaxed font-sans space-y-1.5">
                <p className="font-semibold text-ink-300">Rule-Based Severity Average</p>
                <p>
                  Calculated from the severity mix of detected clauses: <span className="font-mono text-emerald-400">LOW = 1</span>, <span className="font-mono text-amber-400">MEDIUM = 2</span>, <span className="font-mono text-rose-400">HIGH = 3</span> averaged into an indicative 0–100 index.
                </p>
                <p className="text-ink-500 pt-1 border-t border-white/[0.06]">
                  This is not a legal judgment, does not depend on document page length, and does not assess general enforceability.
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
