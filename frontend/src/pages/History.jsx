import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { MessageSquareText, FileText, ChevronDown, Inbox } from "lucide-react";
import { listIssues, listDocuments, getIssue, getDocument } from "../services/api";
import { getIssueDomain } from "../services/normalize";
import GlassCard from "../components/ui/GlassCard";
import RiskBadge from "../components/ui/RiskBadge";
import { SkeletonGrid } from "../components/ui/Skeleton";
import AuthorityCard from "../components/ui/AuthorityCard";
import ClauseAccordion from "../components/ui/ClauseAccordion";

const TABS = [
  { key: "all", label: "All" },
  { key: "issue", label: "Issues" },
  { key: "document", label: "Documents" },
];

function IssueDetail({ id }) {
  const { data, isLoading } = useQuery({ queryKey: ["issue-detail", id], queryFn: () => getIssue(id) });
  if (isLoading) return <SkeletonGrid count={1} lines={3} />;
  if (!data) return null;
  return (
    <div className="space-y-4 px-1">
      <p className="text-sm text-zinc-300 leading-relaxed">{data?.issue_summary}</p>
      {Array.isArray(data?.relevant_laws) && data.relevant_laws.length > 0 && (
        <div className="grid sm:grid-cols-2 gap-2.5">
          {data.relevant_laws.map((law, i) => (
            <AuthorityCard key={law?.ref_id || i} law={law} />
          ))}
        </div>
      )}
    </div>
  );
}

function DocumentDetail({ id }) {
  const { data, isLoading } = useQuery({ queryKey: ["document-detail", id], queryFn: () => getDocument(id) });
  if (isLoading) return <SkeletonGrid count={1} lines={3} />;
  if (!data) return null;
  const clauses = Array.isArray(data?.risky_clauses) ? data.risky_clauses : [];
  return (
    <div className="space-y-3 px-1">
      <p className="text-sm text-zinc-400 leading-relaxed">{data?.summary}</p>
      {clauses.map((clause, i) => (
        <ClauseAccordion key={clause?.clause_id || i} clause={clause} />
      ))}
    </div>
  );
}

export default function History() {
  const [tab, setTab] = useState("all");
  const [expandedKey, setExpandedKey] = useState(null);

  const {
    data: issues,
    isLoading: issuesLoading,
    isError: issuesError,
  } = useQuery({ queryKey: ["issues"], queryFn: listIssues });
  const {
    data: documents,
    isLoading: documentsLoading,
    isError: documentsError,
  } = useQuery({ queryKey: ["documents"], queryFn: listDocuments });

  const isLoading = issuesLoading || documentsLoading;
  const isError = issuesError || documentsError;

  const unified = useMemo(() => {
    const issueItems = (Array.isArray(issues) ? issues : []).map((item) => ({
      type: "issue",
      key: `issue-${item.id}`,
      id: item.id,
      title: item.query,
      subtitle: getIssueDomain(item),
      created_at: item.created_at,
    }));
    const documentItems = (Array.isArray(documents) ? documents : []).map((item) => ({
      type: "document",
      key: `document-${item.document_id}`,
      id: item.document_id,
      title: item.filename,
      subtitle: item.document_type || "Unclassified",
      risk_level: item.risk_level,
      created_at: item.created_at,
    }));
    return [...issueItems, ...documentItems].sort(
      (a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0)
    );
  }, [issues, documents]);

  const filtered = tab === "all" ? unified : unified.filter((item) => item.type === tab);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-medium text-zinc-50 tracking-tight">Analysis History</h1>
        <p className="text-sm text-zinc-500 mt-1">Every issue and document analysis, newest first.</p>
      </div>

      <div className="flex gap-1.5">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-3.5 py-1.5 rounded-lg text-sm transition-colors ${
              tab === t.key ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/25" : "text-zinc-500 hover:text-zinc-300 border border-transparent"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <SkeletonGrid count={4} lines={1} />
      ) : isError ? (
        <GlassCard className="p-12 flex flex-col items-center text-center">
          <Inbox size={28} className="text-zinc-700 mb-3" />
          <p className="text-sm text-zinc-500">Could not load history. Confirm the backend is reachable and try again.</p>
        </GlassCard>
      ) : filtered.length === 0 ? (
        <GlassCard className="p-12 flex flex-col items-center text-center">
          <Inbox size={28} className="text-zinc-700 mb-3" />
          <p className="text-sm text-zinc-500">No analyses yet. Run an issue or document analysis to see it here.</p>
        </GlassCard>
      ) : (
        <div className="space-y-2.5">
          {filtered.map((item) => {
            const isExpanded = expandedKey === item.key;
            const Icon = item.type === "issue" ? MessageSquareText : FileText;
            return (
              <GlassCard key={item.key} className="overflow-hidden">
                <button
                  onClick={() => setExpandedKey(isExpanded ? null : item.key)}
                  className="w-full flex items-center gap-3 p-4 text-left hover:bg-white/[0.03] transition-colors"
                >
                  <div
                    className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${
                      item.type === "issue" ? "bg-emerald-500/10 text-emerald-400" : "bg-indigo-500/10 text-indigo-400"
                    }`}
                  >
                    <Icon size={15} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-zinc-200 truncate">{item.title || "Untitled"}</p>
                    <p className="text-xs text-zinc-500 mt-0.5">{item.subtitle}</p>
                  </div>
                  {item.type === "document" && item.risk_level && <RiskBadge level={item.risk_level} />}
                  <span className="text-xs text-zinc-600 shrink-0 hidden sm:block">
                    {item.created_at ? new Date(item.created_at).toLocaleString() : ""}
                  </span>
                  <motion.div animate={{ rotate: isExpanded ? 180 : 0 }} transition={{ duration: 0.2 }}>
                    <ChevronDown size={16} className="text-zinc-500" />
                  </motion.div>
                </button>

                <AnimatePresence initial={false}>
                  {isExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.25 }}
                      className="overflow-hidden"
                    >
                      <div className="p-4 pt-1 border-t border-white/[0.06]">
                        {item.type === "issue" ? <IssueDetail id={item.id} /> : <DocumentDetail id={item.id} />}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </GlassCard>
            );
          })}
        </div>
      )}
    </div>
  );
}
