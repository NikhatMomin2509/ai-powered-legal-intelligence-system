import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
  Send,
  Download,
  Scale,
  Gavel,
  ListChecks,
  ShieldCheck,
  Info,
  Briefcase,
  MessageSquarePlus,
  Save,
  HelpCircle,
  BookOpen,
  ScrollText,
  UserCheck,
  AlertCircle,
  FileText,
  ChevronDown,
  ChevronUp,
  ArrowDown,
  Sparkles,
  Loader2,
  FileCheck,
  RotateCcw,
} from "lucide-react";
import {
  analyzeIssue,
  getCase,
  exportCaseReport,
  exportIssueReport,
} from "../services/api";
import { getIssueDomain } from "../services/normalize";
import { useToast } from "../components/ui/Toast";
import { useAuth } from "../context/AuthContext";
import AuthModal from "../components/auth/AuthModal";
import Button from "../components/ui/Button";
import ProcessingSteps from "../components/ui/ProcessingSteps";
import AuthorityCard from "../components/ui/AuthorityCard";
import PrecedentCard from "../components/ui/PrecedentCard";
import Disclaimer from "../components/ui/Disclaimer";
import SectionHeader from "../components/ui/SectionHeader";
import CitationChip from "../components/ui/CitationChip";

const STEPS = [
  { label: "Extracting factual claims" },
  { label: "Querying statutory provisions & precedent vectors" },
  { label: "Verifying citations against Indian law corpus" },
  { label: "Formulating balanced considerations & remedies" },
];

const MIN_LENGTH = 10;
const MAX_LENGTH = 2000;

function filterMissingFacts(facts) {
  if (!Array.isArray(facts)) return [];
  return facts.filter(
    (f) =>
      typeof f === "string" &&
      !f.trim().toLowerCase().startsWith("tenancy and rent-control rules vary significantly by indian state")
  );
}

function formatTurnTime(dateStr) {
  if (!dateStr) return "";
  try {
    const s = dateStr.endsWith("Z") || /[+-]\d{2}/.test(dateStr) ? dateStr : dateStr + "Z";
    const d = new Date(s);
    return (
      d.toLocaleString("en-IN", {
        dateStyle: "medium",
        timeStyle: "short",
        timeZone: "UTC",
      }) + " (UTC)"
    );
  } catch {
    return dateStr;
  }
}

function ConsiderationColumn({ title, subtitle, items, side }) {
  const isSupporting = side === "support";
  return (
    <div className="p-5 rounded-lg bg-ink-900/85 border border-ink-800 shadow-card flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between gap-2 mb-2 pb-2.5 border-b border-ink-800">
          <div className="flex items-center gap-2">
            <span
              className={`w-2 h-2 rounded-full ${
                isSupporting ? "bg-accent-400" : "bg-amber-400"
              }`}
            />
            <h3 className="text-sm font-serif font-medium text-ink-100">{title}</h3>
          </div>
          <span className="text-[10px] font-mono uppercase tracking-wider text-ink-500">
            {isSupporting ? "Proponent Authority" : "Opposing Risk"}
          </span>
        </div>
        <p className="text-[11px] text-ink-400 mb-3.5 leading-normal">{subtitle}</p>

        {Array.isArray(items) && items.length > 0 ? (
          <ul className="space-y-3">
            {items.map((item, i) => (
              <li
                key={i}
                className="text-xs sm:text-[13px] text-ink-200 leading-relaxed flex items-start gap-2.5 p-2.5 rounded bg-ink-950/60 border border-ink-850"
              >
                <span
                  className={`mt-1 w-1.5 h-1.5 rounded-full shrink-0 ${
                    isSupporting ? "bg-accent-400" : "bg-amber-400"
                  }`}
                />
                <span className="flex-1">{item}</span>
              </li>
            ))}
          </ul>
        ) : (
          <div className="p-4 rounded bg-ink-950/50 border border-ink-850 text-xs text-ink-500 italic">
            No specific {isSupporting ? "supporting" : "opposing"} arguments identified in the retrieved context.
          </div>
        )}
      </div>
      <div className="mt-4 pt-3 border-t border-ink-850 text-[11px] font-mono text-ink-500 text-right">
        Weight: Equal evidentiary standing
      </div>
    </div>
  );
}

