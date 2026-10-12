import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "framer-motion";
import { X, ShieldCheck } from "lucide-react";
import { LoginForm, RegisterForm } from "./AuthForms";

/**
 * Auth as an OVERLAY (not a route change) wherever the page holds state the
 * user would lose by navigating away — e.g. a one-time anonymous legal
 * analysis that is intentionally never stored anywhere but this tab's memory.
 */
export default function AuthModal({
  open,
  initialMode = "register",
  message,
  onClose,
  onSuccess,
}) {
  const [mode, setMode] = useState(initialMode);

  useEffect(() => {
    if (open) setMode(initialMode);
  }, [open, initialMode]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e) => e.key === "Escape" && onClose?.();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const isLogin = mode === "login";

  // Rendered through a portal to <body>: as a child of a page using Tailwind's
  // `space-y-*`, a position:fixed overlay inherited that class's margin-top and
  // stopped covering the top of the viewport (measured: top=32px, height=968px).
  // Portals also sidestep any parent overflow/stacking-context surprises.
  return createPortal(
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink-950/85 backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onMouseDown={(e) => e.target === e.currentTarget && onClose?.()}
        >
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label={isLogin ? "Log in" : "Create account"}
            className="rounded-lg border border-ink-800 bg-ink-900 w-full max-w-md p-7 relative shadow-2xl"
            initial={{ opacity: 0, y: 14, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.98 }}
            transition={{ duration: 0.2 }}
          >
            <button
              onClick={onClose}
              className="absolute top-4 right-4 p-1.5 rounded text-ink-400 hover:text-ink-100 hover:bg-ink-850 transition-colors"
              aria-label="Close"
            >
              <X size={17} />
            </button>

            <div className="w-10 h-10 rounded-md bg-accent-500/10 border border-accent-500/20 flex items-center justify-center mb-4 text-accent-400">
              <ShieldCheck size={18} />
            </div>
            <h2 className="text-xl font-serif font-medium text-ink-50 tracking-tight">
              {isLogin ? "Welcome back" : "Create your secure workspace"}
            </h2>
            {message && (
              <p className="text-xs sm:text-sm text-ink-300 mt-1.5 mb-5 leading-relaxed">
                {message}
              </p>
            )}
            {!message && <div className="mb-5" />}

            {isLogin ? (
              <LoginForm onSuccess={onSuccess} onSwitch={() => setMode("register")} />
            ) : (
              <RegisterForm onSuccess={onSuccess} onSwitch={() => setMode("login")} />
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body
  );
}
