import { normalizeRiskLevel, RISK_LEVEL_LABEL } from "../../services/normalize";

const STYLES = {
  HIGH: "bg-rose-500/10 text-rose-400 border-rose-500/30",
  MEDIUM: "bg-amber-500/10 text-amber-400 border-amber-500/30",
  LOW: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
  UNKNOWN: "bg-zinc-500/10 text-zinc-400 border-zinc-500/30",
};

export default function RiskBadge({ level, className = "" }) {
  const normalized = normalizeRiskLevel(level);
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${STYLES[normalized]} ${className}`}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {RISK_LEVEL_LABEL[normalized]} risk
    </span>
  );
}
