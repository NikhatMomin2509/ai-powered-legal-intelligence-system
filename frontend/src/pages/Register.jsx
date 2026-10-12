import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ShieldCheck, ArrowLeft } from "lucide-react";
import { RegisterForm } from "../components/auth/AuthForms";
import { useAuth } from "../context/AuthContext";

export default function Register() {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from || "/";

  if (isAuthenticated) return <Navigate to={from} replace />;

  return (
    <div className="min-h-[70vh] flex items-center justify-center py-6 px-4">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="w-full max-w-md"
      >
        <div className="p-8 rounded-lg bg-ink-900 border border-ink-800 shadow-card">
          <div className="w-11 h-11 rounded-md bg-accent-500/10 border border-accent-500/20 flex items-center justify-center mb-5 text-accent-400">
            <ShieldCheck size={20} />
          </div>
          <h1 className="text-2xl font-serif font-medium text-ink-50 tracking-tight">
            Create your secure workspace
          </h1>
          <p className="text-xs sm:text-sm text-ink-300 mt-1.5 mb-6 leading-relaxed">
            Your account keeps your cases and document analyses separate from everyone else&apos;s.
            Original documents are processed temporarily and are not retained as raw files by default.
          </p>
          <RegisterForm
            onSuccess={() => navigate(from, { replace: true })}
            onSwitch={() => navigate("/login", { state: { from } })}
          />
        </div>
        <p className="text-center text-xs text-ink-500 mt-5">
          <Link
            to="/"
            className="hover:text-ink-300 transition-colors inline-flex items-center gap-1.5"
          >
            <ArrowLeft size={13} />
            <span>Back to dashboard</span>
          </Link>
        </p>
      </motion.div>
    </div>
  );
}
