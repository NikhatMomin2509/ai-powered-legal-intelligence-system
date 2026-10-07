import Sidebar from "./Sidebar";

export default function Shell({ children }) {
  return (
    <div className="flex min-h-screen bg-zinc-950 bg-mesh">
      <Sidebar />
      <main className="flex-1 min-w-0 px-8 py-10 md:px-12">
        <div className="max-w-5xl mx-auto">{children}</div>
      </main>
    </div>
  );
}
