import { Scale } from "lucide-react";

/**
 * Renders one retrieved law. Defensive by necessity: the issue analyzer's
 * relevant_laws include why_relevant/category/retrieval_score; a document
 * clause's relevant_laws only have {act, section, title, content} — every
 * field below is optional-chained with a fallback, never assumed present.
 */
export default function AuthorityCard({ law }) {
  if (!law) return null;
  return (
    <div className="rounded-xl border border-authority/20 bg-authority/[0.04] p-4">
      <div className="flex items-start gap-2.5">
        <Scale size={15} className="text-authority shrink-0 mt-0.5" />
        <div className="min-w-0">
          <p className="text-sm font-medium text-zinc-100">
            {law?.act || "Unnamed Act"}
            {law?.section ? ` · Section ${law.section}` : ""}
          </p>
          {law?.title && <p className="text-xs text-zinc-400 mt-0.5">{law.title}</p>}
          {law?.why_relevant && (
            <p className="text-xs text-zinc-500 mt-2 leading-relaxed">{law.why_relevant}</p>
          )}
          {!law?.why_relevant && law?.content && (
            <p className="text-xs text-zinc-500 mt-2 leading-relaxed line-clamp-3">{law.content}</p>
          )}
        </div>
      </div>
    </div>
  );
}
