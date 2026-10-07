export function SkeletonLine({ width = "100%", className = "" }) {
  return (
    <div
      className={`h-3.5 rounded-full bg-white/[0.06] animate-pulse-soft ${className}`}
      style={{ width }}
    />
  );
}

export function SkeletonCard({ lines = 3 }) {
  return (
    <div className="glass rounded-2xl p-5 space-y-3">
      <SkeletonLine width="40%" />
      {Array.from({ length: lines }).map((_, i) => (
        <SkeletonLine key={i} width={`${85 - i * 12}%`} />
      ))}
    </div>
  );
}

export function SkeletonGrid({ count = 3, lines = 3 }) {
  return (
    <div className="grid gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} lines={lines} />
      ))}
    </div>
  );
}
