import Navbar from "./Navbar";
import Logo from "./Logo";
import meta from "../lib/contractMeta.json";

const REDES = { amoy: "Polygon Amoy", polygon: "Polygon" };

export default function Layout({ children }) {
  const red = REDES[meta?.network] ?? "Polygon Amoy";

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Navbar />
      <main className="flex-1">{children}</main>
      <footer className="border-t border-slate-200 bg-white">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-7 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Logo size={20} />
            <span className="text-xs text-slate-400">
              Historial vehicular verificable · Tesis PFI 2026
            </span>
          </div>
          <span className="inline-flex items-center gap-1.5 text-xs text-slate-500">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            <span className="font-mono">{red}</span>
          </span>
        </div>
      </footer>
    </div>
  );
}
