import Sidebar from "./Sidebar";

export default function Shell({ children }) {
  return (
    <div className="flex flex-col md:flex-row min-h-screen bg-ink-950 bg-mesh text-ink-100 antialiased selection:bg-amber-500/20 selection:text-amber-200">
      <Sidebar />
      <main className="flex-1 min-w-0 px-4 py-6 sm:px-6 md:px-10 md:py-10">
        <div className="max-w-5xl mx-auto">{children}</div>
      </main>
    </div>
  );
}
