const VARIANTS = {
  primary:
    "bg-emerald-500 text-zinc-950 hover:bg-emerald-400 shadow-glow font-medium",
  ghost: "bg-white/5 text-zinc-200 hover:bg-white/10 border border-white/10",
  disabled: "bg-white/5 text-zinc-500 border border-white/5 cursor-not-allowed",
};

export default function Button({
  children,
  variant = "primary",
  disabled = false,
  className = "",
  icon: Icon,
  ...props
}) {
  const style = disabled ? VARIANTS.disabled : VARIANTS[variant];
  return (
    <button
      disabled={disabled}
      className={`inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm transition-all duration-200 ${
        !disabled && "active:scale-[0.98]"
      } ${style} ${className}`}
      {...props}
    >
      {Icon && <Icon size={16} />}
      {children}
    </button>
  );
}