export default function IssueAnalyzer() {
  const location = useLocation();
  const navigate = useNavigate();
  const { caseId: paramCaseId } = useParams();
  const queryClient = useQueryClient();
  const { isAuthenticated } = useAuth();
  const { showError, showSuccess } = useToast();
  const stepTimerRef = useRef(null);
  const textareaRef = useRef(null);
  const threadEndRef = useRef(null);

  const [query, setQuery] = useState("");
  const [activeStep, setActiveStep] = useState(-1);
  const [announcement, setAnnouncement] = useState("");
  const [showJumpToLatest, setShowJumpToLatest] = useState(false);

  // Turns thread: [{ issue_id, query, created_at, result }]
  const [turns, setTurns] = useState([]);
  const [pendingQuery, setPendingQuery] = useState("");
  const [resultKind, setResultKind] = useState(null); // "anonymous" | "saved"
  const [lastQuery, setLastQuery] = useState("");

  // Case session (authenticated only)
  const effectiveCaseId = paramCaseId ? parseInt(paramCaseId, 10) : location.state?.caseId ?? null;
  const [caseId, setCaseId] = useState(effectiveCaseId);
  const [caseTitle, setCaseTitle] = useState(location.state?.caseTitle ?? null);
  const [loadingCase, setLoadingCase] = useState(false);

  // Expand state for older turns: map of index -> boolean
  const [expandedOlderTurns, setExpandedOlderTurns] = useState({});

  // Export report status: "idle" | "generating" | "done"
  const [exportStatus, setExportStatus] = useState("idle");

  // Anonymous allowance tracked in tab
  const [anonUsed, setAnonUsed] = useState(false);
  const [modal, setModal] = useState({ open: false, mode: "register", message: "" });

  const openAuth = (mode, message = "") => setModal({ open: true, mode, message });
  const closeAuth = () => setModal((m) => ({ ...m, open: false }));

  // Load existing case if deep-linked or refreshed
  useEffect(() => {
    let isMounted = true;
    if (isAuthenticated && effectiveCaseId != null) {
      setCaseId(effectiveCaseId);
      setLoadingCase(true);
      getCase(effectiveCaseId)
        .then((caseData) => {
          if (!isMounted) return;
          if (caseData?.turns && Array.isArray(caseData.turns)) {
            setTurns(caseData.turns);
            setCaseTitle(caseData.title || `Case #${caseData.case_id}`);
            setResultKind("saved");
          }
        })
        .catch((err) => {
          if (!isMounted) return;
          showError(err.message);
        })
        .finally(() => {
          if (isMounted) setLoadingCase(false);
        });
    }
    return () => {
      isMounted = false;
    };
  }, [isAuthenticated, effectiveCaseId, showError]);

  // Scroll detection for "Jump to latest"
  useEffect(() => {
    const handleScroll = () => {
      const isScrolledUp =
        window.innerHeight + window.scrollY < document.documentElement.scrollHeight - 250;
      setShowJumpToLatest(isScrolledUp && (turns.length > 1 || mutation.isPending));
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, [turns.length]);

  const scrollToBottom = (behavior = "smooth") => {
    threadEndRef.current?.scrollIntoView({ behavior });
  };

  const mutation = useMutation({
    mutationFn: ({ text, forCaseId }) => analyzeIssue(text, forCaseId),
    onMutate: (variables) => {
      setPendingQuery(variables.text);
      setActiveStep(0);
      let step = 0;
      stepTimerRef.current = setInterval(() => {
        step += 1;
        if (step < STEPS.length) setActiveStep(step);
      }, 1800);
      // Auto-scroll to show processing
      setTimeout(() => scrollToBottom("smooth"), 100);
    },
    onSuccess: (data, variables) => {
      const newTurn = {
        issue_id: data?.issue_id ?? ("turn-" + Date.now()),
        query: variables.text,
        created_at: new Date().toISOString(),
        result: data,
      };

      setTurns((prev) => [...prev, newTurn]);
      setPendingQuery("");
      setQuery("");

      if (isAuthenticated) {
        setResultKind("saved");
        if (data?.case_id != null) {
          setCaseId(data.case_id);
          setCaseTitle((prev) => prev ?? variables.text);
          // Refresh / deep link safety: update URL to /case/:id
          window.history.replaceState(null, "", `/case/${data.case_id}`);
        }
        queryClient.invalidateQueries({ queryKey: ["issues"] });
        queryClient.invalidateQueries({ queryKey: ["cases"] });
      } else {
        setResultKind("anonymous");
        setAnonUsed(true);
      }

      setAnnouncement("Legal assessment received for your inquiry.");
      setTimeout(() => {
        textareaRef.current?.focus();
        scrollToBottom("smooth");
      }, 150);
    },
    onError: (err, variables) => {
      // Safe failure path: nothing was saved on server. Keep typed text in composer.
      setQuery(variables.text);
      setPendingQuery("");

      if (err.status === 401 && !isAuthenticated) {
        setAnonUsed(true);
        openAuth("register", err.message);
      } else if (err.status === 404 && caseId != null) {
        showError(err.message);
        setCaseId(null);
        setCaseTitle(null);
      } else {
        showError(err.message);
      }
    },
    onSettled: () => {
      clearInterval(stepTimerRef.current);
      setActiveStep(STEPS.length);
    },
  });

  useEffect(() => () => clearInterval(stepTimerRef.current), []);

  const trimmed = query.trim();
  const isValid = trimmed.length >= MIN_LENGTH;
  const needsAccountForNext = !isAuthenticated && anonUsed;

  const submit = (text, forCaseId) => {
    if (needsAccountForNext) {
      openAuth(
        "register",
        "You've already used your one-time anonymous analysis. Create an account or log in to ask follow-up questions."
      );
      return;
    }
    setLastQuery(text);
    mutation.mutate({ text, forCaseId });
  };

  const handleSubmit = () => {
    if (!isValid || mutation.isPending) return;
    submit(trimmed, isAuthenticated ? caseId : null);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const startNewCase = () => {
    setCaseId(null);
    setCaseTitle(null);
    setTurns([]);
    setPendingQuery("");
    setResultKind(null);
    setQuery("");
    navigate("/issue-analyzer", { replace: true });
  };

  const handleExport = async () => {
    if (exportStatus === "generating") return;

    if (!isAuthenticated) {
      // Anonymous one-time result: client-side only print stylesheet.
      // Must NOT hit the server.
      window.print();
      return;
    }

    setExportStatus("generating");
    try {
      if (caseId != null) {
        await exportCaseReport(caseId);
      } else if (turns[0]?.issue_id != null) {
        await exportIssueReport(turns[0].issue_id);
      }
      setExportStatus("done");
      showSuccess("Case brief PDF downloaded successfully.");
      setTimeout(() => setExportStatus("idle"), 3000);
    } catch (err) {
      setExportStatus("idle");
      showError(err.message);
    }
  };

  const latestTurn = turns[turns.length - 1];
  const latestResult = latestTurn?.result;
  const suggestedFollowUps = filterMissingFacts(latestResult?.missing_facts);

  const placeholder = caseId
    ? "Ask a follow-up, e.g. What if he claims that I damaged the apartment?"
    : needsAccountForNext
    ? "Log in or create an account to ask follow-up questions about this case."
    : "e.g. My landlord is refusing to return my security deposit even though I vacated with one month notice and left the apartment in good condition...";

  return (
    <div className="space-y-8 max-w-5xl mx-auto pb-12">
      {/* Screen Reader Announcement */}
      <div className="sr-only" aria-live="polite" aria-atomic="true">
        {announcement}
      </div>

      {/* Page Heading */}
      <div className="border-b border-ink-800 pb-5 no-print">
        <div className="flex items-center gap-2 text-[11px] font-mono text-accent-400 mb-1.5 uppercase tracking-wider">
          <Scale size={13} />
          <span>Statutory Grounding & Precedent Retrieval</span>
        </div>
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div>
            <h1 className="text-2xl sm:text-3xl font-serif font-medium text-ink-50 tracking-tight">
              Legal Issue Analyzer
            </h1>
            <p className="text-sm text-ink-300 mt-1 max-w-2xl leading-relaxed">
              Describe your legal dispute or question in plain language. The system retrieves relevant Indian statutes
              and Supreme Court precedents, verifies citations in code, and synthesizes a balanced legal brief.
            </p>
          </div>

          {turns.length > 0 && (
            <Button
              variant={exportStatus === "generating" ? "disabled" : "ghost"}
              icon={
                exportStatus === "generating"
                  ? Loader2
                  : exportStatus === "done"
                  ? FileCheck
                  : Download
              }
              onClick={handleExport}
              disabled={exportStatus === "generating"}
              className="no-print"
            >
              {exportStatus === "generating"
                ? "Generating PDF..."
                : exportStatus === "done"
                ? "Report downloaded"
                : "Export report"}
            </Button>
          )}
        </div>
      </div>

      {/* Case Continuation Bar & Real Context Notice */}
      {isAuthenticated && caseId != null && (
        <div className="rounded-lg border border-indigo-500/30 bg-indigo-950/20 px-4 py-3 shadow-sm no-print space-y-1.5">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2.5 min-w-0">
              <Briefcase size={15} className="text-indigo-400 shrink-0" />
              <p className="text-xs text-ink-200 truncate">
                <span className="text-zinc-200 font-semibold">Continuing case:</span> {caseTitle || `#${caseId}`}
              </p>
            </div>
            <button
              onClick={startNewCase}
              className="text-xs font-medium text-indigo-300 hover:text-indigo-200 shrink-0 transition-colors underline underline-offset-2"
            >
              Start a new case
            </button>
          </div>
          <p className="text-[11px] text-ink-400 leading-normal">
            Grounding note: Follow-ups incorporate up to the 3 most recent inquiry turns (each up to 400 characters) as context.
          </p>
        </div>
      )}

      {/* Logged-out Anonymous Pre-Submit Notice */}
      {!isAuthenticated && !anonUsed && turns.length === 0 && !mutation.isPending && (
        <div className="flex items-start gap-3 px-2 py-1 no-print">
          <Info size={15} className="text-ink-500 shrink-0 mt-0.5" />
          <p className="text-xs text-ink-400 leading-relaxed">
            No account needed for your first question. An anonymous analysis is one-time only and is not saved —
            it isn&apos;t stored on our servers or added to any history. Follow-up questions require an account.
          </p>
        </div>
      )}

      {/* THREAD VIEW */}
      {turns.length > 0 && (
        <div className="space-y-8">
          {turns.map((turn, index) => {
            const isLatest = index === turns.length - 1;
            const isOlder = !isLatest;
            const isExpanded = isLatest || Boolean(expandedOlderTurns[index]);
            const res = turn.result;

            return (
              <div
                key={turn.issue_id || index}
                className="space-y-4 pt-2 border-t border-ink-850/80 first:border-t-0 first:pt-0"
              >
                {/* User Inquiry Turn */}
                <div className="flex justify-end">
                  <div className="max-w-2xl w-full p-4 sm:p-5 rounded-lg bg-ink-900 border border-ink-800 shadow-card">
                    <div className="flex items-center justify-between gap-2 mb-2 pb-2 border-b border-ink-850 text-xs font-mono text-ink-400">
                      <span className="flex items-center gap-1.5 text-accent-400 font-semibold">
                        <FileText size={13} />
                        <span>Question {index + 1}</span>
                      </span>
                      {turn.created_at && (
                        <span className="text-[11px] text-ink-500">
                          {formatTurnTime(turn.created_at)}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-ink-100 whitespace-pre-wrap leading-relaxed font-sans">
                      {turn.query}
                    </p>
                  </div>
                </div>

                {/* Assistant Turn: Collapsed for older turns, expanded for latest or toggled */}
                {isOlder && !isExpanded ? (
                  <div className="p-4 sm:p-5 rounded-lg bg-ink-900/75 border border-ink-800 shadow-card flex items-start justify-between gap-4">
                    <div className="space-y-2.5 flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <CitationChip
                          label={getIssueDomain(res) || "Indian Legal Assessment"}
                          variant="accent"
                        />
                        <span className="text-[11px] font-mono text-ink-500">
                          Brief Summary · Turn {index + 1}
                        </span>
                      </div>
                      <p className="text-xs sm:text-sm text-ink-200 line-clamp-2 font-serif leading-relaxed">
                        {res?.issue_summary}
                      </p>
                      {Array.isArray(res?.relevant_laws) && res.relevant_laws.length > 0 && (
                        <div className="flex items-center gap-1.5 flex-wrap pt-1">
                          <span className="text-[10px] font-mono text-ink-500 uppercase mr-1">
                            Authorities:
                          </span>
                          {res.relevant_laws.map((law, li) => (
                            <span
                              key={li}
                              className="text-[11px] font-mono px-2 py-0.5 rounded bg-ink-950 border border-ink-800 text-ink-300"
                            >
                              {law?.section ? `${law.section}, ` : ""}
                              {law?.act || "Statute"}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>

                    <button
                      onClick={() =>
                        setExpandedOlderTurns((prev) => ({
                          ...prev,
                          [index]: true,
                        }))
                      }
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-ink-800 hover:bg-ink-750 text-xs font-mono text-ink-200 border border-ink-700 transition-colors shrink-0"
                      aria-expanded={false}
                    >
                      <span>Expand brief</span>
                      <ChevronDown size={14} />
                    </button>
                  </div>
                ) : (
                  /* Full Assessment Card */
                  <div className="space-y-7">
                    {/* Status Banners on Turn */}
                    {resultKind === "anonymous" && isLatest && (
                      <div className="flex items-start gap-3 rounded-lg border border-amber-500/30 bg-amber-950/20 px-4 py-3 shadow-sm no-print">
                        <Info size={16} className="text-amber-400 shrink-0 mt-0.5" />
                        <p className="text-xs text-ink-200 leading-relaxed">
                          <span className="font-semibold text-amber-300">
                            One-time anonymous analysis.
                          </span>{" "}
                          This result is shown only in this browser tab. It was not saved to an account or to any history, and it will be gone if you refresh or close the tab.
                        </p>
                      </div>
                    )}

                    {resultKind === "saved" && isLatest && (
                      <div className="flex items-start gap-3 rounded-lg border border-accent-500/30 bg-accent-950/20 px-4 py-3 shadow-sm no-print">
                        <ShieldCheck size={16} className="text-accent-400 shrink-0 mt-0.5" />
                        <p className="text-xs text-ink-200 leading-relaxed">
                          <span className="font-semibold text-accent-300">
                            Saved to your account{caseId != null ? ` · Case #${caseId}` : ""}.
                          </span>{" "}
                          Only you can see it. Ask a follow-up below and it will be answered in the context of this case.
                        </p>
                      </div>
                    )}

                    {/* Brief Header: Domain & Neutral Summary */}
                    <div className="p-6 rounded-lg bg-ink-900/90 border border-ink-800 shadow-card">
                      <div className="flex items-center justify-between gap-3 flex-wrap mb-4 pb-3 border-b border-ink-800">
                        <div className="flex items-center gap-2">
                          <CitationChip
                            label={getIssueDomain(res) || "Indian Legal Assessment"}
                            variant="accent"
                          />
                          <span className="text-[11px] font-mono text-ink-500">
                            Grounded Research Brief · Turn {index + 1}
                          </span>
                        </div>

                        {isOlder && (
                          <button
                            onClick={() =>
                              setExpandedOlderTurns((prev) => ({
                                ...prev,
                                [index]: false,
                              }))
                            }
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-ink-850 hover:bg-ink-800 text-xs font-mono text-ink-300 border border-ink-750 transition-colors"
                            aria-expanded={true}
                          >
                            <span>Collapse brief</span>
                            <ChevronUp size={14} />
                          </button>
                        )}
                      </div>

                      <div className="prose prose-invert max-w-none">
                        <h2 className="text-xs font-mono uppercase tracking-wider text-ink-400 mb-1.5">
                          Executive Assessment
                        </h2>
                        <p className="text-sm sm:text-base text-ink-100 font-serif leading-relaxed">
                          {res?.issue_summary}
                        </p>
                      </div>
                    </div>

                    {/* Key Facts Identified */}
                    {Array.isArray(res?.key_facts) && res.key_facts.length > 0 && (
                      <div className="p-5 rounded-lg bg-ink-900/80 border border-ink-800 shadow-card">
                        <SectionHeader
                          title="Factual Elements Identified"
                          subtitle="Core factual predicates extracted from your submission."
                          icon={ListChecks}
                        />
                        <ul className="mt-4 grid sm:grid-cols-2 gap-2.5">
                          {res.key_facts.map((fact, fi) => (
                            <li
                              key={fi}
                              className="text-xs text-ink-200 p-2.5 rounded bg-ink-950/60 border border-ink-850 flex items-start gap-2"
                            >
                              <span className="text-accent-400 font-mono text-[11px] shrink-0 mt-0.5">
                                {String(fi + 1).padStart(2, "0")}.
                              </span>
                              <span>{fact}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Section 1: Statutory Authorities Cited */}
                    {Array.isArray(res?.relevant_laws) && res.relevant_laws.length > 0 && (
                      <div className="space-y-3">
                        <SectionHeader
                          title="Statutory Authorities Cited"
                          subtitle="Verified provisions retrieved from Indian statutes. Every citation is grounded in statutory text."
                          icon={BookOpen}
                        />
                        <div className="grid sm:grid-cols-2 gap-3.5">
                          {res.relevant_laws.map((law, li) => (
                            <AuthorityCard key={law?.ref_id || li} law={law} />
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Section 2: Judicial Precedents & Judgments */}
                    {Array.isArray(res?.relevant_cases) && res.relevant_cases.length > 0 && (
                      <div className="space-y-3">
                        <SectionHeader
                          title="Judicial Precedents & Judgments"
                          subtitle="Supreme Court rulings retrieved via hybrid vector and keyword matching. Displayed verbatim."
                          icon={ScrollText}
                        />
                        <div className="grid sm:grid-cols-2 gap-3.5">
                          {res.relevant_cases.map((precedent, pi) => (
                            <PrecedentCard
                              key={precedent?.case_id || pi}
                              precedent={precedent}
                            />
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Section 3: Supporting vs Opposing Considerations (NEVER HIDE OPPOSING) */}
                    <div className="space-y-3">
                      <SectionHeader
                        title="Balanced Evidentiary Considerations"
                        subtitle="Both positions are presented with equal visual and analytical weight. No outcome prediction or win rates are computed."
                        icon={Scale}
                      />
                      <div className="grid md:grid-cols-2 gap-4">
                        <ConsiderationColumn
                          title="Supporting Considerations"
                          subtitle="Factual and statutory arguments supporting your position."
                          items={res?.supporting_considerations}
                          side="support"
                        />
                        <ConsiderationColumn
                          title="Opposing Considerations"
                          subtitle="Counter-arguments, counterparty defenses, and procedural hurdles."
                          items={res?.opposing_considerations}
                          side="oppose"
                        />
                      </div>
                    </div>

                    {/* Section 4: Critical Missing Facts */}
                    {Array.isArray(res?.missing_facts) && res.missing_facts.length > 0 && (
                      <div className="p-5 rounded-lg bg-ink-900/80 border border-ink-800 shadow-card">
                        <SectionHeader
                          title="Critical Missing Factual Predicates"
                          subtitle="Essential facts not provided in your query that could significantly alter legal applicability."
                          icon={HelpCircle}
                        />
                        <ul className="mt-4 space-y-2">
                          {res.missing_facts.map((fact, mi) => (
                            <li
                              key={mi}
                              className="text-xs text-ink-300 p-2.5 rounded bg-ink-950/60 border border-ink-850 flex items-start gap-2.5"
                            >
                              <AlertCircle size={14} className="text-amber-400 shrink-0 mt-0.5" />
                              <span>{fact}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Section 5: Remedies & Lawyer Specialization */}
                    <div className="p-5 sm:p-6 rounded-lg bg-ink-900/90 border border-ink-800 shadow-card">
                      <SectionHeader
                        title="Actionable Remedies & Next Steps"
                        subtitle="Procedural and legal avenues available under Indian law."
                        icon={Gavel}
                      />

                      <div className="mt-4">
                        {Array.isArray(res?.possible_actions_or_remedies) &&
                        res.possible_actions_or_remedies.length > 0 ? (
                          <ol className="space-y-2.5">
                            {res.possible_actions_or_remedies.map((action, ai) => (
                              <li
                                key={ai}
                                className="text-xs sm:text-sm text-ink-200 leading-relaxed flex items-start gap-3 p-3 rounded-md bg-ink-950/70 border border-ink-850"
                              >
                                <span className="font-mono text-xs text-accent-400 font-semibold shrink-0 mt-0.5">
                                  {ai + 1}.
                                </span>
                                <span>{action}</span>
                              </li>
                            ))}
                          </ol>
                        ) : (
                          <p className="text-xs text-ink-500 italic p-3 rounded bg-ink-950/50">
                            No specific remedies identified from the retrieved statutory scope.
                          </p>
                        )}

                        {res?.lawyer_specialization && (
                          <div className="mt-5 pt-4 border-t border-ink-800 flex items-center justify-between flex-wrap gap-2 text-xs">
                            <div className="flex items-center gap-2 text-ink-400">
                              <UserCheck size={14} className="text-accent-400" />
                              <span>Recommended Advocate Practice Area:</span>
                            </div>
                            <span className="px-3 py-1 rounded bg-accent-500/10 border border-accent-500/25 text-accent-300 font-medium">
                              {res.lawyer_specialization}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Anonymous + still logged out: invite to continue */}
                    {resultKind === "anonymous" && isLatest && !isAuthenticated && (
                      <div className="p-6 rounded-lg bg-ink-900/95 border border-accent-500/30 shadow-card no-print">
                        <div className="flex items-center gap-2 mb-1.5">
                          <MessageSquarePlus size={18} className="text-accent-400" />
                          <h3 className="text-base font-serif font-medium text-ink-100">
                            Want to continue exploring this case?
                          </h3>
                        </div>
                        <p className="text-xs sm:text-sm text-ink-300 leading-relaxed">
                          Create an account or log in to save your case and ask follow-up questions.
                          Your first answer above was never stored, so after signing in you can save this case by running it again.
                        </p>
                        <div className="flex flex-wrap gap-3 mt-5">
                          <Button
                            onClick={() =>
                              openAuth(
                                "register",
                                "Create an account to save your case and ask follow-up questions."
                              )
                            }
                          >
                            Create Account
                          </Button>
                          <Button
                            variant="ghost"
                            onClick={() =>
                              openAuth(
                                "login",
                                "Log in to save your case and ask follow-up questions."
                              )
                            }
                          >
                            Log In
                          </Button>
                          <Button
                            variant="ghost"
                            onClick={() =>
                              openAuth(
                                "register",
                                "Follow-up questions need an account. Create one to continue this case."
                              )
                            }
                          >
                            Ask Follow-up Question
                          </Button>
                        </div>
                      </div>
                    )}

                    {/* Anonymous result, but user signed in: honest save step */}
                    {resultKind === "anonymous" && isLatest && isAuthenticated && (
                      <div className="p-6 rounded-lg bg-ink-900/95 border border-accent-500/30 shadow-card no-print">
                        <div className="flex items-center gap-2 mb-1.5">
                          <Save size={18} className="text-accent-400" />
                          <h3 className="text-base font-serif font-medium text-ink-100">
                            You&apos;re signed in — save this case?
                          </h3>
                        </div>
                        <p className="text-xs sm:text-sm text-ink-300 leading-relaxed">
                          The anonymous analysis above was never stored, so there is nothing to transfer. Saving runs the same
                          question again as part of your account; after that you can ask follow-ups. Or just type a new question above to start a different case.
                        </p>
                        <div className="mt-5">
                          <Button icon={Save} onClick={() => submit(lastQuery, null)}>
                            Save this case (re-run analysis)
                          </Button>
                        </div>
                      </div>
                    )}

                    {/* Legal Disclaimer */}
                    <Disclaimer text={res?.disclaimer} />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Pending Assistant Turn Animation */}
      <AnimatePresence>
        {mutation.isPending && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="space-y-4 pt-4 border-t border-ink-850"
          >
            {pendingQuery && (
              <div className="flex justify-end">
                <div className="max-w-2xl w-full p-4 sm:p-5 rounded-lg bg-ink-900 border border-ink-800 shadow-card">
                  <span className="text-[11px] font-mono text-accent-400 block mb-1">
                    Your Pending Inquiry
                  </span>
                  <p className="text-sm text-ink-100 whitespace-pre-wrap">{pendingQuery}</p>
                </div>
              </div>
            )}
            <ProcessingSteps steps={STEPS} activeIndex={activeStep} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Suggested Follow-Ups derived solely from missing_facts (non-hardcoded) */}
      {turns.length > 0 && !mutation.isPending && suggestedFollowUps.length > 0 && (
        <div className="p-4 rounded-lg bg-ink-900/70 border border-ink-800 no-print space-y-2.5">
          <div className="flex items-center gap-1.5 text-xs font-mono text-ink-400">
            <Sparkles size={13} className="text-accent-400" />
            <span>Suggested follow-up points to clarify from missing factual predicates:</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {suggestedFollowUps.map((fact, sidx) => (
              <button
                key={sidx}
                type="button"
                onClick={() => {
                  setQuery((prev) => (prev ? prev + "\n" + fact : fact));
                  textareaRef.current?.focus();
                }}
                className="text-xs text-left px-3 py-1.5 rounded bg-ink-950/80 hover:bg-ink-850 text-ink-200 border border-ink-800 hover:border-accent-500/40 transition-colors"
                title="Click to insert into inquiry composer"
              >
                + {fact}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Anchor for auto-scroll */}
      <div ref={threadEndRef} />

      {/* PINNED COMPOSER AT BOTTOM */}
      <div className="pinned-composer sticky bottom-0 z-20 pt-2 pb-3 bg-ink-950/95 backdrop-blur-md border-t border-ink-800 no-print pb-[env(safe-area-inset-bottom)]">
        <div className="p-4 sm:p-5 rounded-lg bg-ink-900/90 border border-ink-800 shadow-card">
          <div className="flex items-center justify-between mb-2 text-xs font-mono text-ink-400">
            <span className="flex items-center gap-1.5">
              <FileText size={13} className="text-accent-400" />
              <span>
                {turns.length > 0 ? "Follow-up Inquiry Intake" : "Factual Statement Intake"}
              </span>
            </span>
            <span className="text-[11px] text-ink-500">
              Enter to send · Shift+Enter for new line
            </span>
          </div>

          <textarea
            ref={textareaRef}
            value={query}
            onChange={(e) => setQuery(e.target.value.slice(0, MAX_LENGTH))}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            rows={turns.length > 0 ? 3 : 5}
            className="w-full bg-ink-950/70 border border-ink-800 rounded-md p-3 text-sm text-ink-100 placeholder:text-ink-600 focus:outline-none focus:border-accent-500/60 leading-relaxed resize-none"
            disabled={mutation.isPending || loadingCase}
            aria-label="Legal issue inquiry text"
          />

          <div className="flex items-center justify-between mt-3 pt-3 border-t border-ink-850 gap-3 flex-wrap">
            <span className={`text-xs font-mono ${isValid ? "text-ink-400" : "text-ink-500"}`}>
              {trimmed.length}/{MAX_LENGTH} characters
              {!isValid && trimmed.length > 0 && ` · minimum ${MIN_LENGTH}`}
            </span>
            <Button
              onClick={handleSubmit}
              disabled={!isValid || mutation.isPending || loadingCase}
              icon={Send}
            >
              {mutation.isPending
                ? "Analyzing..."
                : needsAccountForNext
                ? "Ask follow-up (account required)"
                : turns.length > 0 || caseId
                ? "Ask follow-up"
                : "Analyze issue"}
            </Button>
          </div>
        </div>
      </div>

      {/* Floating Jump to Latest Button */}
      {showJumpToLatest && (
        <button
          onClick={() => scrollToBottom("smooth")}
          className="jump-to-latest fixed bottom-28 right-6 z-30 px-3.5 py-2 rounded-full bg-accent-600 hover:bg-accent-500 text-white text-xs font-medium shadow-lg flex items-center gap-1.5 transition-all no-print active:scale-95 border border-accent-400/40"
          aria-label="Jump to latest inquiry turn"
        >
          <ArrowDown size={14} />
          <span>Jump to latest</span>
        </button>
      )}

      {/* Auth Modal */}
      <AuthModal
        open={modal.open}
        initialMode={modal.mode}
        message={modal.message}
        onClose={closeAuth}
        onSuccess={() => {
          closeAuth();
          setAnonUsed(false);
        }}
      />
    </div>
  );
}
