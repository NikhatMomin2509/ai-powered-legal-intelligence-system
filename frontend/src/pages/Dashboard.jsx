import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Scale,
  FileSearch,
  ArrowRight,
  TrendingUp,
  FileWarning,
  FolderCheck,
  Lock,
  ShieldAlert,
  BookOpen,
  CheckCircle2,
  Database,
  GitBranch,
  ShieldCheck,
  HelpCircle,
} from "lucide-react";
import { listIssues, listDocuments } from "../services/api";
import { SkeletonLine } from "../components/ui/Skeleton";
import { useAuth } from "../context/AuthContext";
import SectionHeader from "../components/ui/SectionHeader";
import CitationChip from "../components/ui/CitationChip";

function isHighRisk(doc) {
  const level = (doc?.risk_level || "").toLowerCase();
  const score = Number(doc?.risk_score);
  return level === "high" || (!Number.isNaN(score) && score >= 70);
}

function StatCard({ icon: Icon, label, value, isLoading, isError, accent }) {
  return (
    <div className="p-5 rounded-lg bg-ink-900/80 border border-ink-800 shadow-card">
      <div className="flex items-center justify-between mb-3">
        <div className={`w-9 h-9 rounded-md flex items-center justify-center ${accent.bg}`}>
          <Icon size={16} className={accent.text} />
        </div>
        <span className="text-[10px] font-mono uppercase tracking-wider text-ink-500">
          User Verified
        </span>
      </div>
      {isLoading ? (
        <SkeletonLine width="45%" className="h-7" />
      ) : isError ? (
        <p className="text-sm text-ink-500 font-mono">Unavailable</p>
      ) : (
        <p className="text-3xl font-serif font-medium tracking-tight text-ink-50">{value}</p>
      )}
      <p className="text-xs text-ink-400 mt-1 font-sans">{label}</p>
    </div>
  );
}

