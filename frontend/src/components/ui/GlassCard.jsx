export default function GlassCard({ children, className = "", hover = false, as: Component = "div", ...props }) {
  return (
    <Component
      className={`glass rounded-2xl ${hover ? "glass-hover hover:-translate-y-0.5" : ""} ${className}`}
      {...props}
    >
      {children}
    </Component>
  );
}
