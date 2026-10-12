/**
 * SectionHeader — consistent typographic header for sections of the legal brief.
 */
export default function SectionHeader({
  title,
  subtitle,
  icon: Icon,
  badge,
  action,
  className = "",
}) {
  return (
    <div className={`flex items-start justify-between gap-4 mb-3 ${className}`}>
      <div className="flex items-start gap-2.5">
        {Icon && (
          <div className="w-7 h-7 rounded-lg bg-white/[0.04] border border-white/10 flex items-center justify-center shrink-0 mt-0.5 text-ink-400">
            <Icon size={14} />
          </div>
        )}
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-sm font-medium tracking-tight text-ink-200">
              {title}
            </h3>
            {badge && (
              <span className="text-[11px] font-mono px-2 py-0.2 rounded-full bg-white/[0.04] border border-white/10 text-ink-400">
                {badge}
              </span>
            )}
          </div>
          {subtitle && (
            <p className="text-xs text-ink-500 mt-0.5 leading-relaxed">
              {subtitle}
            </p>
          )}
        </div>
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}
