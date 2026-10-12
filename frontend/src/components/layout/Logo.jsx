/**
 * Logo — original vector emblem for the AI Legal Intelligence System.
 * An abstract geometric motif combining a legal folio, vertical columnar foundation,
 * and dual balanced authority bars. No state emblems or government insignia.
 */
export default function Logo({ size = 28, className = "" }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`shrink-0 ${className}`}
      aria-hidden="true"
    >
      {/* Outer shield/folio subtle background */}
      <rect
        x="2"
        y="2"
        width="28"
        height="28"
        rx="7"
        className="fill-ink-900 stroke-amber-500/30"
        strokeWidth="1.2"
      />
      {/* Vertical architectural pillar */}
      <line
        x1="16"
        y1="7"
        x2="16"
        y2="25"
        stroke="#f59e0b"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
      {/* Upper statutory authority crossbar */}
      <line
        x1="9"
        y1="11"
        x2="23"
        y2="11"
        stroke="#f59e0b"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      {/* Lower judicial precedent balance bar */}
      <line
        x1="11"
        y1="18"
        x2="21"
        y2="18"
        stroke="#818cf8"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      {/* Column base */}
      <line
        x1="10"
        y1="25"
        x2="22"
        y2="25"
        stroke="#f59e0b"
        strokeWidth="1.75"
        strokeLinecap="round"
      />
      {/* Small anchor points representing dual evidence */}
      <circle cx="9" cy="11" r="1.2" fill="#f59e0b" />
      <circle cx="23" cy="11" r="1.2" fill="#f59e0b" />
      <circle cx="11" cy="18" r="1.2" fill="#818cf8" />
      <circle cx="21" cy="18" r="1.2" fill="#818cf8" />
    </svg>
  );
}
