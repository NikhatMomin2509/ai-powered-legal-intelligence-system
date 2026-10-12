import { useCallback, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { Link } from "react-router-dom";
import {
  UploadCloud,
  FileText,
  X,
  Download,
  AlertTriangle,
  FileSearch,
  Lock,
  ShieldCheck,
  FileCheck,
  RotateCcw,
  Loader2,
} from "lucide-react";
import { uploadDocument, analyzeDocument, exportDocumentReport } from "../services/api";
import { useToast } from "../components/ui/Toast";
import { useAuth } from "../context/AuthContext";
import { SkeletonGrid } from "../components/ui/Skeleton";
import Button from "../components/ui/Button";
import ProcessingSteps from "../components/ui/ProcessingSteps";
import RiskGauge from "../components/ui/RiskGauge";
import ClauseAccordion from "../components/ui/ClauseAccordion";
import Disclaimer from "../components/ui/Disclaimer";
import SectionHeader from "../components/ui/SectionHeader";
import CitationChip from "../components/ui/CitationChip";

const STEPS = [
  { label: "Uploading document" },
  { label: "Extracting text layer & OCR processing" },
  { label: "Segmenting contractual clauses" },
  { label: "Detecting risk patterns & indemnity clauses" },
  { label: "Retrieving applicable statutory authorities" },
];

const ACCEPTED_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg"];
const MAX_SIZE_BYTES = 20 * 1024 * 1024;

function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function DocumentAnalyzer() {
  const [file, setFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [activeStep, setActiveStep] = useState(-1);
  const [result, setResult] = useState(null);
  const [exportStatus, setExportStatus] = useState("idle"); // "idle" | "generating" | "done"
  const fileInputRef = useRef(null);
  const { showError, showSuccess } = useToast();
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  const handleExport = async () => {
    if (!result?.document_id || exportStatus === "generating") return;
    setExportStatus("generating");
    try {
      await exportDocumentReport(result.document_id);
      setExportStatus("done");
      showSuccess("Document audit PDF downloaded successfully.");
      setTimeout(() => setExportStatus("idle"), 3000);
    } catch (err) {
      setExportStatus("idle");
      showError(err.message);
    }
  };

  const pipeline = useMutation({
    mutationFn: async (selectedFile) => {
      setActiveStep(0);
      const uploadRes = await uploadDocument(selectedFile);
      setActiveStep(1);
      // Steps 1-4 happen server-side; progress through general indicators
      const stepTimer = setInterval(() => {
        setActiveStep((s) => (s < STEPS.length - 1 ? s + 1 : s));
      }, 1500);
      try {
        const analysis = await analyzeDocument(uploadRes.document_id);
        return analysis;
      } finally {
        clearInterval(stepTimer);
      }
    },
    onSuccess: (data) => {
      setResult(data);
      setActiveStep(STEPS.length);
    },
    onError: (err) => {
      showError(err.message);
      setActiveStep(-1);
    },
  });

  const validateAndSetFile = useCallback(
    (candidate) => {
      if (!candidate) return;
      const ext = "." + candidate.name.split(".").pop().toLowerCase();
      if (!ACCEPTED_EXTENSIONS.includes(ext)) {
        showError(`Unsupported file type "${ext}". Accepted: ${ACCEPTED_EXTENSIONS.join(", ")}`);
        return;
      }
      if (candidate.size > MAX_SIZE_BYTES) {
        showError("File too large. Maximum size is 20 MB.");
        return;
      }
      setFile(candidate);
      setResult(null);
    },
    [showError]
  );

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    validateAndSetFile(e.dataTransfer.files?.[0]);
  };

  const handleRemove = () => {
    setFile(null);
    setResult(null);
    pipeline.reset();
    setActiveStep(-1);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleAnalyze = () => {
    if (!file) return;
    pipeline.mutate(file);
  };

  // Logged-out gating: NO input[type=file] is in the DOM
  if (authLoading) return <SkeletonGrid count={1} lines={3} />;

  if (!isAuthenticated) {
    return (
      <div className="space-y-8 max-w-4xl mx-auto pb-8">
        <div className="border-b border-ink-800 pb-5">
          <div className="flex items-center gap-2 text-[11px] font-mono text-indigo-400 mb-1.5 uppercase tracking-wider">
            <Lock size={13} />
            <span>Encrypted Per-User Isolation</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-serif font-medium text-ink-50 tracking-tight">
            Document Risk Analyzer
          </h1>
        </div>

        <div className="p-8 sm:p-12 rounded-lg bg-ink-900/90 border border-ink-800 shadow-card flex flex-col items-center text-center max-w-xl mx-auto">
          <div className="w-14 h-14 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mb-5 text-indigo-400">
            <Lock size={24} />
          </div>
          <h2 className="text-xl font-serif font-medium text-ink-50 tracking-tight">
            Secure document analysis
          </h2>
          <p className="text-ink-300 mt-2 text-sm">
            Sign in to analyze confidential legal documents.
          </p>
          <p className="text-xs text-ink-400 mt-3 leading-relaxed max-w-md">
            Contracts can contain sensitive party identities, liability covenants, and financial details.
            Document analysis requires an authenticated account to guarantee strict per-user cryptographic isolation.
            Uploaded original files are unlinked from the server immediately after clause extraction.
          </p>
          <div className="flex items-center gap-3 mt-7">
            <Link
              to="/login"
              state={{ from: "/document-analyzer" }}
              className="px-5 py-2.5 rounded-md text-xs sm:text-sm font-medium text-ink-200 bg-ink-800 hover:bg-ink-750 border border-ink-700 transition-colors"
            >
              Log in
            </Link>
            <Link
              to="/register"
              state={{ from: "/document-analyzer" }}
              className="px-5 py-2.5 rounded-md text-xs sm:text-sm font-medium text-white bg-accent-600 hover:bg-accent-500 transition-colors shadow-sm"
            >
              Create Account
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-5xl mx-auto pb-8">
      {/* Page Header */}
      <div className="border-b border-ink-800 pb-5">
        <div className="flex items-center gap-2 text-[11px] font-mono text-indigo-400 mb-1.5 uppercase tracking-wider">
          <FileSearch size={13} />
          <span>Clause-Level Risk Audit & Negotiation Points</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-serif font-medium text-ink-50 tracking-tight">
          Document Risk Analyzer
        </h1>
        <p className="text-sm text-ink-300 mt-1 max-w-2xl leading-relaxed">
          Upload an agreement or contract (PDF or image). The system extracts clauses via native text
          layers or OCR, identifies adverse terms using rule-based risk patterns, and provides balanced
          negotiation counter-proposals.
        </p>
      </div>

      {/* Pre-Upload Privacy Notice */}
      {!result && (
        <div className="flex items-start gap-3 rounded-lg border border-accent-500/30 bg-accent-950/20 px-4 py-3 shadow-sm">
          <ShieldCheck size={18} className="text-accent-400 shrink-0 mt-0.5" />
          <p className="text-xs text-ink-300 leading-relaxed">
            Your original document is processed temporarily and is not retained by default.
            The analysis result is saved to your account so you can reopen it from History.
          </p>
        </div>
      )}

      {/* Upload Dropzone */}
      {!result && (
        <div className="rounded-lg bg-ink-900/90 border border-ink-800 shadow-card overflow-hidden">
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            onClick={() => !file && fileInputRef.current?.click()}
            className={`p-10 sm:p-14 flex flex-col items-center justify-center text-center transition-all duration-200 ${
              !file ? "cursor-pointer" : ""
            } ${
              isDragging
                ? "bg-accent-500/10 border-2 border-dashed border-accent-400"
                : "border-2 border-dashed border-ink-750 hover:border-ink-650"
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept={ACCEPTED_EXTENSIONS.join(",")}
              className="hidden"
              onChange={(e) => validateAndSetFile(e.target.files?.[0])}
            />

            {!file ? (
              <>
                <div
                  className={`w-14 h-14 rounded-lg flex items-center justify-center mb-4 border transition-colors ${
                    isDragging
                      ? "bg-accent-500/20 border-accent-400 text-accent-300"
                      : "bg-ink-950 border-ink-800 text-ink-400"
                  }`}
                >
                  <UploadCloud size={24} />
                </div>
                <p className="text-sm font-medium text-ink-100">
                  Drag and drop your contract or agreement here
                </p>
                <p className="text-xs text-ink-400 mt-1.5 font-mono">
                  or click to select file · PDF, PNG, JPG · up to 20 MB
                </p>
              </>
            ) : (
              <div className="w-full max-w-md flex items-center gap-3.5 rounded-lg bg-ink-950 border border-ink-800 p-4 text-left shadow-sm">
                <div className="w-10 h-10 rounded-md bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center shrink-0 text-indigo-400">
                  <FileText size={18} />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-xs sm:text-sm font-medium text-ink-100 truncate">{file.name}</p>
                  <p className="text-xs text-ink-500 font-mono mt-0.5">{formatFileSize(file.size)}</p>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleRemove();
                  }}
                  className="p-1 rounded text-ink-400 hover:text-ink-100 hover:bg-ink-850 transition-colors shrink-0"
                  disabled={pipeline.isPending}
                  aria-label="Remove uploaded file"
                >
                  <X size={16} />
                </button>
              </div>
            )}
          </div>

          {file && !pipeline.isPending && (
            <div className="px-6 py-3.5 bg-ink-950/60 border-t border-ink-800 flex items-center justify-between">
              <span className="text-xs font-mono text-ink-400">Ready for automated clause audit</span>
              <Button onClick={handleAnalyze} icon={FileSearch}>
                Analyze document
              </Button>
            </div>
          )}
        </div>
      )}

      {/* Processing Animation */}
      <AnimatePresence mode="wait">
        {pipeline.isPending && (
          <motion.div
            key="processing"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
          >
            <ProcessingSteps steps={STEPS} activeIndex={activeStep} />
          </motion.div>
        )}

        {/* Audit Results */}
        {result && !pipeline.isPending && (
          <motion.div
            key="results"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="space-y-7"
          >
            {/* Results Title Bar */}
            <div className="flex items-center justify-between flex-wrap gap-3 pb-4 border-b border-ink-800">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <CitationChip
                    label={result?.document_type || "Commercial Agreement"}
                    variant="precedent"
                  />
                  <span className="text-[11px] font-mono text-ink-500">
                    Clause-by-Clause Audit
                  </span>
                </div>
                <h2 className="text-lg sm:text-xl font-serif font-medium text-ink-100">
                  {file?.name}
                </h2>
              </div>
              <div className="flex items-center gap-2.5">
                <Button variant="ghost" onClick={handleRemove} icon={RotateCcw}>
                  Analyze another
                </Button>
                <Button
                  variant={exportStatus === "generating" ? "disabled" : "ghost"}
                  onClick={handleExport}
                  icon={
                    exportStatus === "generating"
                      ? Loader2
                      : exportStatus === "done"
                      ? FileCheck
                      : Download
                  }
                  disabled={exportStatus === "generating"}
                  className={exportStatus === "generating" ? "opacity-75 cursor-wait" : ""}
                >
                  {exportStatus === "generating"
                    ? "Generating PDF..."
                    : exportStatus === "done"
                    ? "Report downloaded"
                    : "Export analysis"}
                </Button>
              </div>
            </div>

            {/* OCR Warning if applicable */}
            {result?.ocr_warning && (
              <div className="p-4 rounded-lg bg-amber-950/20 border border-amber-500/30 flex items-start gap-3">
                <AlertTriangle size={16} className="text-amber-400 shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-xs font-semibold text-amber-300">OCR Processing Notice</h4>
                  <p className="text-xs text-ink-300 leading-relaxed mt-0.5">{result.ocr_warning}</p>
                </div>
              </div>
            )}

            {/* Score & Executive Summary Card */}
            <div className="p-6 sm:p-8 rounded-lg bg-ink-900/90 border border-ink-800 shadow-card">
              <RiskGauge score={result?.risk_score} level={result?.risk_level} />
              <div className="mt-6 pt-5 border-t border-ink-800 max-w-2xl mx-auto text-center">
                <span className="text-[11px] font-mono uppercase tracking-wider text-ink-400 block mb-1">
                  Executive Risk Summary
                </span>
                <p className="text-sm font-serif text-ink-200 leading-relaxed">
                  {result?.summary}
                </p>
              </div>
            </div>

            {/* Flagged Clauses Section */}
            {Array.isArray(result?.risky_clauses) && result.risky_clauses.length > 0 ? (
              <div className="space-y-4">
                <SectionHeader
                  title={`Flagged clauses (${result.risky_clauses.length})`}
                  subtitle="Clauses containing adverse terms, high liability covenants, or ambiguous obligations. Annotated with plain-English negotiation counter-positions."
                  icon={FileCheck}
                />
                <div className="space-y-3.5">
                  {result.risky_clauses.map((clause, i) => (
                    <ClauseAccordion key={clause?.clause_id || i} clause={clause} />
                  ))}
                </div>
              </div>
            ) : (
              <div className="p-8 rounded-lg bg-ink-900/80 border border-ink-800 text-center shadow-card">
                <p className="text-sm text-ink-400">
                  No risky clauses were flagged in this document under the current rule set.
                </p>
              </div>
            )}

            {/* Legal Disclaimer */}
            <Disclaimer text={result?.disclaimer} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
