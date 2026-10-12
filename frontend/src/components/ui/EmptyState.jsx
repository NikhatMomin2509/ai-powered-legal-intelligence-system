import { FolderOpen } from "lucide-react";

/**
 * EmptyState — accessible empty and zero-state display.
 */
export default function EmptyState({
  icon: Icon = FolderOpen,
  title = "No records found",
  description,
  action,
  className = "",
}) {
  return (
    <div
      className={`rounded-2xl border border-white/10 bg-ink-900/90 p-10 flex flex-col items-center text-center max-w-lg mx-auto ${className}`}
    >
      <div className="w-12 h-12 rounded-xl bg-white/[0.04] border border-white/10 flex items-center justify-center mb-4 text-ink-400">
        <Icon size={22} />
      </div>
      <h3 className="text-base font-medium text-ink-100 tracking-tight">
        {title}
      </h3>
      {description && (
        <p className="text-xs text-ink-400 mt-2 leading-relaxed max-w-sm">
          {description}
        </p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
