import { useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
  Briefcase,
  FileText,
  ChevronDown,
  Inbox,
  Lock,
  MessageSquarePlus,
  FolderOpen,
  Calendar,
  Layers,
  ArrowRight,
  ShieldCheck,
} from "lucide-react";
import { listIssues, listDocuments, getIssue, getDocument } from "../services/api";
import { getIssueDomain } from "../services/normalize";
import { useAuth } from "../context/AuthContext";
import RiskBadge from "../components/ui/RiskBadge";
import { SkeletonGrid } from "../components/ui/Skeleton";
import AuthorityCard from "../components/ui/AuthorityCard";
import ClauseAccordion from "../components/ui/ClauseAccordion";
import SectionHeader from "../components/ui/SectionHeader";
import CitationChip from "../components/ui/CitationChip";

const TABS = [
  { key: "all", label: "All Records" },
  { key: "issue", label: "Cases" },
  { key: "document", label: "Documents" },
];

function IssueDetail({ id }) {
  const { data, isLoading } = useQuery({
    queryKey: ["issue-detail", id],
    queryFn: () => getIssue(id),
  });
  if (isLoading) return <SkeletonGrid count={1} lines={3} />;
  if (!data) return null;
  return (
    <div className="space-y-4 px-1 py-2">
      <div className="p-3.5 rounded bg-ink-950/70 border border-ink-850">
        <span className="text-[10px] font-mono uppercase text-ink-400 block mb-1">
          Synthesized Brief
        </span>
        <p className="text-xs sm:text-sm text-ink-100 font-serif leading-relaxed">
          {data?.issue_summary}
        </p>
      </div>

      {Array.isArray(data?.relevant_laws) && data.relevant_laws.length > 0 && (
        <div>
          <span className="text-[11px] font-mono text-ink-400 block mb-2">
            Grounded Statutory Authorities:
          </span>
          <div className="grid sm:grid-cols-2 gap-2.5">
            {data.relevant_laws.map((law, i) => (
              <AuthorityCard key={law?.ref_id || i} law={law} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function DocumentDetail({ id }) {
  const { data, isLoading } = useQuery({
    queryKey: ["document-detail", id],
    queryFn: () => getDocument(id),
  });
  if (isLoading) return <SkeletonGrid count={1} lines={3} />;
  if (!data) return null;
  const clauses = Array.isArray(data?.risky_clauses) ? data.risky_clauses : [];
  return (
    <div className="space-y-3.5 px-1 py-2">
      <div className="p-3.5 rounded bg-ink-950/70 border border-ink-850">
        <span className="text-[10px] font-mono uppercase text-ink-400 block mb-1">
          Executive Audit Summary
        </span>
        <p className="text-xs sm:text-sm text-ink-200 font-serif leading-relaxed">
          {data?.summary}
        </p>
      </div>

      {clauses.length > 0 && (
        <div>
          <span className="text-[11px] font-mono text-ink-400 block mb-2">
            Flagged Clauses & Negotiation Points:
          </span>
          <div className="space-y-2.5">
            {clauses.map((clause, i) => (
              <ClauseAccordion key={clause?.clause_id || i} clause={clause} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function CaseTurn({ turn, index }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-md border border-ink-800 bg-ink-950/50 overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-ink-850/50 transition-colors"
      >
        <span className="text-xs font-mono text-accent-400 font-semibold shrink-0 w-7">
          Q{index + 1}
        </span>
        <span className="text-xs sm:text-sm text-ink-100 truncate flex-1 font-sans">
          {turn.query}
        </span>
        <motion.div animate={{ rotate: open ? 180 : 0 }} transition={{ duration: 0.2 }}>
          <ChevronDown size={15} className="text-ink-400" />
        </motion.div>
      </button>
      {open && (
        <div className="px-4 pb-4 pt-1 border-t border-ink-850 bg-ink-950/80">
          <IssueDetail id={turn.id} />
        </div>
      )}
    </div>
  );
}

function CaseDetail({ item }) {
  const navigate = useNavigate();
  return (
    <div className="space-y-3">
      <div className="space-y-2">
        {item.turns.map((turn, i) => (
          <CaseTurn key={turn.id} turn={turn} index={i} />
        ))}
      </div>
      {item.caseId != null && (
        <div className="pt-2 flex justify-end">
          <button
            onClick={() =>
              navigate("/issue-analyzer", {
                state: { caseId: item.caseId, caseTitle: item.title },
              })
            }
            className="inline-flex items-center gap-2 px-4 py-2 rounded-md text-xs font-medium text-white bg-accent-600 hover:bg-accent-500 transition-colors shadow-sm"
          >
            <MessageSquarePlus size={14} />
            <span>Continue this case</span>
          </button>
        </div>
      )}
    </div>
  );
}

export default function History() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const requested = searchParams.get("tab");
  const tab = TABS.some((t) => t.key === requested) ? requested : "all";
  const [expandedKey, setExpandedKey] = useState(null);

  // Authenticated-only queries
  const issuesQ = useQuery({
    queryKey: ["issues"],
    queryFn: listIssues,
    enabled: isAuthenticated,
  });
  const documentsQ = useQuery({
    queryKey: ["documents"],
    queryFn: listDocuments,
    enabled: isAuthenticated,
  });

  const unified = useMemo(() => {
    const groups = new Map();
    (Array.isArray(issuesQ.data) ? issuesQ.data : []).forEach((it) => {
      const key = it.case_id != null ? `case-${it.case_id}` : `issue-${it.id}`;
      if (!groups.has(key)) groups.set(key, { key, caseId: it.case_id ?? null, turns: [] });
      groups.get(key).turns.push(it);
    });
    const caseItems = [...groups.values()].map((g) => {
      const turns = [...g.turns].sort(
        (a, b) =>
          new Date(a.created_at || 0) - new Date(b.created_at || 0) || a.id - b.id
      );
      const latest = turns[turns.length - 1];
      return {
        type: "issue",
        key: g.key,
        caseId: g.caseId,
        turns,
        title: turns[0].query,
        subtitle: `${getIssueDomain(latest)} · ${turns.length} question${
          turns.length > 1 ? "s" : ""
        }`,
        created_at: latest.created_at,
      };
    });
    const documentItems = (Array.isArray(documentsQ.data) ? documentsQ.data : []).map(
      (item) => ({
        type: "document",
        key: `document-${item.document_id}`,
        id: item.document_id,
        title: item.filename,
        subtitle: item.document_type || "Unclassified",
        risk_level: item.risk_level,
        created_at: item.created_at,
      })
    );
    return [...caseItems, ...documentItems].sort(
      (a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0)
    );
  }, [issuesQ.data, documentsQ.data]);

  if (authLoading) return <SkeletonGrid count={3} lines={1} />;

  if (!isAuthenticated) {
    return (
      <div className="space-y-8 max-w-4xl mx-auto pb-8">
        <div className="border-b border-ink-800 pb-5">
          <div className="flex items-center gap-2 text-[11px] font-mono text-ink-400 mb-1.5 uppercase tracking-wider">
            <FolderOpen size={13} />
            <span>Encrypted Case Archive</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-serif font-medium text-ink-50 tracking-tight">
            Analysis History
          </h1>
        </div>

        <div className="p-8 sm:p-12 rounded-lg bg-ink-900/90 border border-ink-800 shadow-card flex flex-col items-center text-center max-w-xl mx-auto">
          <div className="w-14 h-14 rounded-lg bg-ink-800/80 border border-ink-700 flex items-center justify-center mb-5 text-ink-400">
            <Lock size={22} />
          </div>
          <h2 className="text-xl font-serif font-medium text-ink-50 tracking-tight">
            History requires an account
          </h2>
          <p className="text-xs sm:text-sm text-ink-300 mt-2.5 leading-relaxed max-w-md">
            Anonymous analyses are not saved anywhere, so there is no history to show. Log in or create an
            account to keep your cases and document analyses — visible only to you.
          </p>
          <div className="flex items-center gap-3 mt-7">
            <Link
              to="/login"
              state={{ from: "/history" }}
              className="px-5 py-2.5 rounded-md text-xs sm:text-sm font-medium text-ink-200 bg-ink-800 hover:bg-ink-750 border border-ink-700 transition-colors"
            >
              Log in
            </Link>
            <Link
              to="/register"
              state={{ from: "/history" }}
              className="px-5 py-2.5 rounded-md text-xs sm:text-sm font-medium text-white bg-accent-600 hover:bg-accent-500 transition-colors shadow-sm"
            >
              Create Account
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const isLoading = issuesQ.isLoading || documentsQ.isLoading;
  const isError = issuesQ.isError || documentsQ.isError;
  const filtered = tab === "all" ? unified : unified.filter((item) => item.type === tab);

  return (
    <div className="space-y-7 max-w-5xl mx-auto pb-8">
      {/* Page Header */}
      <div className="border-b border-ink-800 pb-5">
        <div className="flex items-center gap-2 text-[11px] font-mono text-accent-400 mb-1.5 uppercase tracking-wider">
          <FolderOpen size={13} />
          <span>Case Files & Document Audits</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-serif font-medium text-ink-50 tracking-tight">
          Analysis History
        </h1>
        <p className="text-sm text-ink-300 mt-1 max-w-2xl leading-relaxed">
          Your archived case briefs and audited agreements, newest activity first. Strict cryptographic isolation ensures these are visible only to your authenticated workspace.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1.5 p-1 rounded-md bg-ink-900 border border-ink-800 max-w-fit">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setSearchParams(t.key === "all" ? {} : { tab: t.key })}
            className={`px-3.5 py-1.5 rounded text-xs font-medium transition-colors ${
              tab === t.key
                ? "bg-accent-600 text-white shadow-sm"
                : "text-ink-400 hover:text-ink-200"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Content states: loading, error, empty, list */}
      {isLoading ? (
        <SkeletonGrid count={4} lines={1} />
      ) : isError ? (
        <div className="p-12 rounded-lg bg-ink-900/80 border border-ink-800 text-center shadow-card">
          <Inbox size={32} className="text-ink-600 mx-auto mb-3" />
          <h3 className="text-sm font-medium text-ink-200">Could not load history</h3>
          <p className="text-xs text-ink-400 mt-1 max-w-md mx-auto">
            Confirm the backend is reachable and try again.
          </p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="p-12 rounded-lg bg-ink-900/80 border border-ink-800 text-center shadow-card">
          <Inbox size={32} className="text-ink-600 mx-auto mb-3" />
          <p className="text-sm text-ink-300 font-medium">Nothing here yet.</p>
          <p className="text-xs text-ink-400 mt-1 max-w-md mx-auto">
            Analyze an issue or a document and it will appear in your history.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((item) => {
            const isExpanded = expandedKey === item.key;
            const Icon = item.type === "issue" ? Briefcase : FileText;
            return (
              <div
                key={item.key}
                className="rounded-lg bg-ink-900/85 border border-ink-800 shadow-card overflow-hidden transition-colors"
              >
                <button
                  onClick={() => setExpandedKey(isExpanded ? null : item.key)}
                  className="w-full flex items-center gap-3.5 p-4 text-left hover:bg-ink-850/50 transition-colors"
                >
                  <div
                    className={`w-9 h-9 rounded-md flex items-center justify-center shrink-0 ${
                      item.type === "issue"
                        ? "bg-accent-500/10 text-accent-400 border border-accent-500/20"
                        : "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20"
                    }`}
                  >
                    <Icon size={16} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-ink-100 truncate">
                      {item.title || "Untitled"}
                    </p>
                    <p className="text-xs text-ink-400 mt-0.5 font-mono">{item.subtitle}</p>
                  </div>
                  {item.type === "document" && item.risk_level && (
                    <RiskBadge level={item.risk_level} />
                  )}
                  <span className="text-xs font-mono text-ink-500 shrink-0 hidden sm:block">
                    {item.created_at ? new Date(item.created_at).toLocaleDateString() : ""}
                  </span>
                  <motion.div
                    animate={{ rotate: isExpanded ? 180 : 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    <ChevronDown size={16} className="text-ink-400" />
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
                      <div className="p-4 pt-3 border-t border-ink-800 bg-ink-950/40">
                        {item.type === "issue" ? (
                          <CaseDetail item={item} />
                        ) : (
                          <DocumentDetail id={item.id} />
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