export default function Dashboard() {
  const { isAuthenticated } = useAuth();

  const {
    data: issues,
    isLoading: issuesLoading,
    isError: issuesError,
  } = useQuery({ queryKey: ["issues"], queryFn: listIssues, enabled: isAuthenticated });

  const {
    data: documents,
    isLoading: documentsLoading,
    isError: documentsError,
  } = useQuery({ queryKey: ["documents"], queryFn: listDocuments, enabled: isAuthenticated });

  const issueCount = Array.isArray(issues) ? issues.length : 0;
  const documentCount = Array.isArray(documents) ? documents.length : 0;
  const highRiskCount = Array.isArray(documents) ? documents.filter(isHighRisk).length : 0;

  return (
    <div className="space-y-12 max-w-6xl mx-auto pb-8">
      {/* Hero section */}
      <motion.section
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="relative pt-2"
      >
        <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-ink-900 border border-ink-800 text-[11px] font-mono text-ink-400 mb-5">
          <span className="w-1.5 h-1.5 rounded-full bg-accent-500"></span>
          <span>INDIAN JURISDICTION · STATUTORY CITATION GROUNDING</span>
        </div>

        <h1 className="text-3xl sm:text-4xl lg:text-5xl font-serif font-medium tracking-tight text-ink-50 leading-[1.18] max-w-3xl">
          Every legal assessment anchored to statutory authority.
        </h1>

        <p className="mt-4 text-base sm:text-lg text-ink-300 max-w-2xl leading-relaxed">
          A dual-module research instrument for Indian law. Analyze plain-English legal situations
          against verified statutes and Supreme Court precedents, or audit agreements for clause-level
          exposure with plain-English negotiation points.
        </p>

        <div className="mt-7 flex flex-wrap items-center gap-3">
          <Link
            to="/issue-analyzer"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-md bg-accent-600 hover:bg-accent-500 text-white text-sm font-medium transition-colors shadow-sm"
          >
            <Scale size={16} />
            <span>Analyze Legal Issue</span>
            <ArrowRight size={14} />
          </Link>

          <Link
            to="/document-analyzer"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-md bg-ink-900 hover:bg-ink-850 text-ink-200 border border-ink-750 text-sm font-medium transition-colors"
          >
            <FileSearch size={16} className="text-indigo-400" />
            <span>Audit Document Risk</span>
            {!isAuthenticated && <Lock size={13} className="text-ink-500" />}
          </Link>
        </div>
      </motion.section>

      {/* Primary Module Cards */}
      <section className="grid md:grid-cols-2 gap-5">
        <Link to="/issue-analyzer" className="group">
          <div className="p-6 rounded-lg bg-ink-900/90 border border-ink-800 hover:border-accent-500/50 transition-all duration-200 h-full flex flex-col justify-between shadow-card">
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="w-10 h-10 rounded-md bg-accent-500/10 border border-accent-500/20 flex items-center justify-center text-accent-400">
                  <Scale size={18} />
                </div>
                <CitationChip label="Hybrid Retrieval + RAG" variant="accent" />
              </div>
              <h2 className="text-xl font-serif font-medium text-ink-50 mb-2">Legal Issue Analyzer</h2>
              <p className="text-sm text-ink-300 leading-relaxed mb-4">
                Describe a factual dispute in plain English. The system retrieves applicable Indian
                statutes and Supreme Court rulings, verifies all citations against source texts,
                and produces a balanced brief with supporting and opposing considerations.
              </p>
              <ul className="space-y-1.5 text-xs text-ink-400 font-sans border-t border-ink-800/80 pt-3">
                <li className="flex items-center gap-2">
                  <CheckCircle2 size={13} className="text-accent-400 shrink-0" />
                  <span>Cites verified provisions from IPC/BNS, CrPC/BNSS, Contract Act & TPA</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 size={13} className="text-accent-400 shrink-0" />
                  <span>Symmetric supporting & opposing considerations (no outcome prediction)</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 size={13} className="text-accent-400 shrink-0" />
                  <span>Highlights missing factual predicates needed for complete assessment</span>
                </li>
              </ul>
            </div>
            <div className="pt-5 mt-4 border-t border-ink-800/80 flex items-center justify-between text-xs font-medium text-accent-400 group-hover:text-accent-300">
              <span>Start issue brief</span>
              <ArrowRight size={14} className="group-hover:translate-x-1 transition-transform" />
            </div>
          </div>
        </Link>

        <Link to="/document-analyzer" className="group">
          <div className="p-6 rounded-lg bg-ink-900/90 border border-ink-800 hover:border-indigo-500/50 transition-all duration-200 h-full flex flex-col justify-between shadow-card">
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="w-10 h-10 rounded-md bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                  <FileSearch size={18} />
                </div>
                <CitationChip
                  label={isAuthenticated ? "Authenticated Upload" : "Account Required"}
                  variant={isAuthenticated ? "precedent" : "default"}
                />
              </div>
              <h2 className="text-xl font-serif font-medium text-ink-50 mb-2">Document Risk Analyzer</h2>
              <p className="text-sm text-ink-300 leading-relaxed mb-4">
                Upload commercial contracts or tenancy agreements. The analyzer segments clauses,
                evaluates exposure with a rule-based indicative severity index, flags adverse terms,
                and provides practical negotiation counter-proposals.
              </p>
              <ul className="space-y-1.5 text-xs text-ink-400 font-sans border-t border-ink-800/80 pt-3">
                <li className="flex items-center gap-2">
                  <CheckCircle2 size={13} className="text-indigo-400 shrink-0" />
                  <span>Clause-level extraction with OCR fallback for scanned pages</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 size={13} className="text-indigo-400 shrink-0" />
                  <span>Transparent 0–100 indicative score based on clause severity mix</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 size={13} className="text-indigo-400 shrink-0" />
                  <span>Files processed ephemerally and unlinked immediately after analysis</span>
                </li>
              </ul>
            </div>
            <div className="pt-5 mt-4 border-t border-ink-800/80 flex items-center justify-between text-xs font-medium text-indigo-400 group-hover:text-indigo-300">
              <span>{isAuthenticated ? "Upload agreement" : "Sign in to audit documents"}</span>
              <ArrowRight size={14} className="group-hover:translate-x-1 transition-transform" />
            </div>
          </div>
        </Link>
      </section>

      {/* The Evidence Chain / Architecture Diagram */}
      <section className="p-6 sm:p-7 rounded-lg bg-ink-900/60 border border-ink-800 shadow-card">
        <SectionHeader
          title="The Evidence Chain: How Analysis Works"
          subtitle="Every claim is derived from retrieved authority, verified in code, and balanced across both sides."
          icon={GitBranch}
        />

        <div className="mt-6 grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 rounded-md bg-ink-950/80 border border-ink-800/90 relative">
            <div className="text-[11px] font-mono text-accent-400 font-semibold mb-1">01 · INTAKE</div>
            <h4 className="text-sm font-serif font-medium text-ink-100 mb-1.5">Plain-English Query</h4>
            <p className="text-xs text-ink-400 leading-relaxed">
              Factual scenario described in layman terms or raw contract text submitted for audit.
            </p>
          </div>

          <div className="p-4 rounded-md bg-ink-950/80 border border-ink-800/90 relative">
            <div className="text-[11px] font-mono text-accent-400 font-semibold mb-1">02 · RETRIEVAL</div>
            <h4 className="text-sm font-serif font-medium text-ink-100 mb-1.5">Hybrid Indian Law Search</h4>
            <p className="text-xs text-ink-400 leading-relaxed">
              Vector embeddings + BM25 keyword retrieval over indexed Indian statutes and Supreme Court rulings.
            </p>
          </div>

          <div className="p-4 rounded-md bg-ink-950/80 border border-ink-800/90 relative">
            <div className="text-[11px] font-mono text-accent-400 font-semibold mb-1">03 · VERIFICATION</div>
            <h4 className="text-sm font-serif font-medium text-ink-100 mb-1.5">Citation Grounding</h4>
            <p className="text-xs text-ink-400 leading-relaxed">
              Provisions and citations are cross-referenced in code against retrieved texts; fabricated citations are dropped.
            </p>
          </div>

          <div className="p-4 rounded-md bg-ink-950/80 border border-ink-800/90 relative">
            <div className="text-[11px] font-mono text-accent-400 font-semibold mb-1">04 · ASSESSMENT</div>
            <h4 className="text-sm font-serif font-medium text-ink-100 mb-1.5">Balanced Brief</h4>
            <p className="text-xs text-ink-400 leading-relaxed">
              Equal-weight supporting and opposing arguments, missing facts, and remedies with zero outcome prediction.
            </p>
          </div>
        </div>
      </section>

      {/* Two-column layout: What It Will Not Do & Covered Indian Statutes */}
      <section className="grid lg:grid-cols-2 gap-5">
        {/* What this system will not do */}
        <div className="p-6 rounded-lg bg-ink-900/80 border border-ink-800 shadow-card">
          <SectionHeader
            title="System Boundaries & Guardrails"
            subtitle="Clear architectural and legal limitations enforced by design."
            icon={ShieldAlert}
          />
          <div className="mt-5 space-y-3.5 text-xs leading-relaxed text-ink-300">
            <div className="p-3.5 rounded-md bg-ink-950/70 border border-ink-850">
              <span className="font-semibold text-ink-100 block mb-0.5">No Outcome Prediction or Win Rates</span>
              The system never calculates win probabilities, "case strength" meters, or verdict forecasts. Indian judicial proceedings turn heavily on evidentiary admissibility and factual nuances; both supporting and opposing perspectives receive equal presentation.
            </div>
            <div className="p-3.5 rounded-md bg-ink-950/70 border border-ink-850">
              <span className="font-semibold text-ink-100 block mb-0.5">Informational Research, Not Legal Advice</span>
              Assessments are generated to facilitate legal literacy and initial research. They do not constitute attorney-client representation or formal legal opinions.
            </div>
            <div className="p-3.5 rounded-md bg-ink-950/70 border border-ink-850">
              <span className="font-semibold text-ink-100 block mb-0.5">State Rent-Control Exclusion Notice</span>
              The database covers central Indian statutes (including Transfer of Property Act 1882). It does not index state-specific rent control enactments (e.g., Maharashtra Rent Control Act, Delhi Rent Control Act).
            </div>
          </div>
        </div>

        {/* Indexed Statutory Authority */}
        <div className="p-6 rounded-lg bg-ink-900/80 border border-ink-800 shadow-card">
          <SectionHeader
            title="Indexed Statutory Authority"
            subtitle="The verified corpora retrieved by the search engine."
            icon={BookOpen}
          />
          <div className="mt-5 space-y-2.5">
            <div className="p-3 rounded-md bg-ink-950/70 border border-ink-850 flex items-start gap-3">
              <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-statute-bg text-statute-text border border-statute-border shrink-0 mt-0.5">
                PENAL
              </span>
              <div>
                <p className="text-xs font-medium text-ink-100">Indian Penal Code, 1860 & Bharatiya Nyaya Sanhita, 2023</p>
                <p className="text-[11px] text-ink-400 mt-0.5">Substantive criminal offenses, fraud, cheating, and property offenses.</p>
              </div>
            </div>

            <div className="p-3 rounded-md bg-ink-950/70 border border-ink-850 flex items-start gap-3">
              <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-statute-bg text-statute-text border border-statute-border shrink-0 mt-0.5">
                PROCEDURAL
              </span>
              <div>
                <p className="text-xs font-medium text-ink-100">CrPC, 1973 & BNSS, 2023 Arrest Safeguards</p>
                <p className="text-[11px] text-ink-400 mt-0.5">Arrest procedures, notice under Section 41A / Section 35, bail provisions.</p>
              </div>
            </div>

            <div className="p-3 rounded-md bg-ink-950/70 border border-ink-850 flex items-start gap-3">
              <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-statute-bg text-statute-text border border-statute-border shrink-0 mt-0.5">
                CIVIL
              </span>
              <div>
                <p className="text-xs font-medium text-ink-100">Indian Contract Act, 1872 & Transfer of Property Act, 1882</p>
                <p className="text-[11px] text-ink-400 mt-0.5">Contract formation, breach, damages, leases, covenants, and central property rules.</p>
              </div>
            </div>

            <div className="p-3 rounded-md bg-ink-950/70 border border-ink-850 flex items-start gap-3">
              <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-statute-bg text-statute-text border border-statute-border shrink-0 mt-0.5">
                CONSTITUTIONAL
              </span>
              <div>
                <p className="text-xs font-medium text-ink-100">Constitution of India & Supreme Court Precedents</p>
                <p className="text-[11px] text-ink-400 mt-0.5">Articles 14, 19, 21, 22 constitutional guarantees and indexed Supreme Court judgments.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Workspace Activity / Privacy Architecture */}
      <section>
        <SectionHeader
          title={isAuthenticated ? "Workspace Activity" : "Privacy Architecture"}
          subtitle={
            isAuthenticated
              ? "Your authenticated research records and document audits."
              : "How your data is isolated, protected, and permanently deleted."
          }
          icon={isAuthenticated ? Database : ShieldCheck}
        />

        <div className="mt-4">
          {!isAuthenticated ? (
            <div className="p-6 rounded-lg bg-ink-900/80 border border-ink-800 shadow-card flex flex-col sm:flex-row items-start sm:items-center gap-5">
              <div className="w-12 h-12 rounded-lg bg-accent-500/10 border border-accent-500/20 flex items-center justify-center shrink-0 text-accent-400">
                <ShieldCheck size={22} />
              </div>
              <div className="space-y-1.5 flex-1">
                <h3 className="text-sm font-medium text-ink-100">Zero Storage for Anonymous Queries</h3>
                <p className="text-xs text-ink-300 leading-relaxed">
                  Your activity is private to your account. Anonymous analyses are processed in memory and never written to the database. Uploaded contracts are purged immediately after clause extraction.{" "}
                  <Link to="/login" className="text-accent-400 hover:text-accent-300 underline underline-offset-2">
                    Log in
                  </Link>{" "}
                  or{" "}
                  <Link to="/register" className="text-accent-400 hover:text-accent-300 underline underline-offset-2">
                    create an account
                  </Link>{" "}
                  to keep case files and document audits across sessions. You can ask one legal question without signing in.
                </p>
              </div>
            </div>
          ) : (
            <div className="grid sm:grid-cols-3 gap-4">
              <StatCard
                icon={TrendingUp}
                label="Issues analyzed"
                value={issueCount}
                isLoading={issuesLoading}
                isError={issuesError}
                accent={{ bg: "bg-accent-500/10", text: "text-accent-400" }}
              />
              <StatCard
                icon={FolderCheck}
                label="Documents analyzed"
                value={documentCount}
                isLoading={documentsLoading}
                isError={documentsError}
                accent={{ bg: "bg-indigo-500/10", text: "text-indigo-400" }}
              />
              <StatCard
                icon={FileWarning}
                label="High-risk documents"
                value={highRiskCount}
                isLoading={documentsLoading}
                isError={documentsError}
                accent={{ bg: "bg-rose-500/10", text: "text-rose-400" }}
              />
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
