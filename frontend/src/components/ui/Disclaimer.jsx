import { ShieldAlert } from "lucide-react";

export default function Disclaimer({ text }) {
  const fallback =
    "This is an AI-generated, informational assessment. It is not legal advice and does not " +
    "substitute for consultation with a qualified advocate.";
  return (
    <div className="glass rounded-2xl p-4 flex gap-3 items-start border-amber-500/10">
      <ShieldAlert size={18} className="text-amber-400/80 shrink-0 mt-0.5" />
      <p className="text-xs leading-relaxed text-zinc-400">{text || fallback}</p>
    </div>
  );
}
