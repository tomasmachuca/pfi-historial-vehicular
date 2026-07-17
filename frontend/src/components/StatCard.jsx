export default function StatCard({ icon, label, value, hint, loading = false }) {
  return (
    <div className="card card-hover p-5">
      <div className="flex items-center justify-between">
        <span className="text-sm text-slate-500">{label}</span>
        {icon && (
          <div className="inline-flex items-center justify-center w-8 h-8 rounded-lg bg-brand-50 text-brand-500">
            {icon}
          </div>
        )}
      </div>
      {loading ? (
        <div className="skeleton h-9 w-24 mt-2" />
      ) : (
        <div className="text-3xl font-semibold mt-2 tabular-nums tracking-tight">{value}</div>
      )}
      {hint && <div className="text-xs text-slate-500 mt-1">{hint}</div>}
    </div>
  );
}
