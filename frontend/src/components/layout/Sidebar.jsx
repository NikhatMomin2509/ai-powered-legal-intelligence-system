import { useState } from "react";
import { NavLink } from "react-router-dom";
import { motion } from "framer-motion";
import { LayoutDashboard, MessageSquareText, FileSearch, History, ChevronsLeft, Scale } from "lucide-react";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/issue-analyzer", label: "Issue Analyzer", icon: MessageSquareText },
  { to: "/document-analyzer", label: "Document Analyzer", icon: FileSearch },
  { to: "/history", label: "History", icon: History },
];

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <motion.aside
      animate={{ width: collapsed ? 76 : 248 }}
      transition={{ duration: 0.25, ease: "easeInOut" }}
      className="glass h-screen sticky top-0 shrink-0 flex flex-col border-r border-white/[0.08] rounded-none"
    >
      <div className="flex items-center gap-2.5 px-4 h-16 border-b border-white/[0.06]">
        <div className="w-7 h-7 rounded-lg bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center shrink-0">
          <Scale size={14} className="text-emerald-400" />
        </div>
        {!collapsed && (
          <span className="text-sm font-medium text-zinc-200 truncate">Legal Intelligence</span>
        )}
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `relative flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-colors duration-200 ${
                isActive ? "text-emerald-400 bg-emerald-500/10" : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04]"
              }`
            }
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <motion.div
                    layoutId="sidebar-active-indicator"
                    className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-emerald-400 rounded-full shadow-glow"
                  />
                )}
                <Icon size={17} className="shrink-0" />
                {!collapsed && <span className="truncate">{label}</span>}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="p-3 space-y-2">
        <div className="glass rounded-xl p-3 flex items-center gap-2.5">
          <span className="relative flex h-2 w-2 shrink-0">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-60" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400" />
          </span>
          {!collapsed && <span className="text-xs text-zinc-400">AI Engine Online</span>}
        </div>

        <button
          onClick={() => setCollapsed((v) => !v)}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-xl text-zinc-500 hover:text-zinc-300 hover:bg-white/[0.04] transition-colors"
        >
          <motion.div animate={{ rotate: collapsed ? 180 : 0 }} transition={{ duration: 0.25 }}>
            <ChevronsLeft size={16} />
          </motion.div>
        </button>
      </div>
    </motion.aside>
  );
}
