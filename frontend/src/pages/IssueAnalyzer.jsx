import { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Download, Scale, Gavel, ListChecks } from "lucide-react";
import { analyzeIssue } from "../services/api";
import { getIssueDomain } from "../services/normalize";
import { useToast } from "../components/ui/Toast";
import GlassCard from "../components/ui/GlassCard";
import Button from "../components/ui/Button";
import ProcessingSteps from "../components/ui/ProcessingSteps";
import AuthorityCard from "../components/ui/AuthorityCard";
import Disclaimer from "../components/ui/Disclaimer";

const STEPS = [
  { label: "Extracting key facts" },
  { label: "Searching legal authorities" },
  { label: "Evaluating arguments" },
  { label: "Synthesizing remedies" },
];

const MIN_LENGTH = 10;
const MAX_LENGTH = 2000;

function ConsiderationList({ title, items, tone }) {
  const toneStyles = {
    support: "border-emerald-500/15 bg-emerald-500/[0.04]",
    oppose: "border-amber-500/15 bg-amber-500/[0.04]",
  };
  return (
    <div className={`rounded-2xl border p-5 ${toneStyles[tone]}`}>
      <h3 className="text-sm font-medium text-zinc-200 mb-3">{title}</h3>
      {Array.isArray(items) && items.length > 0 ? (
        <ul className="space-y-2.5">
          {items.map((item, i) => (
            <li key={i} className="text-sm text-zinc-400 leading-relaxed flex gap-2">
              <span className={`mt-1.5 w-1 h-1 rounded-full shrink-0 ${tone === "support" ? "bg-emerald-400" : "bg-amber-400"}`} />
              {item}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-zinc-600 italic">None identified from the retrieved context.</p>
      )}
    </div>
  );
}

export default function IssueAnalyzer() {
  const [query, setQuery] = useState("");
  const [activeStep, setActiveStep] = useState(-1);
  const { showError } = useToast();
  const stepTimerRef = useRef(null);

  const mutation = useMutation({
    mutationFn: analyzeIssue,
    onMutate: () => {
      setActiveStep(0);
      let step = 0;
      stepTimerRef.current = setInterval(() => {
        step += 1;
        if (step < STEPS.length) setActiveStep(step);
      }, 1800);
    },
    onSettled: () => {
      clearInterval(stepTimerRef.current);
      setActiveStep(STEPS.length); // all complete
    },
    onError: (err) => showError(err.message),
  });

  useEffect(() => () => clearInterval(stepTimerRef.current), []);

  const trimmed = query.trim();
  const isValid = trimmed.length >= MIN_LENGTH;

  const handleSubmit = () => {
    if (!isValid || mutation.isPending) return;
    mutation.reset();
    mutation.mutate(trimmed);
  };

  const result = mutation.data;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-medium text-zinc-50 tracking-tight">Legal Issue Analyzer</h1>
        <p className="text-sm text-zinc-500 mt-1">
          Describe your situation in plain language. The system retrieves relevant Indian statutes
          and case law before producing an assessment.
        </p>
      </div>

      <GlassCard className="p-5">
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value.slice(0, MAX_LENGTH))}
          placeholder="e.g. My landlord is refusing to return my security deposit even though I left the apartment in good condition..."
          rows={5}
          className="w-full bg-transparent resize-none text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none leading-relaxed"
          disabled={mutation.isPending}
        />
        <div className="flex items-center justify-between mt-3 pt-3 border-t border-white/[0.06]">
          <span className={`text-xs ${isValid ? "text-zinc-500" : "text-zinc-600"}`}>
            {trimmed.length}/{MAX_LENGTH} characters
            {!isValid && trimmed.length > 0 && ` · minimum ${MIN_LENGTH}`}
          </span>
          <Button onClick={handleSubmit} disabled={!isValid || mutation.isPending} icon={Send}>
            {mutation.isPending ? "Analyzing..." : "Analyze issue"}
          </Button>
        </div>
      </GlassCard>

      <AnimatePresence mode="wait">
        {mutation.isPending && (
          <motion.div
            key="processing"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
          >
            <ProcessingSteps steps={STEPS} activeIndex={activeStep} />
          </motion.div>
        )}

        {result && !mutation.isPending && (
          <motion.div
            key="results"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="space-y-6"
          >
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div>
                <span className="inline-flex items-center gap-1.5 text-xs font-medium text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 px-2.5 py-1 rounded-full mb-3">
                  <Scale size={12} />
                  {getIssueDomain(result)}
                </span>
                <p className="text-zinc-200 leading-relaxed max-w-2xl">{result?.issue_summary}</p>
              </div>
              <Button variant="disabled" icon={Download} disabled>
                Export report
              </Button>
            </div>

            {Array.isArray(result?.key_facts) && result.key_facts.length > 0 && (
              <GlassCard className="p-5">
                <div className="flex items-center gap-2 mb-3">
                  <ListChecks size={15} className="text-zinc-500" />
                  <h3 className="text-sm font-medium text-zinc-300">Key facts identified</h3>
                </div>
                <ul className="space-y-1.5">
                  {result.key_facts.map((fact, i) => (
                    <li key={i} className="text-sm text-zinc-400 leading-relaxed">
                      · {fact}
                    </li>
                  ))}
                </ul>
              </GlassCard>
            )}

            {Array.isArray(result?.relevant_laws) && result.relevant_laws.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-zinc-300 mb-3">Relevant authorities</h3>
                <div className="grid sm:grid-cols-2 gap-3">
                  {result.relevant_laws.map((law, i) => (
                    <AuthorityCard key={law?.ref_id || i} law={law} />
                  ))}
                </div>
              </div>
            )}

            <div className="grid md:grid-cols-2 gap-4">
              <ConsiderationList title="Supporting considerations" items={result?.supporting_considerations} tone="support" />
              <ConsiderationList title="Opposing considerations" items={result?.opposing_considerations} tone="oppose" />
            </div>

            {Array.isArray(result?.missing_facts) && result.missing_facts.length > 0 && (
              <GlassCard className="p-5">
                <h3 className="text-sm font-medium text-zinc-300 mb-3">Facts that could change this assessment</h3>
                <ul className="space-y-1.5">
                  {result.missing_facts.map((fact, i) => (
                    <li key={i} className="text-sm text-zinc-500 leading-relaxed">
                      · {fact}
                    </li>
                  ))}
                </ul>
              </GlassCard>
            )}

            <GlassCard className="p-5">
              <div className="flex items-center gap-2 mb-3">
                <Gavel size={15} className="text-zinc-500" />
                <h3 className="text-sm font-medium text-zinc-300">Possible remedies</h3>
              </div>
              {Array.isArray(result?.possible_actions_or_remedies) && result.possible_actions_or_remedies.length > 0 ? (
                <ol className="space-y-2">
                  {result.possible_actions_or_remedies.map((action, i) => (
                    <li key={i} className="text-sm text-zinc-400 leading-relaxed flex gap-3">
                      <span className="text-emerald-400 font-medium shrink-0">{i + 1}.</span>
                      {action}
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="text-sm text-zinc-600 italic">No specific remedies identified.</p>
              )}
              {result?.lawyer_specialization && (
                <div className="mt-4 pt-4 border-t border-white/[0.06] text-sm text-zinc-400">
                  Recommended specialization:{" "}
                  <span className="text-zinc-200 font-medium">{result.lawyer_specialization}</span>
                </div>
              )}
            </GlassCard>

            <Disclaimer text={result?.disclaimer} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
