import { useEffect, useRef, useState } from "react";
import { Link, NavLink, useNavigate, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import {
  LayoutDashboard,
  MessageSquareText,
  FileSearch,
  History,
  ChevronsLeft,
  User,
  LogIn,
  LogOut,
  Briefcase,
  FileText,
  Menu,
  X,
  ShieldCheck,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import Logo from "./Logo";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/issue-analyzer", label: "Issue Analyzer", icon: MessageSquareText },
  { to: "/document-analyzer", label: "Document Analyzer", icon: FileSearch },
  { to: "/history", label: "History", icon: History },
];

function AccountMenu({ collapsed, onItemClick }) {
  const { user, isAuthenticated, isLoading, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const onDown = (e) => ref.current && !ref.current.contains(e.target) && setOpen(false);
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, []);

  if (isLoading) {
    return <div className="h-11 rounded-xl bg-white/[0.04] animate-pulse-soft" />;
  }

  if (!isAuthenticated) {
    if (collapsed) {
      return (
        <Link
          to="/login"
          aria-label="Log in"
          className="glass rounded-xl p-3 flex items-center justify-center text-ink-400 hover:text-amber-400 transition-colors"
          onClick={onItemClick}
        >
          <LogIn size={16} />
        </Link>
      );
    }
    return (
      <div className="space-y-1.5">
        <Link
          to="/login"
          onClick={onItemClick}
          className="block text-center rounded-xl px-3 py-2 text-sm text-ink-200 bg-white/[0.05] border border-white/10 hover:bg-white/[0.09] transition-colors"
        >
          Log in
        </Link>
        <Link
          to="/register"
          onClick={onItemClick}
          className="block text-center rounded-xl px-3 py-2 text-sm font-medium text-ink-950 bg-emerald-500 hover:bg-emerald-400 transition-colors"
        >
          Create account
        </Link>
      </div>
    );
  }

  const go = (to) => {
    setOpen(false);
    onItemClick?.();
    navigate(to);
  };

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        className="glass rounded-xl w-full p-3 flex items-center gap-2.5 hover:bg-ink-850 transition-colors text-left"
      >
        <span className="w-6 h-6 rounded-full bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center shrink-0">
          <User size={13} className="text-emerald-400" />
        </span>
        {!collapsed && (
          <span className="text-xs text-ink-200 truncate flex-1 font-mono">
            {user?.email}
          </span>
        )}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            role="menu"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 6 }}
            transition={{ duration: 0.15 }}
            className="absolute bottom-full left-0 mb-2 w-56 rounded-xl border border-white/10 bg-ink-900/98 backdrop-blur-xl p-1.5 shadow-2xl z-50"
          >
            <p className="px-3 py-2 text-xs text-ink-500 truncate border-b border-white/[0.06] mb-1 font-mono">
              {user?.email}
            </p>
            <button
              role="menuitem"
              onClick={() => go("/history?tab=issue")}
              className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-ink-300 hover:bg-white/[0.06] transition-colors text-left"
            >
              <Briefcase size={14} className="text-ink-500" />
              <span>My Cases</span>
            </button>
            <button
              role="menuitem"
              onClick={() => go("/history?tab=document")}
              className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-ink-300 hover:bg-white/[0.06] transition-colors text-left"
            >
              <FileText size={14} className="text-ink-500" />
              <span>My Documents</span>
            </button>
            <button
              role="menuitem"
              onClick={() => {
                setOpen(false);
                onItemClick?.();
                logout();
                navigate("/");
              }}
              className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-rose-300 hover:bg-rose-500/10 transition-colors text-left"
            >
              <LogOut size={14} />
              <span>Logout</span>
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  // Close mobile drawer on route change
  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  // Handle escape key for mobile drawer
  useEffect(() => {
    if (!mobileOpen) return;
    const onKey = (e) => e.key === "Escape" && setMobileOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [mobileOpen]);

  const navContent = (isMobile = false) => (
    <>
      <div className="flex items-center justify-between px-4 h-16 border-b border-white/[0.06]">
        <div className="flex items-center gap-2.5 min-w-0">
          <Logo size={26} />
          {(!collapsed || isMobile) && (
            <div className="min-w-0">
              <span className="text-sm font-serif font-medium text-ink-100 tracking-tight block truncate">
                Legal Intelligence
              </span>
              <span className="text-[10px] font-mono uppercase tracking-widest text-ink-500 block">
                Indian Law
              </span>
            </div>
          )}
        </div>
        {isMobile && (
          <button
            onClick={() => setMobileOpen(false)}
            aria-label="Close navigation menu"
            className="p-1.5 rounded-md text-ink-400 hover:text-ink-100 hover:bg-white/[0.05] transition-colors"
          >
            <X size={18} />
          </button>
        )}
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            onClick={() => isMobile && setMobileOpen(false)}
            className={({ isActive }) =>
              `relative flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-colors duration-150 ${
                isActive
                  ? "text-amber-400 bg-amber-500/10 border border-amber-500/20 font-medium"
                  : "text-ink-400 hover:text-ink-200 hover:bg-white/[0.04]"
              }`
            }
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <motion.div
                    layoutId={isMobile ? "mobile-sidebar-active" : "sidebar-active-indicator"}
                    className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-amber-400 rounded-full"
                  />
                )}
                <Icon size={17} className="shrink-0" />
                {(!collapsed || isMobile) && <span className="truncate">{label}</span>}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="p-3 space-y-2">
        <AccountMenu collapsed={collapsed && !isMobile} onItemClick={() => isMobile && setMobileOpen(false)} />

        <div className="glass rounded-xl p-2.5 flex items-center gap-2.5">
          <span className="relative flex h-2 w-2 shrink-0">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-60" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400" />
          </span>
          {(!collapsed || isMobile) && (
            <span className="text-[11px] font-mono text-ink-400 truncate">
              RAG Engine Online
            </span>
          )}
        </div>

        {!isMobile && (
          <button
            onClick={() => setCollapsed((v) => !v)}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-xl text-ink-500 hover:text-ink-300 hover:bg-white/[0.04] transition-colors"
          >
            <motion.div animate={{ rotate: collapsed ? 180 : 0 }} transition={{ duration: 0.2 }}>
              <ChevronsLeft size={16} />
            </motion.div>
          </button>
        )}
      </div>
    </>
  );

  return (
    <>
      {/* Mobile Top Header (screen width < 768px) */}
      <div className="md:hidden sticky top-0 z-40 w-full glass flex items-center justify-between px-4 h-14 border-b border-white/[0.08]">
        <div className="flex items-center gap-2.5">
          <Logo size={22} />
          <span className="text-sm font-serif font-medium text-ink-100">
            Legal Intelligence
          </span>
        </div>
        <button
          onClick={() => setMobileOpen(true)}
          aria-label="Open navigation menu"
          className="p-2 text-ink-400 hover:text-ink-100 transition-colors rounded-lg hover:bg-white/[0.05]"
        >
          <Menu size={20} />
        </button>
      </div>

      {/* Mobile Slide-out Drawer */}
      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setMobileOpen(false)}
              className="md:hidden fixed inset-0 z-50 bg-black/70 backdrop-blur-sm"
              aria-hidden="true"
            />
            <motion.aside
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", damping: 25, stiffness: 300 }}
              className="md:hidden fixed top-0 left-0 bottom-0 z-50 w-72 bg-ink-950 border-r border-white/10 flex flex-col shadow-2xl"
              aria-label="Mobile Navigation"
            >
              {navContent(true)}
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      {/* Desktop Sticky Sidebar */}
      <motion.aside
        animate={{ width: collapsed ? 76 : 248 }}
        transition={{ duration: 0.2, ease: "easeInOut" }}
        className="hidden md:flex glass h-screen sticky top-0 shrink-0 flex-col border-r border-white/[0.08] rounded-none z-30"
        aria-label="Sidebar Navigation"
      >
        {navContent(false)}
      </motion.aside>
    </>
  );
}
