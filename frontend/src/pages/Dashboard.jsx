import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { MessageSquareText, FileSearch, ArrowRight, TrendingUp, FileWarning, FolderCheck } from "lucide-react";
import { listIssues, listDocuments } from "../services/api";
import GlassCard from "../components/ui/GlassCard";
import { SkeletonLine } from "../components/ui/Skeleton";

function isHighRisk(doc) {
  // Defensive: risk_level casing varies by source in this backend; checking
  // both the label and a numeric fallback covers either representation.
  const level = (doc?.risk_level || "").toLowerCase();
  const score = Number(doc?.risk_score);
  return level === "high" || (!Number.isNaN(score) && score >= 70);
}

function StatCard({ icon: Icon, label, value, isLoading, isError, accent }) {
  return (
    <GlassCard className="p-5">
      <div className="flex items-center justify-between mb-3">
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${accent.bg}`}>
          <Icon size={16} className={accent.text} />
        </div>
      </div>
      {isLoading ? (
        <SkeletonLine width="50%" className="h-7" />
      ) : isError ? (
        <p className="text-sm text-zinc-600">Unavailable</p>
      ) : (
        <p className="text-3xl font-semibold tracking-tight text-zinc-50">{value}</p>
      )}
      <p className="text-xs text-zinc-500 mt-1">{label}</p>
    </GlassCard>
  );
}

export default function Dashboard() {
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

  const issueCount = Array.isArray(issues) ? issues.length : 0;
  const documentCount = Array.isArray(documents) ? documents.length : 0;
  const highRiskCount = Array.isArray(documents) ? documents.filter(isHighRisk).length : 0;

  return (
    <div className="space-y-10">
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
        <h1 className="text-4xl md:text-5xl font-serif font-medium tracking-tight text-zinc-50 leading-[1.15]">
          Understand the law.
          <br />
          Understand your risk.
        </h1>
        <p className="mt-4 text-zinc-400 max-w-xl leading-relaxed">
          Evidence-based legal intelligence powered by retrieval-augmented generation.
        </p>
      </motion.div>

      <div className="grid md:grid-cols-2 gap-4">
        <Link to="/issue-analyzer">
          <GlassCard hover className="p-6 h-full group">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mb-4 group-hover:shadow-glow transition-shadow">
              <MessageSquareText size={18} className="text-emerald-400" />
            </div>
            <h3 className="text-lg font-medium text-zinc-100 mb-1.5">Legal Issue Analyzer</h3>
            <p className="text-sm text-zinc-500 leading-relaxed mb-4">
              Describe a legal situation in plain language and retrieve relevant statutes, case
              law, and a structured, evidence-based assessment.
            </p>
            <span className="inline-flex items-center gap-1.5 text-sm text-emerald-400">
              Start analysis <ArrowRight size={14} className="group-hover:translate-x-0.5 transition-transform" />
            </span>
          </GlassCard>
        </Link>

        <Link to="/document-analyzer">
          <GlassCard hover className="p-6 h-full group">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mb-4 group-hover:shadow-glow-indigo transition-shadow">
              <FileSearch size={18} className="text-indigo-400" />
            </div>
            <h3 className="text-lg font-medium text-zinc-100 mb-1.5">Document Risk Analyzer</h3>
            <p className="text-sm text-zinc-500 leading-relaxed mb-4">
              Upload a contract or agreement to surface risky clauses, plain-English explanations,
              and a transparent risk score.
            </p>
            <span className="inline-flex items-center gap-1.5 text-sm text-indigo-400">
              Upload document <ArrowRight size={14} className="group-hover:translate-x-0.5 transition-transform" />
            </span>
          </GlassCard>
        </Link>
      </div>

      <div>
        <h2 className="text-sm font-medium text-zinc-400 mb-3">Workspace activity</h2>
        <div className="grid sm:grid-cols-3 gap-4">
          <StatCard
            icon={TrendingUp}
            label="Issues analyzed"
            value={issueCount}
            isLoading={issuesLoading}
            isError={issuesError}
            accent={{ bg: "bg-emerald-500/10", text: "text-emerald-400" }}
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
      </div>
    </div>
  );
}
