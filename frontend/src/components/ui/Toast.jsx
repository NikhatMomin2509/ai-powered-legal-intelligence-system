import { createContext, useCallback, useContext, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertCircle, CheckCircle2, X } from "lucide-react";

const ToastContext = createContext(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const push = useCallback(
    (message, type = "error") => {
      const id = Date.now() + Math.random();
      setToasts((prev) => [...prev, { id, message, type }]);
      setTimeout(() => dismiss(id), 6000);
    },
    [dismiss]
  );

  const showError = useCallback((message) => push(message, "error"), [push]);
  const showSuccess = useCallback((message) => push(message, "success"), [push]);

  return (
    <ToastContext.Provider value={{ showError, showSuccess }}>
      {children}
      <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 w-full max-w-sm">
        <AnimatePresence>
          {toasts.map((t) => (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, y: 12, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, scale: 0.96 }}
              className={`glass rounded-xl p-3.5 flex items-start gap-2.5 shadow-lg ${
                t.type === "error" ? "border-rose-500/20" : "border-emerald-500/20"
              }`}
            >
              {t.type === "error" ? (
                <AlertCircle size={16} className="text-rose-400 shrink-0 mt-0.5" />
              ) : (
                <CheckCircle2 size={16} className="text-emerald-400 shrink-0 mt-0.5" />
              )}
              <p className="text-sm text-zinc-200 flex-1">{t.message}</p>
              <button onClick={() => dismiss(t.id)} className="text-zinc-500 hover:text-zinc-300">
                <X size={14} />
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}
