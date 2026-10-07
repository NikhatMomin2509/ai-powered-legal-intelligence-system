import { motion } from "framer-motion";
import { normalizeRiskLevel, RISK_LEVEL_LABEL } from "../../services/normalize";

const COLOR = {
  HIGH: "#f43f5e",
  MEDIUM: "#f59e0b",
  LOW: "#10b981",
  UNKNOWN: "#71717a",
};

export default function RiskGauge({ score = 0, level }) {
  const normalized = normalizeRiskLevel(level);
  const color = COLOR[normalized];
  const clamped = Math.max(0, Math.min(100, Number(score) || 0));

  const radius = 72;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - clamped / 100);

  return (
    <div className="relative flex items-center justify-center w-48 h-48">
      <svg width="192" height="192" viewBox="0 0 192 192" className="-rotate-90">
        <circle cx="96" cy="96" r={radius} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="14" />
        <motion.circle
          cx="96"
          cy="96"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="14"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1, ease: "easeOut" }}
          style={{ filter: `drop-shadow(0 0 10px ${color}66)` }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-4xl font-semibold tracking-tight">{clamped}</span>
        <span className="text-xs text-zinc-500 mt-0.5">out of 100</span>
        <span className="mt-2 text-sm font-medium" style={{ color }}>
          {RISK_LEVEL_LABEL[normalized]} risk
        </span>
      </div>
    </div>
  );
}
