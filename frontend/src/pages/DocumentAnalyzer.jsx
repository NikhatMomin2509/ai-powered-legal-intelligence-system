import { useCallback, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { UploadCloud, FileText, X, Download, AlertTriangle, FileSearch } from "lucide-react";
import { uploadDocument, analyzeDocument } from "../services/api";
import { useToast } from "../components/ui/Toast";
import GlassCard from "../components/ui/GlassCard";
import Button from "../components/ui/Button";
import ProcessingSteps from "../components/ui/ProcessingSteps";
import RiskGauge from "../components/ui/RiskGauge";
import ClauseAccordion from "../components/ui/ClauseAccordion";
import Disclaimer from "../components/ui/Disclaimer";

const STEPS = [
  { label: "Uploading document" },
  { label: "Extracting text" },
  { label: "Segmenting clauses" },
  { label: "Detecting risk patterns" },
  { label: "Retrieving legal authorities" },
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
  const fileInputRef = useRef(null);
  const { showError } = useToast();

  const pipeline = useMutation({
    mutationFn: async (selectedFile) => {
      setActiveStep(0);
      const uploadRes = await uploadDocument(selectedFile);
      setActiveStep(1);
      // Steps 1-4 are a single backend call (extract/segment/risk/retrieve/LLM
      // all happen server-side in one request) — step visually through them
      // on a timer so the workspace doesn't look stalled during real work.
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

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-medium text-zinc-50 tracking-tight">Document Risk Analyzer</h1>
        <p className="text-sm text-zinc-500 mt-1">
          Upload a rental agreement, employment contract, or other legal document to surface
          potentially risky clauses.
        </p>
      </div>

      {!result && (
        <GlassCard className="p-0 overflow-hidden">
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            onClick={() => !file && fileInputRef.current?.click()}
            className={`relative p-12 flex flex-col items-center justify-center text-center transition-all duration-300 ${
              !file ? "cursor-pointer" : ""
            } ${isDragging ? "bg-emerald-500/[0.06] shadow-[inset_0_0_0_1.5px_rgba(16,185,129,0.5)]" : ""}`}
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
                <motion.div
                  animate={{ y: isDragging ? -4 : 0 }}
                  className={`w-14 h-14 rounded-2xl flex items-center justify-center mb-4 border transition-colors ${
                    isDragging ? "bg-emerald-500/15 border-emerald-500/40 shadow-glow" : "bg-white/5 border-white/10"
                  }`}
                >
                  <UploadCloud size={22} className={isDragging ? "text-emerald-400" : "text-zinc-500"} />
                </motion.div>
                <p className="text-sm text-zinc-300 font-medium">Drag and drop your document here</p>
                <p className="text-xs text-zinc-600 mt-1.5">or click to browse · PDF, PNG, JPG · up to 20 MB</p>
              </>
            ) : (
              <div className="w-full max-w-md flex items-center gap-3 glass rounded-xl p-4 text-left">
                <div className="w-10 h-10 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center shrink-0">
                  <FileText size={18} className="text-indigo-400" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-zinc-200 truncate">{file.name}</p>
                  <p className="text-xs text-zinc-500">{formatFileSize(file.size)}</p>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleRemove();
                  }}
                  className="text-zinc-500 hover:text-zinc-200 transition-colors shrink-0"
                  disabled={pipeline.isPending}
                >
                  <X size={16} />
                </button>
              </div>
            )}
          </div>

          {file && !pipeline.isPending && (
            <div className="px-6 py-4 border-t border-white/[0.06] flex justify-end">
              <Button onClick={handleAnalyze} icon={FileSearch}>
                Analyze document
              </Button>
            </div>
          )}
        </GlassCard>
      )}

      <AnimatePresence mode="wait">
        {pipeline.isPending && (
          <motion.div key="processing" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <ProcessingSteps steps={STEPS} activeIndex={activeStep} />
          </motion.div>
        )}

        {result && !pipeline.isPending && (
          <motion.div
            key="results"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="space-y-6"
          >
            <div className="flex items-center justify-between flex-wrap gap-3">
              <div>
                <h2 className="text-lg font-medium text-zinc-100">{file?.name}</h2>
                <p className="text-sm text-zinc-500 mt-0.5">
                  {result?.document_type || "Unclassified document"}
                </p>
              </div>
              <div className="flex gap-2">
                <Button variant="ghost" onClick={handleRemove}>
                  Analyze another
                </Button>
                <Button variant="disabled" icon={Download} disabled>
                  Export analysis
                </Button>
              </div>
            </div>

            {result?.ocr_warning && (
              <div className="glass rounded-xl p-4 flex gap-3 border-amber-500/15">
                <AlertTriangle size={16} className="text-amber-400 shrink-0 mt-0.5" />
                <p className="text-xs text-zinc-400 leading-relaxed">{result.ocr_warning}</p>
              </div>
            )}

            <GlassCard className="p-8 flex flex-col items-center">
              <RiskGauge score={result?.risk_score} level={result?.risk_level} />
              <p className="text-sm text-zinc-400 text-center mt-5 max-w-md leading-relaxed">
                {result?.summary}
              </p>
            </GlassCard>

            {Array.isArray(result?.risky_clauses) && result.risky_clauses.length > 0 ? (
              <div>
                <h3 className="text-sm font-medium text-zinc-300 mb-3">
                  Flagged clauses ({result.risky_clauses.length})
                </h3>
                <div className="space-y-3">
                  {result.risky_clauses.map((clause, i) => (
                    <ClauseAccordion key={clause?.clause_id || i} clause={clause} />
                  ))}
                </div>
              </div>
            ) : (
              <GlassCard className="p-6 text-center">
                <p className="text-sm text-zinc-500">No risky clauses were flagged in this document.</p>
              </GlassCard>
            )}

            <Disclaimer text={result?.disclaimer} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
