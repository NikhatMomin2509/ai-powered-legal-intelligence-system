import { Info, AlertCircle, AlertTriangle, ShieldCheck } from "lucide-react";

/**
 * Callout — communicative banner for privacy notes, constraints, and operational messages.
 * Uses near-opaque backgrounds to ensure high contrast and readability.
 */
export default function Callout({
  variant = "info",
  icon: CustomIcon,
  title,
  children,
  className = "",
  action,
}) {
  const configs = {
    info: {
      border: "border-sky-500/20",
      bg: "bg-sky-500/[0.04]",
      iconColor: "text-sky-400",
      Icon: Info,
    },
    amber: {
      border: "border-amber-500/20",
      bg: "bg-amber-500/[0.04]",
      iconColor: "text-amber-400",
      Icon: AlertTriangle,
    },
    emerald: {
      border: "border-emerald-500/20",
      bg: "bg-emerald-500/[0.04]",
      iconColor: "text-emerald-400",
      Icon: ShieldCheck,
    },
    rose: {
      border: "border-rose-500/20",
      bg: "bg-rose-500/[0.04]",
      iconColor: "text-rose-400",
      Icon: AlertCircle,
    },
    neutral: {
      border: "border-white/10",
      bg: "bg-ink-900/90",
      iconColor: "text-ink-400",
      Icon: Info,
    },
  };

  const cfg = configs[variant] || configs.info;
  const ResolvedIcon = CustomIcon || cfg.Icon;

  return (
    <div
      role="note"
      className={`rounded-xl border ${cfg.border} ${cfg.bg} p-4 flex items-start gap-3 ${className}`}
    >
      <ResolvedIcon size={16} className={`${cfg.iconColor} shrink-0 mt-0.5`} />
      <div className="flex-1 min-w-0">
        {title && (
          <h4 className="text-xs font-semibold text-ink-200 mb-1">
            {title}
          </h4>
        )}
        <div className="text-xs text-ink-300 leading-relaxed font-sans">
          {children}
        </div>
      </div>
      {action && <div className="shrink-0 ml-2">{action}</div>}
    </div>
  );
}
